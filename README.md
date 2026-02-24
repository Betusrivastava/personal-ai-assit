# Personal Focus Assistant

An AI agent that helps you stay on top of your priorities through natural conversation. Built with **LangChain + Groq** for agent reasoning, **ChromaDB** for semantic memory, and **SQLite** for ordered history — it remembers what you've shared across sessions and surfaces patterns, blockers, and focus suggestions based on your actual history.

---

## Architecture

```
User message
    │
    ├─ LangChain AgentExecutor receives input
    │
    ├─ Agent REASONS about what to do:
    │   ├─ Call save_priority tool   → persist goals to DB + ChromaDB
    │   └─ Call get_priorities tool  → semantic search past context
    │
    ├─ ChromaDB returns top-3 relevant past conversations
    │
    ├─ Agent generates response grounded in real context
    │
    ├─ Conversation saved to SQLite + embedded in ChromaDB
    │
    └─ Every 20 turns: auto-summarise into priority snapshot
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent Framework | LangChain `AgentExecutor` + `create_tool_calling_agent` | Reasoning loop — agent decides when to save/retrieve |
| LLM | Groq (Llama 3.1 8B Instant) | Fast inference via Groq API |
| Semantic Memory | ChromaDB (all-MiniLM-L6-v2 embeddings) | Vector search over past conversations & priorities |
| Ordered History | SQLite | Timestamped conversation log, settings, priorities |
| API | FastAPI | REST endpoints for chat, history, priorities |
| Frontend | Streamlit | Chat UI with dark/light theme, streaming |

### Agent Tools

| Tool | Description |
|------|-------------|
| `save_priority(text)` | Saves a user priority/goal to SQLite + ChromaDB for future recall |
| `get_priorities(query)` | Semantic search across all past conversations, priorities, and summaries |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Betusrivastava/personal-ai-assit.git
cd personal-ai-assit
pip install -r requirements.txt
```

> **Note:** On first run, ChromaDB will download the embedding model (~80MB). This is a one-time setup.

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run

```bash
streamlit run app.py
```

App is now live at `http://localhost:8080`

---

## File Structure

```
personal-ai-assistant/
├── app.py           # Streamlit frontend — chat UI with streaming
├── main.py          # FastAPI app — REST endpoints
├── agent.py         # LangChain AgentExecutor + tools (save_priority, get_priorities)
├── memory.py        # Dual memory layer — SQLite + ChromaDB semantic retrieval
├── database.py      # DB schema, migrations, CRUD helpers
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## API

To test via Postman or curl, run the FastAPI backend separately:

```bash
python main.py
# API live at http://localhost:8081
# Docs at   http://localhost:8081/docs
```

### POST /chat

Send a message; the agent reasons, uses tools if needed, and returns a context-aware response.

```bash
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need to finish the API refactor and prep for Friday demo"}'
```

Response:
```json
{
  "response": "Got it — two priorities this week: API refactor and Friday demo prep. Which feels more at risk right now?"
}
```

```bash
# Two days later (new session, server restarted)
curl -X POST http://localhost:8081/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quick check-in. Feeling scattered."}'
```

Response:
```json
{
  "response": "Last time you mentioned the API refactor and the Friday demo. Friday is two days away — how is the demo prep looking? Is the refactor creating blockers for it?"
}
```

### GET /history

```bash
curl http://localhost:8081/history?limit=5
```

### GET /priorities

Retrieve all saved priorities.

```bash
curl http://localhost:8081/priorities
```

### DELETE /history

Clears both SQLite history and ChromaDB embeddings.

```bash
curl -X DELETE http://localhost:8081/history
```

### GET /health

```bash
curl http://localhost:8081/health
```

---

## Memory System

The assistant uses a **dual memory architecture**:

1. **SQLite** — Ordered conversation history with timestamps. Provides the last 10 turns as recent context.
2. **ChromaDB** — Semantic vector store. Every conversation turn and priority is embedded. On each new message, the top-3 semantically similar past entries are retrieved and injected into the prompt.
3. **Auto-summarisation** — Every 20 turns, the LLM generates a priority snapshot summarising recurring themes, goals, and blockers. This summary persists and is injected at the top of the context window.

This means the agent can recall a priority mentioned 50 conversations ago if it's semantically relevant to the current message — not just the last 10 turns.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Free at console.groq.com |
| `API_KEY` | No | — | FastAPI auth key (leave blank to disable) |
| `DB_PATH` | No | `focus_assistant.db` | SQLite file path |
| `CHROMA_DIR` | No | `./chroma_db` | ChromaDB persistent storage directory |
| `MODEL_NAME` | No | `llama-3.1-8b-instant` | Groq model to use |
| `MAX_TOKENS` | No | `512` | Max tokens per LLM response |
