from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS support_contacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_email TEXT NOT NULL,
    subject       TEXT,
    contacted_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contacts_email_time
    ON support_contacts (customer_email, contacted_at);

CREATE TABLE IF NOT EXISTS tickets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id       TEXT NOT NULL UNIQUE,
    customer_email TEXT NOT NULL,
    subject        TEXT,
    final_action   TEXT NOT NULL,
    route_reason   TEXT,
    priority       TEXT NOT NULL,
    status         TEXT NOT NULL,
    reply_text     TEXT,
    replied_by     TEXT,
    replied_at     TEXT,
    send_status    TEXT,
    payload        TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status, id DESC);

CREATE TABLE IF NOT EXISTS processed_messages (
    message_id   TEXT PRIMARY KEY,
    trace_id     TEXT NOT NULL,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_attempts (
    message_id  TEXT PRIMARY KEY,
    state       TEXT NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT,
    updated_at  TEXT NOT NULL
);
"""

STATUS_FOR_ACTION = {
    "auto_reply": "auto_replied",
    "route_to_human": "open",
    "ignored": "ignored",
}

class TicketStore:
    def __init__(
        self,
        db_path: Path | None = None,
        max_message_attempts: int | None = None,
        claim_ttl_seconds: int | None = None,
    ) -> None:
        self.db_path = db_path or settings.db_path
        self.max_message_attempts = max_message_attempts or settings.max_message_attempts
        self.claim_ttl_seconds = claim_ttl_seconds if claim_ttl_seconds is not None else settings.message_claim_ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
        self._backfill_processed_messages()

    def _backfill_processed_messages(self) -> None:
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM processed_messages LIMIT 1").fetchone():
                return
            rows = conn.execute("SELECT trace_id, payload, created_at FROM tickets").fetchall()

            seeded = [
                (message_id, row["trace_id"], row["created_at"])
                for row in rows
                if (message_id := (json.loads(row["payload"]).get("email") or {}).get("message_id"))
            ]
            if seeded:
                conn.executemany(
                    """INSERT INTO processed_messages (message_id, trace_id, processed_at)
                       VALUES (?, ?, ?) ON CONFLICT(message_id) DO NOTHING""",
                    seeded,
                )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_contact(self, customer_email: str, subject: str, when: datetime | None = None) -> None:
        when = when or datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO support_contacts (customer_email, subject, contacted_at) VALUES (?, ?, ?)",
                (customer_email.lower(), subject, when.isoformat()),
            )

    def count_recent_contacts(self, customer_email: str, window_days: int | None = None) -> int:
        window_days = window_days or settings.contact_frequency_window_days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM support_contacts WHERE customer_email = ? AND contacted_at >= ?",
                (customer_email.lower(), cutoff),
            ).fetchone()
        return int(row["n"])

    def is_frequent_contact(self, customer_email: str) -> tuple[bool, int]:
        count = self.count_recent_contacts(customer_email)
        return count > settings.contact_frequency_threshold, count

    def record_ticket(
        self,
        trace_id: str,
        customer_email: str,
        subject: str,
        final_action: str,
        route_reason: str | None,
        priority: str,
        payload: dict[str, Any],
        reply_text: str | None = None,
        send_status: str | None = None,
    ) -> int:
        status = STATUS_FOR_ACTION.get(final_action, "open")
        now = datetime.now(timezone.utc).isoformat()
        replied_by = "agent" if status == "auto_replied" else None
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO tickets
                   (trace_id, customer_email, subject, final_action, route_reason, priority,
                    status, reply_text, replied_by, replied_at, send_status, payload, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(trace_id) DO NOTHING""",
                (
                    trace_id,
                    customer_email.lower(),
                    subject,
                    final_action,
                    route_reason,
                    priority,
                    status,
                    reply_text,
                    replied_by,
                    now if replied_by else None,
                    send_status,
                    json.dumps(payload, ensure_ascii=False, default=str),
                    now,
                ),
            )
        return int(cursor.lastrowid)

    @staticmethod
    def _row_to_ticket(row: sqlite3.Row) -> dict[str, Any]:
        return {**dict(row), "payload": json.loads(row["payload"])}

    def list_tickets(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        query = "SELECT * FROM tickets"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_ticket(row) for row in rows]

    def get_ticket(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE trace_id = ?", (trace_id,)).fetchone()
        return self._row_to_ticket(row) if row else None

    def mark_replied_by_human(self, trace_id: str, reply_text: str, send_status: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE tickets
                   SET status = 'resolved', reply_text = ?, replied_by = 'human',
                       replied_at = ?, send_status = ?
                   WHERE trace_id = ? AND status = 'open'""",
                (reply_text, datetime.now(timezone.utc).isoformat(), send_status, trace_id),
            )
        return cursor.rowcount > 0

    def is_message_processed(self, message_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,)
            ).fetchone()
        return row is not None

    def claim_message(self, message_id: str) -> bool:
        now = datetime.now(timezone.utc)
        stale_before = (now - timedelta(seconds=self.claim_ttl_seconds)).isoformat()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,)).fetchone():
                return False
            row = conn.execute(
                "SELECT state, attempts, updated_at FROM message_attempts WHERE message_id = ?", (message_id,)
            ).fetchone()
            if row:
                if row["state"] == "dead":
                    return False
                if row["state"] == "processing" and row["updated_at"] > stale_before:
                    return False
                if row["attempts"] >= self.max_message_attempts:
                    conn.execute(
                        "UPDATE message_attempts SET state = 'dead', updated_at = ? WHERE message_id = ?",
                        (now.isoformat(), message_id),
                    )
                    return False
            conn.execute(
                """INSERT INTO message_attempts (message_id, state, attempts, updated_at)
                   VALUES (?, 'processing', 1, ?)
                   ON CONFLICT(message_id) DO UPDATE
                   SET state = 'processing', attempts = attempts + 1, updated_at = excluded.updated_at""",
                (message_id, now.isoformat()),
            )
        return True

    def release_failed_message(self, message_id: str, error: str) -> bool:
        with self._connect() as conn:
            conn.execute(
                """UPDATE message_attempts
                   SET state = CASE WHEN attempts >= ? THEN 'dead' ELSE 'failed' END,
                       last_error = ?, updated_at = ?
                   WHERE message_id = ?""",
                (self.max_message_attempts, error[:500], datetime.now(timezone.utc).isoformat(), message_id),
            )
            row = conn.execute("SELECT state FROM message_attempts WHERE message_id = ?", (message_id,)).fetchone()
        return bool(row and row["state"] == "dead")

    def mark_message_processed(self, message_id: str, trace_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO processed_messages (message_id, trace_id, processed_at)
                   VALUES (?, ?, ?) ON CONFLICT(message_id) DO NOTHING""",
                (message_id, trace_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.execute("DELETE FROM message_attempts WHERE message_id = ?", (message_id,))

    def list_dead_letters(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM message_attempts WHERE state = 'dead' ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def message_attempt_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT state, COUNT(*) AS n FROM message_attempts GROUP BY state").fetchall()
        return {row["state"]: int(row["n"]) for row in rows}

    def counts_by_status(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT status, COUNT(*) AS n FROM tickets GROUP BY status").fetchall()
        return {row["status"]: int(row["n"]) for row in rows}
