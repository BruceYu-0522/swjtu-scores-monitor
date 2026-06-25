import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class DummyResponse:
    url = "https://jwc.swjtu.edu.cn/"
    history = []
    status_code = 200
    reason = "OK"
    text = "<html><table id='table3'><tr><th>课程名称</th></tr><tr><td>数学</td></tr></table></html>"

    def raise_for_status(self):
        return None


def import_fetcher_without_network(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: DummyResponse())
    sys.modules.pop("utils.fetcher", None)
    return importlib.import_module("utils.fetcher")


def test_login_reuses_valid_saved_session(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    saved_session = {
        "user_agent": "Saved Browser User Agent",
        "cookies": [
            {
                "name": "JSESSIONID",
                "value": "abc123",
                "domain": "jwc.swjtu.edu.cn",
                "path": "/",
            }
        ]
    }

    monkeypatch.setattr(fetcher_module.session_store, "load_session", lambda: saved_session)

    client = fetcher_module.ScoreFetcher("user", "password")
    monkeypatch.setattr(client, "_validate_current_session", lambda: True)
    monkeypatch.setattr(client, "_password_login", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("password login should not run")))

    assert client.login() is True
    assert client.is_logged_in is True
    assert client.session.headers["User-Agent"] == "Saved Browser User Agent"
    assert client.session.cookies.get("JSESSIONID", domain="jwc.swjtu.edu.cn", path="/") == "abc123"


def test_login_stops_when_saved_session_is_invalid(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    monkeypatch.setattr(fetcher_module.session_store, "load_session", lambda: {"cookies": []})

    client = fetcher_module.ScoreFetcher("user", "password")
    monkeypatch.setattr(client, "_validate_current_session", lambda: False)
    monkeypatch.setattr(client, "_password_login", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("password login should not run")))

    assert client.login(max_retries=1) is False


def test_login_falls_back_to_password_when_no_saved_session(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    monkeypatch.setattr(fetcher_module.session_store, "load_session", lambda: None)

    client = fetcher_module.ScoreFetcher("user", "password")
    monkeypatch.setattr(client, "_password_login", lambda *args, **kwargs: True)

    assert client.login(max_retries=1) is True


class FakeBrowserSession:
    def __init__(self, storage_state, html="", start_result=True):
        self.storage_state = storage_state
        self.html = html
        self.start_result = start_result
        self.started_with = None
        self.html_requests = []
        self.closed = False

    def start(self, validation_url):
        self.started_with = validation_url
        return self.start_result

    def get_html(self, url, referer=None):
        self.html_requests.append((url, referer))
        return self.html

    def close(self):
        self.closed = True


def test_login_prefers_complete_browser_storage_state(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    storage_state = {
        "cookies": [{"name": "JSESSIONID", "value": "abc"}],
        "origins": [{"origin": "https://jwc.swjtu.edu.cn"}],
    }
    saved_session = {
        "storage_state": storage_state,
        "user_agent": "Saved Browser User Agent",
        "cookies": [],
    }
    monkeypatch.setattr(fetcher_module.session_store, "load_session", lambda: saved_session)

    created = []

    def browser_factory(state, user_agent=None):
        browser_session = FakeBrowserSession(state)
        browser_session.user_agent = user_agent
        created.append(browser_session)
        return browser_session

    client = fetcher_module.ScoreFetcher(
        "user",
        "password",
        browser_session_factory=browser_factory,
    )
    monkeypatch.setattr(
        client,
        "_validate_current_session",
        lambda: (_ for _ in ()).throw(
            AssertionError("requests validation should not run")
        ),
    )

    assert client.login() is True
    assert client.is_logged_in is True
    assert client.browser_session is created[0]
    assert created[0].storage_state == storage_state
    assert created[0].user_agent == "Saved Browser User Agent"
    assert created[0].started_with == fetcher_module.ALL_SCORES_URL


def test_get_all_scores_parses_html_from_browser(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    html = """
    <html><table id="table3">
      <tr><th>课程名称</th><th>教师</th><th>成绩</th></tr>
      <tr><td>高等数学</td><td>张老师</td><td>95</td></tr>
    </table></html>
    """
    browser_session = FakeBrowserSession({}, html=html)
    client = fetcher_module.ScoreFetcher("user", "password")
    client.is_logged_in = True
    client.browser_session = browser_session

    scores = client.get_all_scores()

    assert scores == [{"课程名称": "高等数学", "教师": "张老师", "成绩": "95"}]
    assert browser_session.html_requests == [
        (fetcher_module.ALL_SCORES_URL, fetcher_module.LOADING_URL)
    ]


def test_get_normal_scores_parses_html_from_browser(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    html = """
    <html><table id="table3">
      <tr><th>header</th></tr>
      <tr>
        <td>1</td><td>2</td><td>3</td><td>高等数学</td><td>5</td>
        <td>张老师</td><td>课堂测验</td><td>20%</td><td>95</td>
        <td>10</td><td>2026-06-25</td>
      </tr>
    </table></html>
    """
    browser_session = FakeBrowserSession({}, html=html)
    client = fetcher_module.ScoreFetcher("user", "password")
    client.is_logged_in = True
    client.browser_session = browser_session

    scores = client.get_normal_scores()

    assert scores[0]["课程名称"] == "高等数学"
    assert scores[0]["教师"] == "张老师"
    assert scores[0]["详情"][0]["成绩"] == "95"
    assert browser_session.html_requests == [
        (fetcher_module.NORMAL_SCORES_URL, fetcher_module.ALL_SCORES_URL)
    ]


def test_get_combined_scores_closes_browser_after_success(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    browser_session = FakeBrowserSession({})
    client = fetcher_module.ScoreFetcher("user", "password")
    client.is_logged_in = True
    client.browser_session = browser_session
    monkeypatch.setattr(
        client,
        "get_all_scores",
        lambda: [{"课程名称": "高等数学", "教师": "张老师"}],
    )
    monkeypatch.setattr(client, "get_normal_scores", lambda: [])

    assert client.get_combined_scores() == [
        {
            "课程名称": "高等数学",
            "教师": "张老师",
            "平时成绩详情": None,
            "平时成绩总结": None,
        }
    ]
    assert browser_session.closed is True


def test_get_combined_scores_closes_browser_after_failure(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    browser_session = FakeBrowserSession({})
    client = fetcher_module.ScoreFetcher("user", "password")
    client.is_logged_in = True
    client.browser_session = browser_session
    monkeypatch.setattr(
        client,
        "get_all_scores",
        lambda: (_ for _ in ()).throw(RuntimeError("page failed")),
    )

    try:
        client.get_combined_scores()
    except RuntimeError as exc:
        assert str(exc) == "page failed"
    else:
        raise AssertionError("expected get_combined_scores to fail")

    assert browser_session.closed is True
