from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, UploadFile
from pydantic import BaseModel

from core.config import settings
from core.logging_config import configure_logging, get_logger
from core.spa import companion_ports, install_web_ui
from part1_email_agent import email_loader
from part1_email_agent import metrics as ticket_metrics
from part1_email_agent.fetch_jobs import FetchJobRegistry
from part1_email_agent.graph import EmailAgent
from part1_email_agent.models import IncomingEmail
from part1_email_agent.poller import InboxPoller
from part1_email_agent.ticketing import TicketStore

log = get_logger(__name__)
_agent: EmailAgent | None = None
_poller: "InboxPoller | None" = None
_fetch_jobs = FetchJobRegistry()

def get_agent() -> EmailAgent:
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent still starting up")
    return _agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    configure_logging()
    store = TicketStore()
    if store.count_recent_contacts("rina.wijaya@lippomall.example", window_days=3650) == 0:
        import sys

        sys.path.insert(0, str(settings.data_dir))
        from seed_db import seed

        seed()
    log.info("startup_loading_agent", llm=settings.llm_provider, embeddings=settings.embedding_backend)
    _agent = EmailAgent(store=store)
    log.info(
        "startup_complete",
        llm=_agent.llm.name,
        llm_model=getattr(_agent.llm, "active_model", None),
        kb_chunks=len(_agent.kb.chunks),
    )

    global _poller
    if settings.poll_enabled:
        _poller = InboxPoller(_agent)
        _poller.start()
    else:
        log.info("poller_disabled", reason="POLL_ENABLED not set or IMAP not configured")

    try:
        yield
    finally:
        if _poller:
            await _poller.stop()

app = FastAPI(title="Nimbus Support Email Agent", version="1.0.0", lifespan=lifespan)

class ProcessRequest(BaseModel):
    text: str | None = None
    subject: str | None = None
    body: str | None = None
    sender: str | None = None

@app.get("/api/metrics")
def metrics(window: int = Query(500, ge=1, le=5000)) -> dict:
    store = TicketStore()
    return {
        **ticket_metrics.summarize(store.list_tickets(limit=window)),
        "ticket_status": store.counts_by_status(),
        "message_attempts": store.message_attempt_counts(),
        "poller": _poller.status() if _poller else {"enabled": False},
    }

@app.get("/api/dead-letters")
def dead_letters(limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    return TicketStore().list_dead_letters(limit=limit)

@app.get("/api/health")
def health() -> dict:
    agent = get_agent()
    poller_degraded = bool(_poller and _poller.status()["degraded"])
    return {
        "status": "degraded" if poller_degraded else "ok",
        "llm_backend": agent.llm.name,
        "llm_model": getattr(agent.llm, "active_model", None),
        "embedding_backend": settings.embedding_backend,
        "kb_documents": sorted(agent.kb.document_ids),
        "kb_chunks": len(agent.kb.chunks),
        "imap_enabled": settings.imap_enabled,
        "smtp_enabled": settings.smtp_enabled,
        "poller": _poller.status() if _poller else {"enabled": False},
        "companions": companion_ports(),
        "default_tab": "part1",
    }

@app.get("/api/samples")
def list_samples() -> list[dict]:
    return [
        {"name": path.name, "subject": incoming.subject, "sender": incoming.sender, "body": incoming.body}
        for path, incoming in email_loader.load_sample_emails()
    ]

@app.post("/api/process")
def process(request: ProcessRequest) -> dict:
    if request.body and request.body.strip():
        incoming = IncomingEmail(
            sender=(request.sender or "unknown@customer.example").strip().lower(),
            subject=(request.subject or "").strip() or "(no subject)",
            body=request.body.strip(),
        )
    elif request.text and request.text.strip():
        incoming = email_loader.parse_pasted_text(request.text)
        if request.sender:
            incoming.sender = request.sender.strip().lower()
    else:
        raise HTTPException(status_code=400, detail="Email body is empty")

    return get_agent().process(incoming).model_dump(mode="json")

@app.post("/api/process-eml")
async def process_eml(file: UploadFile) -> dict:
    import email as email_module

    raw = await file.read()
    incoming = email_loader.parse_message(email_module.message_from_bytes(raw))
    return get_agent().process(incoming).model_dump(mode="json")

class HumanReply(BaseModel):
    text: str

@app.post("/api/fetch-now")
async def fetch_now(limit: int = 10) -> dict:
    if not settings.imap_enabled:
        raise HTTPException(status_code=400, detail="IMAP is not configured — set IMAP_* in .env")

    agent = get_agent()
    try:
        fetched = await asyncio.to_thread(email_loader.fetch_from_imap, limit)
    except Exception as exc:
        log.error("manual_fetch_failed", error=str(exc)[:300])
        raise HTTPException(status_code=502, detail=f"IMAP fetch failed: {exc}") from exc

    job = _fetch_jobs.create(fetched)
    log.info("manual_fetch_started", job_id=job.job_id, fetched=len(fetched))
    if fetched:
        asyncio.create_task(_fetch_jobs.run(job, agent, fetched))
    else:
        job.finished = True
    return job.as_dict()

@app.get("/api/fetch-status/{job_id}")
def fetch_status(job_id: str) -> dict:
    job = _fetch_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown or expired fetch job")
    return job.as_dict()

@app.get("/api/tickets")
def list_tickets(status: str | None = None, limit: int = 50) -> dict:
    store = TicketStore()
    return {"counts": store.counts_by_status(), "tickets": store.list_tickets(status=status, limit=limit)}

@app.get("/api/tickets/{trace_id}")
def get_ticket(trace_id: str) -> dict:
    ticket = TicketStore().get_ticket(trace_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"No ticket with trace_id {trace_id}")
    return ticket

@app.post("/api/tickets/{trace_id}/reply")
def reply_as_human(trace_id: str, reply: HumanReply) -> dict:
    if not reply.text.strip():
        raise HTTPException(status_code=400, detail="Reply text is empty")

    store = TicketStore()
    ticket = store.get_ticket(trace_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"No ticket with trace_id {trace_id}")
    if ticket["status"] != "open":
        raise HTTPException(status_code=409, detail=f"Ticket is already {ticket['status']}")

    original = IncomingEmail.model_validate(ticket["payload"]["email"])
    result = get_agent().sender.send_reply(original, reply.text, trace_id)
    store.mark_replied_by_human(trace_id, reply.text, result.reason)

    log.info("human_reply_sent", trace_id=trace_id, to=original.sender, sent=result.sent, reason=result.reason)
    return {"sent": result.sent, "send_status": result.reason, "detail": result.detail}

install_web_ui(app, default_tab="part1")
