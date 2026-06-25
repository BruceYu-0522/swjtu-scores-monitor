from bs4 import BeautifulSoup


class BrowserSession:
    def __init__(self, storage_state, user_agent=None, playwright_factory=None):
        self.storage_state = storage_state
        self.user_agent = user_agent
        self.playwright_factory = playwright_factory
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self, validation_url):
        try:
            if self.playwright_factory is None:
                from playwright.sync_api import sync_playwright

                self.playwright_factory = sync_playwright

            self.playwright = self.playwright_factory().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            context_options = {"storage_state": self.storage_state}
            if self.user_agent:
                context_options["user_agent"] = self.user_agent
            self.context = self.browser.new_context(**context_options)
            self.page = self.context.new_page()
            self.page.goto(validation_url, wait_until="domcontentloaded")

            html = self.page.content()
            soup = BeautifulSoup(html, "html.parser")
            if soup.find("table", id="table3") is not None:
                return True

            title = self.page.title() or "无标题"
            page_text = " ".join(soup.get_text(" ", strip=True).split())
            print(
                "浏览器登录态验证失败: "
                f"final_url={self.page.url}, title={title}"
            )
            print(f"浏览器登录态验证页面摘要: {page_text[:500]}")
            self.close()
            return False
        except Exception as exc:
            print(f"启动无头浏览器验证登录态失败: {exc}")
            self.close()
            return False

    def get_html(self, url, referer=None):
        if self.page is None:
            raise RuntimeError("浏览器会话尚未启动")

        options = {"wait_until": "domcontentloaded"}
        if referer:
            options["referer"] = referer
        self.page.goto(url, **options)
        return self.page.content()

    def close(self):
        for resource_name in ("page", "context", "browser"):
            resource = getattr(self, resource_name)
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    pass
                setattr(self, resource_name, None)

        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
