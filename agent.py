"""
LangChain-based Focus Assistant agent with ReAct reasoning loop.

The agent uses Groq (Llama 3.1) via LangChain and has two tools:
  - save_priority: persist a user priority for future recall
  - get_priorities: semantically search past priorities and conversations

Uses a ReAct (Reason + Act) loop — the agent explicitly thinks about
what to do, then decides whether to use a tool or respond directly.
"""

import os

from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_react_agent

from database import (
    get_setting,
    save_priority as db_save_priority,
    get_all_priorities,
    get_latest_summary,
)
from memory import (
    get_history,
    semantic_search,
    format_history_for_prompt,
    save_turn,
    _collection,
)

# ── LLM (lazy init) ──────────────────────────────────────────────

MODEL = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "512"))

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model_name=MODEL,
            max_tokens=MAX_TOKENS,
            streaming=True,
        )
    return _llm


# ── Tools ─────────────────────────────────────────────────────────

@tool
def save_priority(text: str) -> str:
    """Save a user priority, goal, or important item for future reference.
    Use this when the user mentions a new priority, goal, deadline, or
    something they want to track across sessions."""
    row_id = db_save_priority(text)
    _collection.add(
        documents=[f"Priority: {text}"],
        metadatas=[{"type": "priority", "session_id": "default", "priority_id": str(row_id)}],
        ids=[f"priority_{row_id}"],
    )
    return f"Saved priority: {text}"


@tool
def get_priorities(query: str) -> str:
    """Retrieve relevant past priorities and conversation context via semantic search.
    Use this when you need to recall what the user previously said about their
    goals, priorities, blockers, or recurring themes. Pass a descriptive query."""
    results = semantic_search(query, n_results=5)
    if not results:
        return "No relevant past priorities or context found."

    lines = []
    for r in results:
        lines.append(f"- {r['document']}")
    return "\n".join(lines)


TOOLS = [save_priority, get_priorities]


# ── ReAct Prompt Template ────────────────────────────────────────

REACT_PROMPT = PromptTemplate.from_template("""\
You are Sage AI, a warm and personal focus assistant for {user_name}.
Your role is to help {user_name} stay on top of their priorities, surface patterns \
in their thinking, and prompt useful reflection.

{context_block}

{cold_start_instruction}

Guidelines:
- Address {user_name} by name naturally — not in every sentence, but often enough to feel personal.
- Only reference priorities or goals {user_name} has explicitly mentioned — never invent them.
- When {user_name} seems scattered or overwhelmed, ask what feels most at risk right now.
- Surface recurring themes or blockers you notice across sessions.
- Keep replies concise: 2–4 sentences unless {user_name} asks for more detail.
- Always ground your response in what {user_name} actually told you, not generic advice.
- If the conversation history does not contain relevant context for this message, \
respond based only on what the user just said and ask a clarifying question. \
Do not fabricate past priorities or goals.

You have access to the following tools:

{tools}

To use a tool, respond with EXACTLY this format:

Thought: [your reasoning about what to do]
Action: [tool name]
Action Input: [input to the tool]

When you receive a tool result, it will appear as:
Observation: [tool result]

You can then continue reasoning or give your final answer.

When you are ready to respond to the user (no more tools needed), use EXACTLY:

Thought: I now have enough information to respond.
Final Answer: [your response to the user]

IMPORTANT: You must ALWAYS start with "Thought:" and end with either an Action or "Final Answer:".
Do NOT include any text before the first "Thought:".

Tool names: {tool_names}

Begin!

Question: {input}
{agent_scratchpad}""")


def _build_agent(user_message: str):
    """Construct the AgentExecutor with context-aware prompt."""
    user_name = get_setting("user_name", "there")
    session_id = "default"

    # Gather context
    history = get_history(limit=10, session_id=session_id)
    semantic_results = semantic_search(user_message, n_results=3, session_id=session_id)
    summary = get_latest_summary(session_id)

    # Build context block
    context_block = format_history_for_prompt(
        history, semantic_results, summary, user_name,
    )

    # Cold-start instruction
    cold_start = ""
    if not history:
        cold_start = (
            f"This is a new conversation. Start by warmly greeting {user_name} "
            f"and asking about their top 3 priorities or what they're working on right now."
        )

    # Bind the dynamic context into the prompt via partial variables
    prompt = REACT_PROMPT.partial(
        user_name=user_name,
        context_block=context_block,
        cold_start_instruction=cold_start,
    )

    agent = create_react_agent(_get_llm(), TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=5,
    )


# ── Public interface ──────────────────────────────────────────────

def run_agent(user_message: str) -> str:
    """Non-streaming agent call. Used by FastAPI /chat endpoint."""
    executor = _build_agent(user_message)
    result = executor.invoke({"input": user_message})
    reply = result["output"]
    save_turn(user_message, reply)
    return reply


def stream_agent(user_message: str):
    """Streaming agent call — yields text chunks. Used by Streamlit."""
    executor = _build_agent(user_message)
    full_reply = ""

    for event in executor.stream({"input": user_message}):
        if "output" in event:
            chunk = event["output"]
            if chunk:
                delta = chunk[len(full_reply):]
                full_reply = chunk
                if delta:
                    yield delta

    save_turn(user_message, full_reply)
