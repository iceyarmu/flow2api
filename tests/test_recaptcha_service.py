"""测试 reCAPTCHA Token Service"""
import asyncio
import sys
import io
from pathlib import Path
import httpx
import json

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
SERVICE_URL = "http://127.0.0.1:8001"


async def test_health():
    """测试健康检查"""
    print("=" * 60)
    print("测试健康检查")
    print("=" * 60)
    print()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SERVICE_URL}/health")
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("✅ 服务健康")
                    return True
                else:
                    print(f"⚠️  服务状态: {data.get('status')}")
                    return False
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"❌ 无法连接到服务 ({SERVICE_URL})")
        print("   请确保服务已启动: python recaptcha_service.py")
        return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


async def test_get_token(project_id: str):
    """测试获取 token"""
    print()
    print("=" * 60)
    print("测试获取 Token")
    print("=" * 60)
    print()
    print(f"Project ID: {project_id}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("发送请求...")
            response = await client.post(
                f"{SERVICE_URL}/token",
                json={"project_id": project_id}
            )
            
            print(f"状态码: {response.status_code}")
            print()
            
            data = response.json()
            print("响应:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print()
            
            if response.status_code == 200:
                if data.get("success"):
                    token = data.get("token")
                    duration_ms = data.get("duration_ms", 0)
                    print("=" * 60)
                    print("✅ Token 获取成功！")
                    print("=" * 60)
                    print()
                    print(f"Token 长度: {len(token)} 字符")
                    print(f"耗时: {duration_ms:.0f}ms")
                    print()
                    print("Token 预览（前100字符）:")
                    print(token[:100] + "..." if len(token) > 100 else token)
                    return True
                else:
                    error = data.get("error", "Unknown error")
                    duration_ms = data.get("duration_ms", 0)
                    print("=" * 60)
                    print("❌ Token 获取失败")
                    print("=" * 60)
                    print()
                    print(f"错误: {error}")
                    print(f"耗时: {duration_ms:.0f}ms")
                    return False
            else:
                print(f"❌ 请求失败: {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"❌ 无法连接到服务 ({SERVICE_URL})")
        print("   请确保服务已启动: python recaptcha_service.py")
        return False
    except httpx.TimeoutException:
        print("❌ 请求超时（60秒）")
        return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_concurrent_requests(project_id: str, count: int = 3):
    """测试并发请求"""
    print()
    print("=" * 60)
    print(f"测试并发请求（{count} 个并发）")
    print("=" * 60)
    print()
    
    async def get_token_once(index: int):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{SERVICE_URL}/token",
                    json={"project_id": project_id}
                )
                data = response.json()
                if data.get("success"):
                    duration_ms = data.get("duration_ms", 0)
                    print(f"  ✅ 请求 #{index+1}: 成功 ({duration_ms:.0f}ms)")
                    return True
                else:
                    print(f"  ❌ 请求 #{index+1}: 失败 - {data.get('error')}")
                    return False
        except Exception as e:
            print(f"  ❌ 请求 #{index+1}: 异常 - {str(e)}")
            return False
    
    print("发送并发请求...")
    import time
    start_time = time.time()
    
    tasks = [get_token_once(i) for i in range(count)]
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    success_count = sum(results)
    
    print()
    print("=" * 60)
    print("并发测试结果")
    print("=" * 60)
    print(f"成功: {success_count}/{count}")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"平均耗时: {total_time/count:.2f}秒/请求")
    print()


async def main():
    """主函数"""
    # 获取 project_id
    project_id = None
    
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        # 尝试从数据库获取
        try:
            # 添加项目根目录到路径（tests/目录的父目录）
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))
            
            from src.core.database import Database
            import aiosqlite
            
            db = Database()
            if db.db_exists():
                async with aiosqlite.connect(db.db_path) as conn:
                    cursor = await conn.execute("""
                        SELECT current_project_id 
                        FROM tokens 
                        WHERE is_active = 1 
                          AND current_project_id IS NOT NULL 
                        LIMIT 1
                    """)
                    row = await cursor.fetchone()
                    if row and row[0]:
                        project_id = row[0]
        except:
            pass
        
        if not project_id:
            print("请提供 project_id 作为命令行参数")
            print("用法: python test_recaptcha_service.py <project_id>")
            print()
            print("或者确保数据库中有有效的 token 和 project_id")
            sys.exit(1)
    
    # 测试健康检查
    if not await test_health():
        print()
        print("⚠️  服务未就绪，请先启动服务:")
        print("   python recaptcha_service.py")
        sys.exit(1)
    
    # 测试获取 token
    await test_get_token(project_id)
    
    # 测试并发请求
    await test_concurrent_requests(project_id, count=3)
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

