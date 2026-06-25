import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bootstrap_session


def test_browser_launch_options_include_proxy(monkeypatch):
    monkeypatch.setenv("SWJTU_BROWSER_PROXY", "socks5://127.0.0.1:1080")

    assert bootstrap_session.build_browser_launch_options() == {
        "headless": False,
        "proxy": {"server": "socks5://127.0.0.1:1080"},
    }


def test_browser_launch_options_without_proxy(monkeypatch):
    monkeypatch.delenv("SWJTU_BROWSER_PROXY", raising=False)

    assert bootstrap_session.build_browser_launch_options() == {"headless": False}


def test_capture_storage_state_includes_indexed_db():
    class FakeContext:
        def __init__(self):
            self.indexed_db = None

        def storage_state(self, indexed_db=False):
            self.indexed_db = indexed_db
            return {
                "cookies": [{"name": "JSESSIONID", "value": "abc"}],
                "origins": [{"origin": "https://jwc.swjtu.edu.cn"}],
            }

    context = FakeContext()

    state = bootstrap_session.capture_storage_state(context)

    assert context.indexed_db is True
    assert state["cookies"][0]["name"] == "JSESSIONID"
    assert state["origins"][0]["origin"] == "https://jwc.swjtu.edu.cn"


def test_capture_storage_state_supports_older_playwright():
    class FakeContext:
        def __init__(self):
            self.calls = 0

        def storage_state(self, **kwargs):
            self.calls += 1
            if kwargs:
                raise TypeError("indexed_db is unsupported")
            return {"cookies": [], "origins": []}

    context = FakeContext()

    assert bootstrap_session.capture_storage_state(context) == {
        "cookies": [],
        "origins": [],
    }
    assert context.calls == 2
