from __future__ import annotations

import asyncio

import pytest

from part1_email_agent.fetch_jobs import FetchJobRegistry
from part1_email_agent.models import FinalAction, IncomingEmail, TicketState

class FakeStore:
    def __init__(self, already: set[str] | None = None):
        self.already = already or set()
        self.marked: list[str] = []

    def is_message_processed(self, message_id: str) -> bool:
        return message_id in self.already

    def mark_message_processed(self, message_id: str, trace_id: str) -> None:
        self.marked.append(message_id)

class FakeAgent:
    def __init__(self, store: FakeStore, fail_on: str | None = None):
        self.store = store
        self.fail_on = fail_on
        self.processed: list[str] = []

    def process_exactly_once(self, incoming: IncomingEmail, record_contact: bool = True) -> TicketState | None:
        if incoming.message_id in self.store.already:
            return None
        state = self.process(incoming, record_contact)
        if incoming.message_id:
            self.store.mark_message_processed(incoming.message_id, state.trace_id)
        return state

    def process(self, incoming: IncomingEmail, record_contact: bool = True) -> TicketState:
        if self.fail_on and self.fail_on in incoming.subject:
            raise RuntimeError("classifier exploded")
        self.processed.append(incoming.subject)
        return TicketState(
            trace_id=f"t-{len(self.processed)}",
            email=incoming,
            final_action=FinalAction.AUTO_REPLY,
        )

def email(subject: str, message_id: str | None = None) -> IncomingEmail:
    return IncomingEmail(
        sender="customer@company.com", subject=subject, body="...", message_id=message_id
    )

def test_job_lists_every_message_before_any_is_processed():
    registry = FetchJobRegistry()
    job = registry.create([email("First"), email("Second")])

    data = job.as_dict()
    assert data["total"] == 2
    assert data["pending"] == 2
    assert [m["subject"] for m in data["messages"]] == ["First", "Second"]
    assert all(m["status"] == "queued" for m in data["messages"])

def test_processing_marks_each_message_done():
    store = FakeStore()
    agent = FakeAgent(store)
    registry = FetchJobRegistry()
    emails = [email("First", "<1@m>"), email("Second", "<2@m>")]
    job = registry.create(emails)

    asyncio.run(registry.run(job, agent, emails))

    data = job.as_dict()
    assert data["finished"] is True
    assert data["pending"] == 0
    assert [m["status"] for m in data["messages"]] == ["done", "done"]
    assert [m["action"] for m in data["messages"]] == ["auto_reply", "auto_reply"]
    assert store.marked == ["<1@m>", "<2@m>"]

def test_processing_state_is_visible_while_a_message_is_being_classified():
    import threading

    entered, release = threading.Event(), threading.Event()

    class BlockingAgent(FakeAgent):
        def process(self, incoming, record_contact=True):
            entered.set()
            release.wait(timeout=5)
            return super().process(incoming, record_contact)

    agent = BlockingAgent(FakeStore())
    registry = FetchJobRegistry()
    emails = [email("Slow", "<1@m>"), email("Next", "<2@m>")]
    job = registry.create(emails)

    async def scenario():
        task = asyncio.create_task(registry.run(job, agent, emails))
        await asyncio.to_thread(entered.wait, 5)
        snapshot = job.as_dict()
        release.set()
        await task
        return snapshot

    snapshot = asyncio.run(scenario())

    assert [m["status"] for m in snapshot["messages"]] == ["processing", "queued"]
    assert snapshot["pending"] == 2
    assert snapshot["finished"] is False
    assert job.as_dict()["finished"] is True

def test_already_processed_messages_are_skipped_not_reprocessed():
    store = FakeStore(already={"<1@m>"})
    agent = FakeAgent(store)
    registry = FetchJobRegistry()
    emails = [email("Old", "<1@m>"), email("New", "<2@m>")]
    job = registry.create(emails)

    asyncio.run(registry.run(job, agent, emails))

    statuses = [m["status"] for m in job.as_dict()["messages"]]
    assert statuses == ["skipped", "done"]
    assert agent.processed == ["New"], "the skipped message must never reach the pipeline"

def test_one_failing_message_does_not_sink_the_batch():
    store = FakeStore()
    agent = FakeAgent(store, fail_on="Bad")
    registry = FetchJobRegistry()
    emails = [email("Bad", "<1@m>"), email("Good", "<2@m>")]
    job = registry.create(emails)

    asyncio.run(registry.run(job, agent, emails))

    messages = job.as_dict()["messages"]
    assert messages[0]["status"] == "failed"
    assert "classifier exploded" in messages[0]["error"]
    assert messages[1]["status"] == "done"
    assert job.finished is True

def test_a_failed_message_is_not_marked_processed():
    store = FakeStore()
    agent = FakeAgent(store, fail_on="Bad")
    registry = FetchJobRegistry()
    emails = [email("Bad", "<1@m>")]

    asyncio.run(registry.run(registry.create(emails), agent, emails))

    assert store.marked == []

def test_unknown_job_id_returns_nothing():
    assert FetchJobRegistry().get("does-not-exist") is None

def test_old_jobs_are_evicted():
    registry = FetchJobRegistry()
    jobs = [registry.create([email(f"E{i}")]) for i in range(25)]

    assert registry.get(jobs[-1].job_id) is not None
    assert registry.get(jobs[0].job_id) is None, "the registry must not grow without bound"
