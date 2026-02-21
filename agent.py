import os
from groq import Groq
from memory import get_history, format_history_for_prompt, save_turn
from database import get_setting

client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "llama-3.1-8b-instant"
MAX_TOKENS = 512

SYSTEM_PROMPT = """You are Sage AI, a warm and personal assistant for {user_name}. \
Your role is to help {user_name} stay on top of their priorities, surface patterns in \
their thinking, and prompt useful reflection.

[CONVERSATION HISTORY — last {n} sessions]
{history}
[END HISTORY]

Guidelines:
- Address {user_name} by name naturally — not in every sentence, but often enough to feel personal.
- Only reference priorities or goals {user_name} has explicitly mentioned — never invent them.
- When {user_name} seems scattered or overwhelmed, ask what feels most at risk right now.
- Surface recurring themes or blockers you notice across sessions.
- Keep replies concise: 2–4 sentences unless {user_name} asks for more detail.
- Always ground your response in what {user_name} actually told you, not generic advice."""


def _build_prompt(user_name: str) -> str:
    history = get_history(limit=10)
    formatted = format_history_for_prompt(history)
    return SYSTEM_PROMPT.format(user_name=user_name, n=len(history), history=formatted), history


def run_agent(user_message: str) -> str:
    user_name = get_setting("user_name", "there")
    system_prompt, _ = _build_prompt(user_name)

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    reply = response.choices[0].message.content
    save_turn(user_message, reply)
    return reply


def stream_agent(user_message: str):
    """Yields text chunks for streaming; saves the full reply when done."""
    user_name = get_setting("user_name", "there")
    system_prompt, _ = _build_prompt(user_name)

    stream = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    full_reply = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_reply += delta
            yield delta

    save_turn(user_message, full_reply)
