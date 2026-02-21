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
├── app.py           # Streamlit frontend — chat UI
├── main.py          # FastAPI app — REST endpoints (optional)
├── agent.py         # Agent core — system prompt + Groq call
├── memory.py        # Memory layer — SQLite read/write/format
├── database.py      # DB schema init
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## API (Optional)

To test via Postman or curl, run the FastAPI backend separately:

```bash
python main.py
# API live at http://localhost:8081
# Docs at   http://localhost:8081/docs
```

### POST /chat

Send a message; get a context-aware response.

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

Inspect stored conversation history.

```bash
curl http://localhost:8081/history?limit=5
```

### DELETE /history

```bash
curl -X DELETE http://localhost:8081/history
```

### GET /health

```bash
curl http://localhost:8081/health
```

---

## How the Agent Works

```
User types in Streamlit chat
    │
    ├─ Fetch last 10 turns from SQLite
    │
    ├─ Format history as context block
    │
    ├─ Inject into system prompt
    │
    ├─ Call Llama 3.1 via Groq API
    │
    ├─ Save reply to SQLite
    │
    └─ Show reply in chat bubble
```

---

## Known Limitations

| Limitation | Improvement |
|---|---|
| Single user — no session isolation | Add `session_id` to DB schema |
| Last-N turns only | Add ChromaDB for semantic search |
| No streaming | Use Groq streaming + `st.write_stream` |
| History grows unbounded | Add a cleanup/archive job |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Free at console.groq.com |
| `API_KEY` | No | — | FastAPI auth key (leave blank to disable) |
| `DB_PATH` | No | `focus_assistant.db` | SQLite file path |
