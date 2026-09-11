from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from part1_email_agent import web
from part1_email_agent.smtp_sender import SendResult
from part1_email_agent.ticketing import TicketStore

class StubSender:
    def __init__(self, result: SendResult):
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def send_reply(self, original, reply_text, trace_id):
        self.calls.append((original.sender, reply_text))
        return self.result

class StubAgent:
    def __init__(self, sender):
        self.sender = sender

@pytest.fixture
def client(store, monkeypatch):
    sender = StubSender(SendResult(sent=True, reason="sent"))
    monkeypatch.setattr(web, "get_agent", lambda: StubAgent(sender))
    monkeypatch.setattr(web, "TicketStore", lambda: store)
    test_client = TestClient(web.app)
    test_client.stub_sender = sender
    return test_client

def seed_ticket(store: TicketStore, trace_id="abc123", action="route_to_human"):
    store.record_ticket(
        trace_id=trace_id,
        customer_email="customer@company.com",
        subject="Invoice question",
        final_action=action,
        route_reason="kb_context_incomplete",
        priority="standard",
        payload={
            "email": {"sender": "customer@company.com", "subject": "Invoice question", "body": "Where is my invoice?"},
            "draft_attempt": {"text": "Draft the agent wrote.", "citations": ["KB-FAQ-002"], "fully_answerable": False},
        },
    )

class _ImapOn:
    imap_enabled = True

class _ImapOff:
    imap_enabled = False

def test_fetch_now_lists_messages_before_processing_them(client, monkeypatch, store):
    from part1_email_agent.models import IncomingEmail

    fetched = [
        IncomingEmail(sender="a@company.com", subject="First", body="...", message_id="<1@m>"),
        IncomingEmail(sender="b@company.com", subject="Second", body="...", message_id="<2@m>"),
    ]
    monkeypatch.setattr(web, "settings", _ImapOn())
    monkeypatch.setattr(web.email_loader, "fetch_from_imap", lambda limit: fetched)

    class SlowAgent(StubAgent):
        def process(self, incoming, record_contact=True):
            raise AssertionError("fetch-now must return before processing starts")

    agent = SlowAgent(client.stub_sender)
    agent.store = store
    monkeypatch.setattr(web, "get_agent", lambda: agent)
    monkeypatch.setattr(web._fetch_jobs, "run", lambda *a, **k: _noop())

    response = client.post("/api/fetch-now")

    assert response.status_code == 200
    job = response.json()
    assert job["total"] == 2
    assert [m["subject"] for m in job["messages"]] == ["First", "Second"]
    assert all(m["status"] == "queued" for m in job["messages"])

    status = client.get(f"/api/fetch-status/{job['job_id']}")
    assert status.status_code == 200
    assert status.json()["job_id"] == job["job_id"]

async def _noop():
    return None

def test_fetch_now_requires_imap(client, monkeypatch):
    monkeypatch.setattr(web, "settings", _ImapOff())
    assert client.post("/api/fetch-now").status_code == 400

def test_fetch_status_of_unknown_job_is_404(client):
    assert client.get("/api/fetch-status/nope").status_code == 404

def test_process_accepts_separate_subject_and_body(client, monkeypatch):
    captured = {}

    class RecordingAgent(StubAgent):
        def process(self, incoming, record_contact=True):
            captured["email"] = incoming
            from part1_email_agent.models import TicketState

            return TicketState(trace_id="t", email=incoming)

    monkeypatch.setattr(web, "get_agent", lambda: RecordingAgent(client.stub_sender))

    response = client.post(
        "/api/process",
        json={"subject": "Invoice question", "body": "Where is my invoice?", "sender": "Cust@Company.com"},
    )

    assert response.status_code == 200
    assert captured["email"].subject == "Invoice question"
    assert captured["email"].body == "Where is my invoice?"
    assert captured["email"].sender == "cust@company.com"

