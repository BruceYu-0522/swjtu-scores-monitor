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
