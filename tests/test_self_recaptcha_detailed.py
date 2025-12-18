"""详细测试自实现的 reCAPTCHA 方案（带调试信息）"""
import asyncio
import sys
import io
from pathlib import Path
from typing import Optional

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
# 添加项目根目录到路径（tests/目录的父目录）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright 未安装")
    print("请运行: pip install playwright && playwright install chromium")
    sys.exit(1)

async def test_detailed_recaptcha(project_id: str):
    """详细测试 reCAPTCHA token 获取过程"""
    print("=" * 80)
    print("详细测试自实现的 reCAPTCHA 方案")
    print("=" * 80)
    print()
    print(f"Project ID: {project_id}")
    website_url = f"https://labs.google/fx/tools/flow/project/{project_id}"
    website_key = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
    print(f"目标 URL: {website_url}")
    print(f"reCAPTCHA Site Key: {website_key}")
    print()
    
    async with async_playwright() as p:
        print("1. 启动浏览器（有头模式，可以看到窗口）...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        print("   ✅ 浏览器已启动")
        print()
        
        print("2. 创建浏览器上下文...")
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        page = await context.new_page()
        print("   ✅ 上下文已创建")
        print()
        
        print("3. 访问页面...")
        print(f"   URL: {website_url}")
        try:
            # 监听页面加载事件
            page.on("console", lambda msg: print(f"   [页面控制台] {msg.text}"))
            page.on("pageerror", lambda err: print(f"   [页面错误] {err}"))
            
            response = await page.goto(website_url, wait_until="domcontentloaded", timeout=30000)
            print(f"   ✅ 页面已加载，状态码: {response.status if response else 'N/A'}")
            
            # 检查页面标题和URL
            title = await page.title()
            current_url = page.url
            print(f"   页面标题: {title}")
            print(f"   当前URL: {current_url}")
            print()
            
            # 检查是否需要登录
            if "accounts.google.com" in current_url or "signin" in current_url.lower():
                print("   ⚠️  页面重定向到登录页面（这是正常的）")
                print("   注意：即使需要登录，我们仍尝试获取 reCAPTCHA token")
            print()
            
        except Exception as e:
            print(f"   ⚠️  页面加载异常: {str(e)}")
            print("   继续尝试获取 reCAPTCHA token...")
            print()
        
        print("4. 检查 reCAPTCHA 是否已加载...")
        try:
            # 检查 window.grecaptcha 是否存在
            grecaptcha_exists = await page.evaluate("typeof window.grecaptcha !== 'undefined'")
            print(f"   window.grecaptcha 存在: {grecaptcha_exists}")
            
            if grecaptcha_exists:
                grecaptcha_ready = await page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            if (window.grecaptcha && window.grecaptcha.ready) {
                                window.grecaptcha.ready(() => resolve(true));
                                setTimeout(() => resolve(false), 5000);
                            } else {
                                resolve(false);
                            }
                        });
                    }
                """)
                print(f"   grecaptcha.ready: {grecaptcha_ready}")
            print()
        except Exception as e:
            print(f"   ⚠️  检查 reCAPTCHA 时出错: {str(e)}")
            print()
        
        print("5. 等待 reCAPTCHA 初始化（3秒）...")
        await page.wait_for_timeout(3000)
        print("   ✅ 等待完成")
        print()
        
        print("6. 尝试执行 reCAPTCHA 并获取 token...")
        try:
            token = await page.evaluate("""
                async (websiteKey) => {
                    try {
                        console.log('[测试脚本] 开始获取 reCAPTCHA token...');
                        console.log('[测试脚本] websiteKey:', websiteKey);
                        
                        // 检查 grecaptcha 是否存在
                        if (typeof window.grecaptcha === 'undefined') {
                            console.error('[测试脚本] window.grecaptcha 未定义');
                            return null;
                        }
                        
                        console.log('[测试脚本] window.grecaptcha 存在');
                        
                        // 等待 grecaptcha ready
                        await new Promise((resolve, reject) => {
                            const timeout = setTimeout(() => {
                                reject(new Error('reCAPTCHA加载超时'));
                            }, 10000);
                            
                            if (window.grecaptcha && window.grecaptcha.ready) {
                                window.grecaptcha.ready(() => {
                                    clearTimeout(timeout);
                                    console.log('[测试脚本] grecaptcha.ready() 完成');
                                    resolve();
                                });
                            } else {
                                clearTimeout(timeout);
                                resolve();
                            }
                        });
                        
                        console.log('[测试脚本] 调用 grecaptcha.execute...');
                        // 执行reCAPTCHA v3
                        const token = await window.grecaptcha.execute(websiteKey, {
                            action: 'FLOW_GENERATION'
                        });
                        
                        console.log('[测试脚本] token 获取成功，长度:', token ? token.length : 0);
                        return token;
                    } catch (error) {
                        console.error('[测试脚本] reCAPTCHA执行错误:', error);
                        console.error('[测试脚本] 错误详情:', error.message, error.stack);
                        return null;
                    }
                }
            """, website_key)
            
            print()
            print("=" * 80)
            if token:
                print("✅ Token 获取成功！")
                print("=" * 80)
                print()
                print(f"Token 长度: {len(token)} 字符")
                print()
                print("Token 预览（前150字符）:")
                print(token[:150] + "..." if len(token) > 150 else token)
                print()
                print("完整 Token:")
                print(token)
            else:
                print("❌ Token 获取失败（返回 null）")
                print("=" * 80)
                print()
                print("可能的原因：")
                print("1. 页面需要登录，reCAPTCHA 无法在没有认证的情况下执行")
                print("2. reCAPTCHA 未正确加载到页面中")
                print("3. 页面结构发生变化，无法找到 reCAPTCHA")
                print("4. 网络问题导致 reCAPTCHA 脚本未加载")
        except Exception as e:
            print()
            print("=" * 80)
            print(f"❌ 执行 reCAPTCHA 时发生异常: {str(e)}")
            print("=" * 80)
            import traceback
            traceback.print_exc()
        
        print()
        print("7. 清理资源...")
        print("   提示：浏览器窗口将保持打开5秒，方便查看页面状态")
        await page.wait_for_timeout(5000)
        await context.close()
        await browser.close()
        print("   ✅ 资源清理完成")
        print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


async def main():
    """主函数"""
    # 获取 project_id
    project_id: Optional[str] = None
    
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
            print("用法: python test_self_recaptcha_detailed.py <project_id>")
            sys.exit(1)
    
    await test_detailed_recaptcha(project_id)


if __name__ == "__main__":
    asyncio.run(main())

