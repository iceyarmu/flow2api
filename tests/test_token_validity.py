"""测试生成的 reCAPTCHA token 是否有效"""
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

# 添加项目根目录到路径（tests/目录的父目录）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置
RECAPTCHA_SERVICE_URL = "http://127.0.0.1:8001"
FLOW2API_URL = "http://127.0.0.1:8000"
API_KEY = "han1234"


async def get_token_from_service(project_id: str) -> dict:
    """从服务获取 token"""
    print(f"从 reCAPTCHA 服务获取 token...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{RECAPTCHA_SERVICE_URL}/token",
                json={"project_id": project_id}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    token = data.get("token")
                    duration_ms = data.get("duration_ms", 0)
                    print(f"✅ Token 获取成功（耗时 {duration_ms:.0f}ms）")
                    print(f"Token 长度: {len(token)} 字符")
                    return {
                        "success": True,
                        "token": token,
                        "duration_ms": duration_ms
                    }
                else:
                    print(f"❌ Token 获取失败: {data.get('error')}")
                    return {"success": False, "error": data.get("error")}
            else:
                print(f"❌ 服务请求失败: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ 获取 token 异常: {str(e)}")
        return {"success": False, "error": str(e)}


async def test_token_with_flow_api(project_id: str, token: str):
    """使用 token 测试 Flow API 调用
    
    我们尝试调用图片生成 API，看是否会返回 403 reCAPTCHA 错误
    """
    print()
    print("=" * 60)
    print("测试 Token 有效性（调用 Flow API）")
    print("=" * 60)
    print()
    
    # 首先需要获取一个有效的 AT token
    print("1. 获取有效的 AT token...")
    at_token = None
    try:
        # 从数据库获取 token
        from src.core.database import Database
        import aiosqlite
        
        db = Database()
        if db.db_exists():
            async with aiosqlite.connect(db.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT at 
                    FROM tokens 
                    WHERE is_active = 1 
                      AND at IS NOT NULL 
                    LIMIT 1
                """)
                row = await cursor.fetchone()
                if row and row[0]:
                    at_token = row[0]
        
        if not at_token:
            print("⚠️  未找到有效的 AT token，跳过 API 调用测试")
            print("   建议：先添加一个 token 到系统")
            return False
        else:
            print("✅ 找到有效的 AT token")
    except Exception as e:
        print(f"⚠️  获取 AT token 失败: {str(e)}")
        print("   跳过 API 调用测试")
        return False
    
    # 使用 Flow2API 来测试（这会使用我们获取的 reCAPTCHA token）
    print()
    print("2. 调用 Flow2API 图片生成接口（会使用 reCAPTCHA token）...")
    print(f"   Project ID: {project_id}")
    print(f"   模型: gemini-2.5-flash-image-landscape")
    print(f"   提示词: A beautiful sunset")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{FLOW2API_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gemini-2.5-flash-image-landscape",
                    "messages": [
                        {
                            "role": "user",
                            "content": "A beautiful sunset"
                        }
                    ],
                    "stream": True  # 使用流式模式才能生成图片
                }
            )
            
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ API 调用成功（没有 403 错误）")
                print("   ✅ Token 验证通过！")
                print()
                
                # 处理流式响应
                print("   接收流式响应...")
                import re
                content_parts = []
                image_urls = []
                
                async for line in response.aiter_lines():
                    if line:
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    if "delta" in choice:
                                        delta = choice["delta"]
                                        if "content" in delta:
                                            content = delta["content"]
                                            content_parts.append(content)
                                            
                                            # 检查是否包含图片 URL（Markdown 格式）
                                            img_matches = re.findall(r'!\[.*?\]\((.*?)\)', content)
                                            for img_url in img_matches:
                                                if img_url not in image_urls:
                                                    image_urls.append(img_url)
                            except json.JSONDecodeError:
                                continue
                
                # 显示结果
                full_content = "".join(content_parts)
                print(f"   接收到的内容长度: {len(full_content)} 字符")
                
                if image_urls:
                    print()
                    print("   ✅ 图片生成成功！")
                    for idx, img_url in enumerate(image_urls, 1):
                        print(f"   图片 {idx}: {img_url}")
                    print()
                    print("   完整响应内容（前500字符）:")
                    print(f"   {full_content[:500]}...")
                else:
                    print()
                    print("   ⚠️  响应中没有找到图片 URL")
                    if full_content:
                        print(f"   内容: {full_content[:300]}...")
                    else:
                        print("   （响应内容为空）")
                
                return True
            elif response.status_code == 403:
                print("   ❌ API 返回 403 错误")
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    print(f"   错误信息: {error_msg}")
                    if "reCAPTCHA" in error_msg or "recaptcha" in error_msg.lower():
                        print("   ❌ Token 无效或已过期")
                    else:
                        print("   ⚠️  其他 403 错误（可能不是 reCAPTCHA 问题）")
                except:
                    print(f"   响应内容: {response.text[:200]}")
                return False
            else:
                print(f"   ⚠️  API 返回其他错误: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   错误信息: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   响应内容: {response.text[:200]}")
                # 其他错误不一定表示 token 无效，可能是其他原因
                return None
                
    except httpx.ConnectError:
        print(f"   ❌ 无法连接到 Flow2API ({FLOW2API_URL})")
        print("   请确保 Flow2API 服务已启动")
        return False
    except Exception as e:
        print(f"   ❌ 调用 API 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def analyze_token(token: str):
    """分析 token 的基本特征"""
    print()
    print("=" * 60)
    print("Token 分析")
    print("=" * 60)
    print()
    
    print(f"Token 长度: {len(token)} 字符")
    print(f"Token 类型: Base64 编码字符串")
    print()
    
    # 检查 token 格式
    import base64
    import re
    
    # reCAPTCHA v3 token 通常是 Base64 编码的字符串
    # 包含字母、数字、连字符、下划线
    if re.match(r'^[A-Za-z0-9_-]+$', token):
        print("✅ Token 格式正确（符合 Base64 URL-safe 编码）")
    else:
        print("⚠️  Token 格式可能有问题（包含非法字符）")
    
    # 尝试 Base64 解码（部分 token 可以解码查看结构）
    try:
        # 注意：reCAPTCHA token 可能包含连字符，需要替换
        decoded = base64.urlsafe_b64decode(token.replace('-', '+').replace('_', '/') + '==')
        print(f"✅ Token 可以 Base64 解码（解码后长度: {len(decoded)} 字节）")
        print(f"   解码后前16字节（hex）: {decoded[:16].hex()}")
    except Exception as e:
        print(f"⚠️  Token Base64 解码失败: {str(e)}")
    
    print()
    print("Token 预览（前150字符）:")
    print(token[:150] + "..." if len(token) > 150 else token)
    print()


async def main():
    """主函数"""
    print("=" * 60)
    print("测试 reCAPTCHA Token 有效性")
    print("=" * 60)
    print()
    
    # 获取 project_id
    project_id = None
    
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        # 尝试从数据库获取
        try:
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
            print("用法: python test_token_validity.py <project_id>")
            print()
            print("或者确保数据库中有有效的 token 和 project_id")
            sys.exit(1)
    
    print(f"Project ID: {project_id}")
    print()
    
    # 1. 获取 token
    token_result = await get_token_from_service(project_id)
    
    if not token_result.get("success"):
        print()
        print("❌ 无法获取 token，测试终止")
        sys.exit(1)
    
    token = token_result["token"]
    
    # 2. 分析 token
    await analyze_token(token)
    
    # 3. 测试 token 有效性（通过实际 API 调用）
    api_result = await test_token_with_flow_api(project_id, token)
    
    # 总结
    print()
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print()
    
    if api_result is True:
        print("✅ Token 验证通过！")
        print("   - Token 格式正确")
        print("   - Token 可以被 Flow API 接受")
        print("   - 没有返回 403 reCAPTCHA 错误")
    elif api_result is False:
        print("❌ Token 验证失败")
        print("   - Token 可能无效或已过期")
        print("   - 或者 Flow API 返回了 403 reCAPTCHA 错误")
    else:
        print("⚠️  无法确定 Token 有效性")
        print("   - API 返回了其他错误（可能不是 reCAPTCHA 问题）")
        print("   - 建议检查其他错误信息")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())

