from __future__ import annotations
from typing import List, Dict
from database import get_connection


def save_turn(user_msg: str, agent_msg: str) -> None:
    """Persist one conversation turn to SQLite."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (user_msg, agent_msg) VALUES (?, ?)",
            (user_msg, agent_msg),
        )
        conn.commit()


def get_history(limit: int = 10) -> List[Dict[str, str]]:
    """Return the last `limit` turns, oldest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT user_msg, agent_msg, created_at
            FROM conversations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    # Reverse so oldest is first (chronological order)
    return [dict(r) for r in reversed(rows)]


def format_history_for_prompt(history: List[Dict[str, str]]) -> str:
    """Convert history rows into a readable context block for the system prompt."""
    if not history:
        return "No prior conversations."

    lines: List[str] = []
    for turn in history:
        ts = turn.get("created_at", "")
        lines.append(f"[{ts}]")
        lines.append(f"User: {turn['user_msg']}")
        lines.append(f"Assistant: {turn['agent_msg']}")
        lines.append("")

    return "\n".join(lines).strip()
