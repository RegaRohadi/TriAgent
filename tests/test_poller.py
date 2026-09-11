from __future__ import annotations

import asyncio

import pytest

from core.embeddings import HashingEmbedder
from core.rag import KnowledgeBase, chunk_document
from part1_email_agent.graph import EmailAgent
from part1_email_agent.mock_llm import MockLLM
from part1_email_agent.models import IncomingEmail
from part1_email_agent.poller import InboxPoller
from part1_email_agent.precheck import CriticalSignalDetector

KB_TEXT = """Document ID: KB-FAQ-002
Q3. How do I get a copy of my invoice?
Invoices are auto-emailed to your billing contact and available under Account Settings.
"""

@pytest.fixture
def agent(store) -> EmailAgent:
    embedder = HashingEmbedder()
    chunks = chunk_document(KB_TEXT, "KB-FAQ-002", "faq_billing.pdf")
    kb = KnowledgeBase(chunks, embedder.encode([c.text for c in chunks]), embedder)
    return EmailAgent(
        llm=MockLLM(), kb=kb, store=store,
        detector=CriticalSignalDetector(embedder=embedder, threshold=2.0),
    )

def email(message_id: str | None, body: str = "Where can I download my invoice?") -> IncomingEmail:
    return IncomingEmail(
        sender="customer@company.com", subject="Invoice question", body=body, message_id=message_id,
    )

def test_the_same_message_is_processed_only_once(agent, store):
    first = agent.process_new_emails([email("<abc@mail>")])
    second = agent.process_new_emails([email("<abc@mail>")])

    assert len(first) == 1
    assert second == [], "a second poll of the same inbox must not reprocess it"
    assert len(store.list_tickets()) == 1

def test_a_repeated_fetch_only_processes_the_new_message(agent):
    agent.process_new_emails([email("<one@mail>")])

    states = agent.process_new_emails([email("<one@mail>"), email("<two@mail>")])

    assert len(states) == 1
    assert states[0].email.message_id == "<two@mail>"

def test_email_without_message_id_is_always_processed(agent):
    agent.process_new_emails([email(None)])
    states = agent.process_new_emails([email(None)])

    assert len(states) == 1

def test_enabling_polling_does_not_reprocess_earlier_manual_runs(agent, store, tmp_path):
    from part1_email_agent.ticketing import TicketStore

    agent.process_new_emails([email("<already@mail>")])
    with store._connect() as conn:
        conn.execute("DELETE FROM processed_messages")

    reopened = TicketStore(db_path=store.db_path)

    assert reopened.is_message_processed("<already@mail>"), "existing tickets must seed the marker table"

def test_processed_marker_records_the_trace(agent, store):
    state = agent.process_new_emails([email("<abc@mail>")])[0]

    assert store.is_message_processed("<abc@mail>")
    assert not store.is_message_processed("<other@mail>")
    assert state.trace_id

class FakeLoader:

    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = 0

    def __call__(self, limit):
        self.calls += 1
        return self.batches.pop(0) if self.batches else []

def test_poll_once_returns_only_new_emails(agent, monkeypatch):
    loader = FakeLoader([[email("<a@mail>"), email("<b@mail>")], [email("<a@mail>"), email("<c@mail>")]])
    monkeypatch.setattr("part1_email_agent.email_loader.fetch_from_imap", loader)
    poller = InboxPoller(agent, interval_seconds=0.01, batch_size=5)

    assert asyncio.run(poller.poll_once()) == 2
    assert asyncio.run(poller.poll_once()) == 1
    assert poller.stats.emails_processed == 3
    assert poller.stats.cycles == 2

def test_a_failing_cycle_does_not_stop_the_loop(agent, monkeypatch):
    calls = {"n": 0}

    def flaky(limit):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("imap unreachable")
        return [email(f"<{calls['n']}@mail>")]

    monkeypatch.setattr("part1_email_agent.email_loader.fetch_from_imap", flaky)
    poller = InboxPoller(agent, interval_seconds=0.01, batch_size=5)

    async def run_briefly():
        poller.start()
        await asyncio.sleep(0.25)
        await poller.stop()

    asyncio.run(run_briefly())

    assert calls["n"] > 1, "the loop must keep polling after a failure"
    assert poller.stats.emails_processed >= 1

def test_status_reports_what_operators_need(agent, monkeypatch):
    monkeypatch.setattr("part1_email_agent.email_loader.fetch_from_imap", FakeLoader([[email("<a@mail>")]]))
    poller = InboxPoller(agent, interval_seconds=30, batch_size=7)
    asyncio.run(poller.poll_once())

    status = poller.status()
    assert status["interval_seconds"] == 30
    assert status["batch_size"] == 7
    assert status["cycles"] == 1
    assert status["emails_processed"] == 1
    assert status["last_poll_at"]
    assert status["last_error"] is None
    assert status["consecutive_failures"] == 0
    assert status["degraded"] is False

def test_repeated_cycle_failures_mark_the_poller_degraded(agent):
    poller = InboxPoller(agent, interval_seconds=30, batch_size=7)
    poller.stats.consecutive_failures = 3

    assert poller.status()["degraded"] is True

def test_a_poison_message_does_not_block_the_batch(agent, store, monkeypatch):
    original_process = agent.process

    def flaky_process(incoming, record_contact=True):
        if "poison" in incoming.body:
            raise RuntimeError("pipeline exploded")
        return original_process(incoming, record_contact)

    monkeypatch.setattr(agent, "process", flaky_process)

    states = agent.process_new_emails([email("<bad@mail>", body="poison"), email("<good@mail>")])

    assert [s.email.message_id for s in states] == ["<good@mail>"]
    assert store.message_attempt_counts() == {"failed": 1}

def test_a_poison_message_is_dead_lettered_after_its_attempt_budget(agent, store, monkeypatch):
    calls = {"n": 0}

    def always_fails(incoming, record_contact=True):
        calls["n"] += 1
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(agent, "process", always_fails)

    for _ in range(store.max_message_attempts + 2):
        agent.process_new_emails([email("<bad@mail>")])

    assert calls["n"] == store.max_message_attempts, "a dead message must stop consuming pipeline runs"
    assert [d["message_id"] for d in store.list_dead_letters()] == ["<bad@mail>"]
