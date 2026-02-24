import sqlite3
import os
from typing import List, Dict, Optional

DB_PATH = os.getenv("DB_PATH", "focus_assistant.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_msg   TEXT    NOT NULL,
                agent_msg  TEXT    NOT NULL,
                session_id TEXT    DEFAULT 'default',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS priorities (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT    NOT NULL,
                session_id TEXT    DEFAULT 'default',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                active     BOOLEAN DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    DEFAULT 'default',
                summary    TEXT    NOT NULL,
                turn_count INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Migrate existing conversations table — add session_id if missing
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT DEFAULT 'default'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        conn.commit()


# ── Priority helpers ──────────────────────────────────────────────

def save_priority(text: str, session_id: str = "default") -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO priorities (text, session_id) VALUES (?, ?)",
            (text, session_id),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_priorities(session_id: str = "default") -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, text, created_at, active FROM priorities WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Summary helpers ───────────────────────────────────────────────

def save_summary(session_id: str, summary: str, turn_count: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO summaries (session_id, summary, turn_count) VALUES (?, ?, ?)",
            (session_id, summary, turn_count),
        )
        conn.commit()


def get_latest_summary(session_id: str = "default") -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT summary FROM summaries WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
    return row["summary"] if row else None


def get_turn_count(session_id: str = "default") -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return row["cnt"]
