"""
Dual memory layer: SQLite (ordered history) + ChromaDB (semantic retrieval).
"""

import os
from typing import List, Dict, Optional

import chromadb

from database import (
    get_connection, save_summary, get_latest_summary,
    get_turn_count, save_priority as db_save_priority,
)

# ── ChromaDB setup ────────────────────────────────────────────────

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")

_chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _chroma_client.get_or_create_collection(
    name="conversation_memory",
    metadata={"hnsw:space": "cosine"},
)


# ── Save / retrieve conversation turns (SQLite) ──────────────────

def save_turn(user_msg: str, agent_msg: str, session_id: str = "default") -> None:
    """Persist a conversation turn to SQLite and embed it in ChromaDB."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO conversations (user_msg, agent_msg, session_id) VALUES (?, ?, ?)",
            (user_msg, agent_msg, session_id),
        )
        conn.commit()
        turn_id = cursor.lastrowid

    # Embed in ChromaDB for semantic retrieval
    combined = f"User: {user_msg}\nAssistant: {agent_msg}"
    _collection.add(
        documents=[combined],
        metadatas=[{"session_id": session_id, "type": "conversation", "turn_id": str(turn_id)}],
        ids=[f"conv_{session_id}_{turn_id}"],
    )

    # Trigger summarisation every 20 turns
    count = get_turn_count(session_id)
    if count > 0 and count % 20 == 0:
        _summarize(session_id, count)


def get_history(limit: int = 10, session_id: str = "default") -> List[Dict[str, str]]:
    """Retrieve the last N conversation turns in chronological order."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT user_msg, agent_msg, created_at FROM conversations "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ── Semantic search (ChromaDB) ────────────────────────────────────

def semantic_search(query: str, n_results: int = 3, session_id: str = "default") -> List[Dict]:
    """Return the top-N semantically similar past entries from ChromaDB."""
    total = _collection.count()
    if total == 0:
        return []

    results = _collection.query(
        query_texts=[query],
        n_results=min(n_results, total),
        where={"session_id": session_id},
    )

    out = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append({"document": doc, "metadata": meta, "distance": dist})
    return out


# ── Format history for prompt injection ───────────────────────────

def format_history_for_prompt(
    history: List[Dict[str, str]],
    semantic_results: Optional[List[Dict]] = None,
    summary: Optional[str] = None,
    user_name: str = "User",
) -> str:
    """Build a structured, timestamped history block for the system prompt."""
    parts: List[str] = []

    # Priority snapshot from last summarisation
    if summary:
        parts.append("[PRIORITY SNAPSHOT — auto-generated summary]")
        parts.append(summary)
        parts.append("[END SNAPSHOT]\n")

    # Semantically retrieved context (may overlap with recent history — that's fine)
    if semantic_results:
        parts.append("[RELATED PAST CONTEXT — semantically retrieved]")
        for item in semantic_results:
            parts.append(f"  {item['document']}")
        parts.append("[END RELATED CONTEXT]\n")

    # Ordered recent history with labelled timestamps
    if history:
        parts.append(f"[RECENT HISTORY — last {len(history)} exchanges]")
        for turn in history:
            ts = turn.get("created_at", "")
            parts.append(f"[{ts} — {user_name}] {turn['user_msg']}")
            parts.append(f"[{ts} — Sage] {turn['agent_msg']}")
            parts.append("")
        parts.append("[END HISTORY]")
    else:
        parts.append("No prior conversations.")

    return "\n".join(parts).strip()


# ── Summarisation ─────────────────────────────────────────────────

def _summarize(session_id: str, turn_count: int) -> None:
    """Summarise the last 20 turns into a priority snapshot."""
    from langchain_groq import ChatGroq

    history = get_history(limit=20, session_id=session_id)
    if not history:
        return

    lines = []
    for t in history:
        lines.append(f"User: {t['user_msg']}")
        lines.append(f"Assistant: {t['agent_msg']}")

    transcript = "\n".join(lines)

    summarizer = ChatGroq(model_name="llama-3.1-8b-instant", max_tokens=300)
    result = summarizer.invoke(
        f"Summarise this user's key priorities, recurring themes, and blockers "
        f"from these conversations into a concise priority snapshot (max 5 bullet points):\n\n"
        f"{transcript}"
    )
    summary_text = result.content

    # Persist to SQLite
    save_summary(session_id, summary_text, turn_count)

    # Embed in ChromaDB so it surfaces in semantic search
    _collection.add(
        documents=[f"Summary: {summary_text}"],
        metadatas=[{"session_id": session_id, "type": "summary"}],
        ids=[f"summary_{session_id}_{turn_count}"],
    )


# ── Cleanup ───────────────────────────────────────────────────────

def clear_memory(session_id: str = "default") -> None:
    """Wipe conversation history from both SQLite and ChromaDB."""
    with get_connection() as conn:
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM priorities WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM summaries WHERE session_id = ?", (session_id,))
        conn.commit()

    # Clear ChromaDB entries for this session
    try:
        ids = _collection.get(where={"session_id": session_id})["ids"]
        if ids:
            _collection.delete(ids=ids)
    except Exception:
        pass
