from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from core.config import settings
from core.logging_config import get_logger
from part1_email_agent import email_loader
from part1_email_agent.graph import EmailAgent

log = get_logger(__name__)

DEGRADED_AFTER_FAILURES = 3

@dataclass
class PollerStats:
    running: bool = False
    cycles: int = 0
    emails_processed: int = 0
    last_poll_at: str | None = None
    last_error: str | None = None
    consecutive_failures: int = 0

class InboxPoller:
    def __init__(
        self,
        agent: EmailAgent,
        interval_seconds: float | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.agent = agent
        self.interval = interval_seconds if interval_seconds is not None else settings.poll_interval_seconds
        self.batch_size = batch_size if batch_size is not None else settings.poll_batch_size
        self.stats = PollerStats()
        self._task: asyncio.Task | None = None

    async def poll_once(self) -> int:
        emails = await asyncio.to_thread(email_loader.fetch_from_imap, self.batch_size)
        states = await asyncio.to_thread(self.agent.process_new_emails, emails)

        self.stats.cycles += 1
        self.stats.emails_processed += len(states)
        self.stats.last_poll_at = datetime.now(timezone.utc).isoformat()

        if states:
            log.info(
                "poll_processed",
                new_emails=len(states),
                fetched=len(emails),
                actions=[s.final_action.value if s.final_action else None for s in states],
            )
        return len(states)

    async def _loop(self) -> None:
        log.info("poller_started", interval_seconds=self.interval, batch_size=self.batch_size)
        self.stats.running = True
        try:
            while True:
                try:
                    await self.poll_once()
                    self.stats.last_error = None
                    self.stats.consecutive_failures = 0
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.stats.consecutive_failures += 1
                    self.stats.last_error = f"{type(exc).__name__}: {exc}"[:300]
                    log.error(
                        "poll_cycle_failed",
                        error=self.stats.last_error,
                        consecutive_failures=self.stats.consecutive_failures,
                    )
                delay = self.interval * min(2 ** self.stats.consecutive_failures, 8)
                await asyncio.sleep(delay)
        finally:
            self.stats.running = False
            log.info("poller_stopped", cycles=self.stats.cycles)

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def status(self) -> dict:
        return {
            "enabled": True,
            "running": self.stats.running,
            "degraded": self.stats.consecutive_failures >= DEGRADED_AFTER_FAILURES,
            "consecutive_failures": self.stats.consecutive_failures,
            "interval_seconds": self.interval,
            "batch_size": self.batch_size,
            "cycles": self.stats.cycles,
            "emails_processed": self.stats.emails_processed,
            "last_poll_at": self.stats.last_poll_at,
            "last_error": self.stats.last_error,
        }
