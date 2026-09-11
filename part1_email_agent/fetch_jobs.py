from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.logging_config import get_logger
from part1_email_agent.graph import EmailAgent
from part1_email_agent.models import IncomingEmail

log = get_logger(__name__)

MAX_RETAINED_JOBS = 20

@dataclass
class MessageProgress:
    message_id: str | None
    subject: str
    sender: str
    status: str = "queued"
    action: str | None = None
    reason: str | None = None
    trace_id: str | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": self.sender,
            "status": self.status,
            "action": self.action,
            "reason": self.reason,
            "trace_id": self.trace_id,
            "error": self.error,
        }

@dataclass
class FetchJob:
    job_id: str
    messages: list[MessageProgress]
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished: bool = False
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "started_at": self.started_at,
            "finished": self.finished,
            "error": self.error,
            "total": len(self.messages),
            "pending": sum(1 for m in self.messages if m.status in ("queued", "processing")),
            "messages": [m.as_dict() for m in self.messages],
        }

class FetchJobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, FetchJob] = {}

    def get(self, job_id: str) -> FetchJob | None:
        return self._jobs.get(job_id)

    def create(self, emails: list[IncomingEmail]) -> FetchJob:
        job = FetchJob(
            job_id=uuid.uuid4().hex[:12],
            messages=[
                MessageProgress(message_id=e.message_id, subject=e.subject or "(no subject)", sender=e.sender)
                for e in emails
            ],
        )
        self._jobs[job.job_id] = job
        self._evict_old()
        return job

    def _evict_old(self) -> None:
        if len(self._jobs) <= MAX_RETAINED_JOBS:
            return
        for job_id in sorted(self._jobs, key=lambda j: self._jobs[j].started_at)[:-MAX_RETAINED_JOBS]:
            del self._jobs[job_id]

    async def run(self, job: FetchJob, agent: EmailAgent, emails: list[IncomingEmail]) -> None:
        try:
            for progress, incoming in zip(job.messages, emails):
                progress.status = "processing"
                try:
                    state = await asyncio.to_thread(agent.process_exactly_once, incoming)
                except Exception as exc:
                    progress.status = "failed"
                    progress.error = f"{type(exc).__name__}: {exc}"[:200]
                    log.error("fetch_job_message_failed", subject=progress.subject[:60], error=progress.error)
                    continue

                if state is None:
                    progress.status = "skipped"
                    progress.reason = "already processed or in progress elsewhere"
                    continue
                progress.status = "done"
                progress.action = state.final_action.value if state.final_action else None
                progress.reason = state.route_reason
                progress.trace_id = state.trace_id
        finally:
            job.finished = True
            log.info(
                "fetch_job_finished",
                job_id=job.job_id,
                done=sum(1 for m in job.messages if m.status == "done"),
                skipped=sum(1 for m in job.messages if m.status == "skipped"),
                failed=sum(1 for m in job.messages if m.status == "failed"),
            )
