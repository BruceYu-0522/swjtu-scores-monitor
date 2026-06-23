import os
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import session_store
from utils.fetcher import BASE_URL


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("缺少 Playwright。请使用下面的命令启动：")
        print("uv run --with playwright python scripts/bootstrap_session.py")
        return 1

    if not os.getenv("GIST_PAT"):
        print("请先设置 GIST_PAT 环境变量，它需要有 gist 权限。")
        return 1

    if not os.getenv("SESSION_ENCRYPTION_KEY"):
        print("请先设置 SESSION_ENCRYPTION_KEY 环境变量，并在 GitHub Secrets 中使用同一个值。")
        return 1

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
        except Exception as e:
            print(f"启动 Playwright 浏览器失败: {e}")
            print("如果是首次使用，请先运行：uv run --with playwright playwright install chromium")
            return 1

        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/service/login.jsp", wait_until="domcontentloaded")
        user_agent = page.evaluate("navigator.userAgent")

        print("浏览器已打开教务网登录页。")
        print("请在浏览器里完成企业微信认证，并进入能查看成绩的页面。")
        input("完成后回到这里按 Enter 保存登录态...")

        cookies = context.cookies()
        browser.close()

    if not cookies:
        print("没有捕获到任何 cookie，请确认已经在打开的浏览器中登录成功。")
        return 1

    session_data = {
        "base_url": "https://jwc.swjtu.edu.cn",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "user_agent": user_agent,
        "cookies": cookies,
    }

    result = session_store.save_session(session_data)
    if not result:
        print("登录态保存失败，请检查 GIST_PAT 和 SESSION_ENCRYPTION_KEY。")
        return 1

    domains = sorted({cookie.get("domain", "") for cookie in cookies if cookie.get("domain")})
    print(f"登录态已加密保存，共保存 {len(cookies)} 个 cookie。")
    print(f"涉及域名: {', '.join(domains)}")
    print("GitHub Actions 下次运行会优先复用它。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