def test_process_still_accepts_a_raw_pasted_email(client, monkeypatch):
    captured = {}

    class RecordingAgent(StubAgent):
        def process(self, incoming, record_contact=True):
            captured["email"] = incoming
            from part1_email_agent.models import TicketState

            return TicketState(trace_id="t", email=incoming)

    monkeypatch.setattr(web, "get_agent", lambda: RecordingAgent(client.stub_sender))

    response = client.post("/api/process", json={"text": "Subject: Pasted\n\nBody here."})

    assert response.status_code == 200
    assert captured["email"].subject == "Pasted"

def test_process_rejects_an_empty_body(client):
    assert client.post("/api/process", json={"subject": "Only a subject", "body": "  "}).status_code == 400
    assert client.post("/api/process", json={}).status_code == 400

def test_history_lists_tickets_with_counts(client, store):
    seed_ticket(store, "a", "auto_reply")
    seed_ticket(store, "b", "route_to_human")

    body = client.get("/api/tickets").json()

    assert body["counts"] == {"auto_replied": 1, "open": 1}
    assert {t["trace_id"] for t in body["tickets"]} == {"a", "b"}

def test_history_can_filter_to_open_tickets(client, store):
    seed_ticket(store, "a", "auto_reply")
    seed_ticket(store, "b", "route_to_human")

    tickets = client.get("/api/tickets?status=open").json()["tickets"]

    assert [t["trace_id"] for t in tickets] == ["b"]

def test_ticket_detail_includes_the_attempted_draft(client, store):
    seed_ticket(store)

    body = client.get("/api/tickets/abc123").json()

    assert body["payload"]["draft_attempt"]["text"] == "Draft the agent wrote."

def test_unknown_ticket_is_404(client):
    assert client.get("/api/tickets/nope").status_code == 404

def test_human_reply_is_sent_and_closes_the_ticket(client, store):
    seed_ticket(store)

    response = client.post("/api/tickets/abc123/reply", json={"text": "Here is the real answer."})

    assert response.status_code == 200
    assert response.json()["sent"] is True
    assert client.stub_sender.calls == [("customer@company.com", "Here is the real answer.")]
    assert store.get_ticket("abc123")["status"] == "resolved"

def test_empty_reply_is_rejected(client, store):
    seed_ticket(store)

    assert client.post("/api/tickets/abc123/reply", json={"text": "   "}).status_code == 400
    assert store.get_ticket("abc123")["status"] == "open", "a rejected reply must not close the ticket"

def test_replying_twice_is_a_conflict(client, store):
    seed_ticket(store)
    client.post("/api/tickets/abc123/reply", json={"text": "First."})

    response = client.post("/api/tickets/abc123/reply", json={"text": "Second."})

    assert response.status_code == 409

def test_metrics_endpoint_summarises_the_ticket_history(client, store):
    seed_ticket(store, "a", "auto_reply")
    seed_ticket(store, "b", "route_to_human")
    store.claim_message("<stuck@m>")

    body = client.get("/api/metrics").json()

    assert body["window"] == 2
    assert body["tickets_by_action"] == {"auto_reply": 1, "route_to_human": 1}
    assert body["ticket_status"] == {"auto_replied": 1, "open": 1}
    assert body["message_attempts"] == {"processing": 1}
    assert "node_latency_ms" in body

def test_metrics_window_is_validated(client):
    assert client.get("/api/metrics?window=0").status_code == 422

def test_dead_letters_are_listed(client, store):
    store.claim_message("<poison@m>")
    for _ in range(store.max_message_attempts):
        store.release_failed_message("<poison@m>", "RuntimeError: boom")
        store.claim_message("<poison@m>")

    body = client.get("/api/dead-letters").json()

    assert [d["message_id"] for d in body] == ["<poison@m>"]

def test_reply_to_undeliverable_address_still_resolves_but_reports_it(client, store, monkeypatch):
    seed_ticket(store)
    client.stub_sender.result = SendResult(sent=False, reason="undeliverable_recipient", detail="reserved domain")

    body = client.post("/api/tickets/abc123/reply", json={"text": "Answer."}).json()

    assert body["sent"] is False
    assert body["send_status"] == "undeliverable_recipient"
    assert store.get_ticket("abc123")["send_status"] == "undeliverable_recipient"
