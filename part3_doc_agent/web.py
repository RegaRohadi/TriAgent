from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from core.config import settings
from core.logging_config import configure_logging, get_logger
from part3_doc_agent.graph import DocumentAgent
from part3_doc_agent.memory import ConversationMemory, normalise_session_id

log = get_logger(__name__)

_agent: DocumentAgent | None = None

_session_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

def _lock_for(session_id: str) -> threading.Lock:
    with _locks_guard:
        return _session_locks.setdefault(session_id, threading.Lock())

def get_agent() -> DocumentAgent:
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent still starting up")
    return _agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    configure_logging()
    log.info("startup_loading_agent", llm=settings.llm_backend, embeddings=settings.embedding_backend)
    _agent = DocumentAgent()
    log.info("startup_complete", chunks=len(_agent.kb.chunks), document=settings.chat_document_path.name)
    yield

app = FastAPI(title="PointStar Document Agent", version="1.0.0", lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str
    session_id: str = Field(default="web", description="Conversation to continue; memory is keyed on it")

@app.get("/api/health")
def health() -> dict:
    agent = get_agent()
    return {
        "status": "ok",
        "llm_backend": agent.llm.name,
        "embedding_backend": settings.embedding_backend,
        "document": settings.chat_document_path.name,
        "chunks": len(agent.kb.chunks),
        "sections": agent.toc.strip().splitlines(),
        "tools": ["document_search", "calculator"],
    }

@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is empty")

    agent = get_agent()
    session_id = normalise_session_id(request.session_id)

    with _lock_for(session_id):
        memory = ConversationMemory.load(session_id)
        state = agent.chat(request.message, memory)
        profile = dict(memory.profile)

    answer = state.answer
    return {
        "turn_id": state.turn_id,
        "session_id": session_id,
        "answer": answer.answer if answer else "",
        "citations": answer.citations if answer else [],
        "fully_answerable": answer.fully_answerable if answer else False,
        "tools_used": state.tools_used,
        "routing_reason": state.decision.reasoning if state.decision else None,
        "queries": state.decision.document_queries if state.decision else [],
        "calculation": state.calculation.model_dump() if state.calculation else None,
        "tool_calls": [call.model_dump() for call in state.tool_calls],
        "retrieved": [
            {"citation": chunk.citation, "score": round(chunk.score, 3)} for chunk in state.retrieved
        ],
        "trace": [event.model_dump() for event in state.trace],
        "memory": profile,
        "error": state.error,
    }

@app.get("/api/session/{session_id}")
def get_session(session_id: str) -> dict:
    memory = ConversationMemory.load(session_id)
    return {
        "session_id": memory.session_id,
        "memory": memory.profile,
        "turns": [turn.model_dump() for turn in memory.turns],
    }

@app.delete("/api/session/{session_id}")
def clear_session(session_id: str) -> dict:
    session_id = normalise_session_id(session_id)
    with _lock_for(session_id):
        memory = ConversationMemory.load(session_id)
        memory.clear()
        memory.save()
    log.info("session_cleared", session=session_id)
    return {"session_id": session_id, "memory": {}, "turns": []}

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "chat.html").read_text(encoding="utf-8")
