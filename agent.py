from __future__ import annotations
import os
from groq import Groq
from memory import get_history, format_history_for_prompt, save_turn

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "llama-3.1-8b-instant"  # free & fast — swap to "llama-3.3-70b-versatile" for better quality
MAX_TOKENS = 512

SYSTEM_PROMPT_TEMPLATE = """You are a personal focus assistant. Your role is to help the user \
stay on top of their priorities, surface patterns in their thinking, and prompt useful reflection.

[CONVERSATION HISTORY — last {n} sessions]
{history}
[END HISTORY]

Guidelines:
- Only reference priorities or goals the user has explicitly mentioned — never invent them.
- When the user seems scattered or overwhelmed, ask what feels most at risk right now.
- Surface recurring themes or blockers you notice across sessions (e.g. the same task keeps getting pushed).
- Keep replies concise: 2–4 sentences unless the user asks for more detail.
- If this is the first interaction, welcome the user and ask what they want to focus on.
- Always ground your response in what the user actually told you, not generic productivity advice."""


def run_agent(user_message: str) -> str:
    """
    Core agent call:
    1. Load conversation history from SQLite
    2. Inject it into the system prompt
    3. Send to Groq (Llama3)
    4. Persist the turn and return the response
    """
    history = get_history(limit=10)
    formatted = format_history_for_prompt(history)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        n=len(history),
        history=formatted,
    )

    response = _client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    )

    agent_reply = response.choices[0].message.content

    save_turn(user_message, agent_reply)

    return agent_reply
