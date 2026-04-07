import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("data/compass.db")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                indexed     BOOLEAN DEFAULT FALSE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_message(session_id: str, role: str, content: str) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        return cursor.lastrowid


def get_session_messages(session_id: str, limit: int = 10) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT role, content FROM messages
               WHERE session_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def mark_indexed(message_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE messages SET indexed = TRUE WHERE id = ?", (message_id,))
