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
    assert client.session.cookies.get("JSESSIONID", domain="jwc.swjtu.edu.cn", path="/") == "abc123"


def test_login_falls_back_to_password_when_saved_session_invalid(monkeypatch):
    fetcher_module = import_fetcher_without_network(monkeypatch)
    monkeypatch.setattr(fetcher_module.session_store, "load_session", lambda: {"cookies": []})

    client = fetcher_module.ScoreFetcher("user", "password")
    monkeypatch.setattr(client, "_validate_current_session", lambda: False)
    monkeypatch.setattr(client, "_password_login", lambda *args, **kwargs: True)

    assert client.login(max_retries=1) is True
