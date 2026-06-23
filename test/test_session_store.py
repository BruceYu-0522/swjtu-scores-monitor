import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import session_store


def test_session_round_trip_encrypts_gist_payload(monkeypatch):
    saved = {}

    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "test-key-that-is-long-enough")
    monkeypatch.setattr(session_store.database, "save_file", lambda name, content: saved.update({name: content}) or "ok")
    monkeypatch.setattr(session_store.database, "get_file", lambda name: saved.get(name))

    session = {
        "created_at": "2026-06-23T00:00:00+00:00",
        "cookies": [{"name": "JSESSIONID", "value": "secret-cookie", "domain": "jwc.swjtu.edu.cn"}],
    }

    assert session_store.save_session(session) == "ok"

    raw_payload = saved[session_store.SESSION_FILENAME]
    assert "secret-cookie" not in raw_payload
    assert json.loads(raw_payload)["version"] == 1
    assert session_store.load_session() == session


def test_load_session_returns_none_when_no_payload(monkeypatch):
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "test-key-that-is-long-enough")
    monkeypatch.setattr(session_store.database, "get_file", lambda name: None)

    assert session_store.load_session() is None
