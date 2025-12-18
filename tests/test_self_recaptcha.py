"""测试自实现的 reCAPTCHA 方案"""
import asyncio
import sys
import io
from pathlib import Path
from typing import Optional

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径（tests/目录的父目录）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.self_recaptcha_solver import SelfRecaptchaSolver
from src.core.logger import debug_logger
from src.core.database import Database

# 为了测试，我们也可以直接使用 Playwright 来调试
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


async def get_project_id_from_db() -> Optional[str]:
    """从数据库获取一个 project_id（用于测试）"""
    try:
        import aiosqlite
        db = Database()
        if not db.db_exists():
            return None
        
        async with aiosqlite.connect(db.db_path) as conn:
            # 查询一个有效的 token 的 project_id
            cursor = await conn.execute("""
                SELECT current_project_id 
                FROM tokens 
                WHERE is_active = 1 
                  AND current_project_id IS NOT NULL 
                LIMIT 1
            """)
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
    except Exception as e:
        debug_logger.log_warning(f"从数据库获取 project_id 失败: {str(e)}")
    
    return None


async def test_self_recaptcha():
    """测试自实现的 reCAPTCHA token 获取"""
    print("=" * 60)
    print("测试自实现的 reCAPTCHA 方案")
    print("=" * 60)
    print()
    
    # 获取 project_id
    project_id: Optional[str] = None
    
    # 方式1: 命令行参数
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        print(f"从命令行参数获取 project_id: {project_id}")
    else:
        # 方式2: 从数据库获取
        print("尝试从数据库获取 project_id...")
        project_id = await get_project_id_from_db()
        if project_id:
            print(f"从数据库获取到 project_id: {project_id}")
        else:
            print("⚠️  未能从数据库获取 project_id")
            print()
            print("请通过以下方式之一提供 project_id:")
            print("1. 命令行参数: python test_self_recaptcha.py <project_id>")
            print("2. 确保数据库中有有效的 token 和 project_id")
            print()
            print("示例 project_id 格式（UUID）:")
            print("  例如: 12345678-1234-1234-1234-123456789abc")
            return
    print()
    
    print(f"Project ID: {project_id}")
    print(f"目标URL: https://labs.google/fx/tools/flow/project/{project_id}")
    print()
    
    # 创建 solver 实例（本地测试使用有头模式，可以看到浏览器）
    print("正在创建 Playwright solver...")
    try:
        solver = SelfRecaptchaSolver(headless=False)  # False 表示显示浏览器窗口
        print("✅ Solver 创建成功")
        print()
    except ImportError as e:
        print(f"❌ 错误：Playwright 未安装")
        print(f"   请运行: pip install playwright")
        print(f"   然后运行: playwright install chromium")
        return
    except Exception as e:
        print(f"❌ 创建 solver 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 获取 token
    print("开始获取 reCAPTCHA token...")
    print("（这可能需要几秒钟，浏览器窗口会自动打开）")
    print()
    print("提示：如果浏览器窗口打开了，请观察页面是否正常加载")
    print("如果页面显示需要登录，这是正常的（Google Flow 需要登录）")
    print("但我们仍然尝试从页面中获取 reCAPTCHA token")
    print()
    
    try:
        token = await solver.get_recaptcha_token(project_id)
        
        print()
        print("=" * 60)
        if token:
            print("✅ Token 获取成功！")
            print("=" * 60)
            print()
            print(f"Token 长度: {len(token)} 字符")
            print()
            print("Token 预览（前100字符）:")
            print(token[:100] + "..." if len(token) > 100 else token)
            print()
            print("完整 Token:")
            print(token)
        else:
            print("❌ Token 获取失败")
            print("=" * 60)
            print()
            print("可能的原因：")
            print("1. Project ID 不正确")
            print("2. 网络连接问题")
            print("3. reCAPTCHA 未正确加载")
            print("4. 页面访问被阻止")
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 测试过程中发生异常: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        print()
        print("正在清理资源...")
        try:
            await solver.close()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️  清理资源时出错: {str(e)}")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_self_recaptcha())

