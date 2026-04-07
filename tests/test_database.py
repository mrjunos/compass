"""
Unit tests for backend/database.py.
Uses a real in-memory SQLite database — no mocking needed.
"""

import sqlite3
import pytest
from unittest.mock import patch
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Isolated database in a temp directory for each test."""
    db_path = tmp_path / "test_compass.db"
    with patch("backend.database.DB_PATH", db_path):
        from backend.database import init_db, save_message, get_session_messages
        init_db()
        yield {"save": save_message, "get": get_session_messages, "path": db_path}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_messages_table_exists(self, db):
        conn = sqlite3.connect(str(db["path"]))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        ).fetchone()
        conn.close()
        assert tables is not None

    def test_session_id_index_exists(self, db):
        conn = sqlite3.connect(str(db["path"]))
        idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_messages_session_id'"
        ).fetchone()
        conn.close()
        assert idx is not None


# ---------------------------------------------------------------------------
# save_message / get_session_messages
# ---------------------------------------------------------------------------

class TestMessages:
    def test_save_returns_id(self, db):
        msg_id = db["save"]("s1", "user", "hello")
        assert isinstance(msg_id, int)
        assert msg_id > 0

    def test_get_returns_saved_messages(self, db):
        db["save"]("s1", "user", "hello")
        db["save"]("s1", "assistant", "hi there")
        msgs = db["get"]("s1")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_get_returns_chronological_order(self, db):
        db["save"]("s1", "user", "first")
        db["save"]("s1", "assistant", "second")
        db["save"]("s1", "user", "third")
        msgs = db["get"]("s1")
        assert [m["content"] for m in msgs] == ["first", "second", "third"]

    def test_get_isolates_by_session(self, db):
        db["save"]("session-a", "user", "message A")
        db["save"]("session-b", "user", "message B")
        assert len(db["get"]("session-a")) == 1
        assert db["get"]("session-a")[0]["content"] == "message A"

    def test_get_respects_limit(self, db):
        for i in range(10):
            db["save"]("s1", "user", f"msg {i}")
        msgs = db["get"]("s1", limit=3)
        assert len(msgs) == 3

    def test_get_returns_most_recent_when_limited(self, db):
        for i in range(5):
            db["save"]("s1", "user", f"msg {i}")
        msgs = db["get"]("s1", limit=2)
        assert msgs[0]["content"] == "msg 3"
        assert msgs[1]["content"] == "msg 4"

    def test_get_empty_session_returns_empty_list(self, db):
        assert db["get"]("nonexistent") == []
