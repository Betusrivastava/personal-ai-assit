from typing import List, Dict
from database import get_connection


def save_turn(user_msg: str, agent_msg: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (user_msg, agent_msg) VALUES (?, ?)",
            (user_msg, agent_msg),
        )
        conn.commit()


def get_history(limit: int = 10) -> List[Dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT user_msg, agent_msg, created_at FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def format_history_for_prompt(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No prior conversations."

    lines = []
    for turn in history:
        lines.append(f"[{turn.get('created_at', '')}]")
        lines.append(f"User: {turn['user_msg']}")
        lines.append(f"Assistant: {turn['agent_msg']}")
        lines.append("")

    return "\n".join(lines).strip()
