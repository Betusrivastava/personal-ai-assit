import os
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
load_dotenv()

import groq as _groq
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel

from database import init_db
from agent import run_agent
from memory import get_history

API_KEY = os.getenv("API_KEY")


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Personal Focus Assistant",
    description="An AI agent that remembers your priorities across sessions.",
    version="1.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class HistoryItem(BaseModel):
    user_msg: str
    agent_msg: str
    created_at: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        reply = run_agent(body.message.strip())
    except _groq.AuthenticationError:
        raise HTTPException(status_code=502, detail="Invalid Groq API key.")
    except _groq.BadRequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except _groq.APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not reach Groq API.")
    return ChatResponse(response=reply)


@app.get("/history", response_model=List[HistoryItem], dependencies=[Depends(verify_api_key)])
def history(limit: int = 10):
    rows = get_history(limit=limit)
    return [HistoryItem(**r) for r in rows]


@app.delete("/history", dependencies=[Depends(verify_api_key)])
def clear_history():
    from database import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM conversations")
        conn.commit()
    return {"message": "Conversation history cleared."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
