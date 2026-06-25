import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.browser_session import BrowserSession


SCORE_URL = "https://jwc.swjtu.edu.cn/vatuu/StudentScoreInfoAction"


class FakePage:
    def __init__(self, html):
        self.html = html
        self.visited = []
        self.closed = False

    def goto(self, url, **kwargs):
        self.visited.append((url, kwargs))

    def content(self):
        return self.html

    def title(self):
        return "VATUU"

    @property
    def url(self):
        return self.visited[-1][0] if self.visited else ""

    def close(self):
        self.closed = True


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, context):
        self.context = context
        self.new_context_options = None
        self.closed = False

    def new_context(self, **kwargs):
        self.new_context_options = kwargs
        return self.context

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, browser):
        self.browser = browser
        self.launch_options = None

    def launch(self, **kwargs):
        self.launch_options = kwargs
        return self.browser


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright):
        self.playwright = playwright

    def start(self):
        return self.playwright


def make_session(html):
    page = FakePage(html)
    context = FakeContext(page)
    browser = FakeBrowser(context)
    chromium = FakeChromium(browser)
    playwright = FakePlaywright(chromium)
    factory = lambda: FakePlaywrightManager(playwright)
    session = BrowserSession(
        {"cookies": [{"name": "JSESSIONID", "value": "abc"}], "origins": []},
        playwright_factory=factory,
    )
    return session, page, context, browser, chromium, playwright


def test_start_restores_storage_state_and_validates_score_page():
    session, page, context, browser, chromium, playwright = make_session(
        "<html><table id='table3'></table></html>"
    )

    assert session.start(SCORE_URL) is True
    assert chromium.launch_options == {"headless": True}
    assert browser.new_context_options["storage_state"]["cookies"][0]["name"] == "JSESSIONID"
    assert page.visited[0][0] == SCORE_URL

    session.close()
    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert playwright.stopped is True


def test_start_rejects_logged_out_page_and_closes_resources():
    session, page, context, browser, chromium, playwright = make_session(
        "<html><body>非常抱歉，您还未登陆，请先登陆系统！</body></html>"
    )

    assert session.start(SCORE_URL) is False
    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert playwright.stopped is True


def test_get_html_returns_page_content_with_referer():
    session, page, *_ = make_session("<html><table id='table3'></table></html>")
    assert session.start(SCORE_URL) is True

    page.html = "<html><body>scores</body></html>"
    html = session.get_html("https://jwc.swjtu.edu.cn/scores", referer=SCORE_URL)

    assert html == "<html><body>scores</body></html>"
    assert page.visited[-1] == (
        "https://jwc.swjtu.edu.cn/scores",
        {"wait_until": "domcontentloaded", "referer": SCORE_URL},
    )
