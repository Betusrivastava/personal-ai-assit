# Personal Focus Assistant

A lightweight AI agent that helps you stay on top of your priorities through natural conversation. It remembers what you've shared across sessions and surfaces patterns, blockers, and focus suggestions based on your actual history — not generic advice.

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Betusrivastava/personal-ai-assit.git
cd personal-ai-assit
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GROQ_API_KEY (free at console.groq.com)
```

### 3. Run

```bash
python main.py
```

API is now live at `http://localhost:8080`
Interactive docs: `http://localhost:8080/docs`

---

## API Usage

### POST /chat

Send a message; get a context-aware response.

```bash
curl -X POST http://localhost:8080/chat \
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
curl -X POST http://localhost:8080/chat \
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

Inspect stored conversation history.

```bash
curl http://localhost:8080/history?limit=5
```

### DELETE /history

Clear all conversation history (fresh start).

```bash
curl -X DELETE http://localhost:8080/history
```

### GET /health

```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

### Optional API Key Auth

Set `API_KEY=your-secret` in `.env` to enable:

```bash
curl -X POST http://localhost:8080/chat \
  -H "X-API-Key: your-secret" \
  -H "Content-Type: application/json" \
  -d '{"message": "How am I doing?"}'
```

---

## Architecture

### File Structure

```
personal-ai-assistant/
├── main.py          # FastAPI app — endpoints, auth, lifespan
├── agent.py         # Agent core — system prompt + Groq call
├── memory.py        # Memory layer — SQLite read/write/format
├── database.py      # DB schema init
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Tech Choices & Rationale

**LLM: Groq (`llama-3.1-8b-instant`)**
Groq is free (14,400 requests/day, no credit card needed) and extremely fast — ideal for an evaluation where reviewers will run the code. Swappable to `llama-3.3-70b-versatile` for higher quality by changing one constant in `agent.py`.

**Agent Framework: Direct Groq SDK (no LangChain/CrewAI)**
The task calls for "deliberate use of agent primitives." A well-designed system prompt + memory injection layer *is* the agent. Adding a heavy framework would obscure the architecture rather than reveal it. The agent has a clear identity, behavioral guardrails, and a memory retrieval step — the three things that matter.

**Memory: SQLite**
Chose SQLite over a vector store (ChromaDB/FAISS) for these reasons:
- **Zero setup** — built into Python, no external services needed
- **Ordered recall** — conversation history is inherently sequential; a vector store adds semantic retrieval complexity that isn't needed when retrieving the last N turns
- **Persistent across restarts** — the `.db` file survives server restarts, satisfying the cross-session memory requirement
- **Right-sized** — a focus assistant has hundreds, not millions, of entries

The tradeoff: SQLite doesn't support semantic similarity search. If you wanted "remind me of everything I said about the API refactor" across 6 months of data, a vector store would be better. For the scope of this task, SQLite is the cleaner and more deliberate choice.

**Memory injection pattern:**
History is formatted as a timestamped dialogue block and injected directly into the system prompt (not as conversation history messages). This ensures the model always has full context even on the first message of a new session — which is the core cross-session memory requirement.

---

## How the Agent Works

```
POST /chat
    │
    ├─ memory.get_history(limit=10)        ← SQLite: fetch last 10 turns
    │
    ├─ memory.format_history_for_prompt()  ← Format as readable context block
    │
    ├─ agent: build system prompt          ← Inject history + persona + guardrails
    │
    ├─ groq.chat.completions.create()      ← Call Llama3 via Groq
    │
    ├─ memory.save_turn(user, agent)       ← Persist to SQLite
    │
    └─ return {"response": "..."}
```

---

## Known Limitations & What I'd Improve

| Limitation | Improvement |
|---|---|
| Single user — no session isolation | Add a `session_id` / user token to the DB schema |
| Last-N turns only (no semantic search) | Add ChromaDB to retrieve thematically relevant older turns |
| No streaming | Use Groq streaming + FastAPI `StreamingResponse` |
| History grows unbounded | Add a cleanup job or archive old turns |
| No retry logic on API errors | Wrap the Groq call with `tenacity` for retries |
| Plain text history format | Experiment with structured JSON injection for more reliable parsing |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Free API key from console.groq.com |
| `API_KEY` | No | — | Static key for endpoint auth (leave blank to disable) |
| `DB_PATH` | No | `focus_assistant.db` | Path to SQLite database file |
