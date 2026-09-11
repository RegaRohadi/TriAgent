from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.embeddings import HashingEmbedder
from core.rag import KnowledgeBase, chunk_document
from part1_email_agent.graph import EmailAgent
from part1_email_agent.mock_llm import MockLLM
from part1_email_agent.models import FinalAction, Priority
from part1_email_agent.precheck import CriticalSignalDetector

KB_TEXT = """Document ID: KB-FAQ-002
Q3. How do I get a copy of my invoice?
Invoices are auto-emailed to your billing contact and available under Account Settings.
Q8. I was charged twice this month - can I get a refund?
Duplicate charges are always refunded in full once verified.
"""

@pytest.fixture(scope="module")
def embedder() -> HashingEmbedder:
    return HashingEmbedder()

@pytest.fixture
def agent(store, embedder) -> EmailAgent:
    chunks = chunk_document(KB_TEXT, "KB-FAQ-002", "faq_billing.pdf")
    kb = KnowledgeBase(chunks, embedder.encode([c.text for c in chunks]), embedder)
    detector = CriticalSignalDetector(embedder=embedder, threshold=2.0)
    return EmailAgent(llm=MockLLM(), kb=kb, store=store, detector=detector)

def test_automated_notification_is_dropped_before_triage(agent, make_email, store):
    state = agent.process(
        make_email("Someone signed in to your account.", subject="Security alert",
                   sender="no-reply@accounts.google.com")
    )

    assert state.final_action == FinalAction.IGNORED
    assert state.route_reason == "no_reply_sender"
    assert state.classification is None, "an ignored email must not reach the classifier"
    assert [event.node for event in state.trace] == ["triage"]
    assert store.list_tickets(status="open") == [], "automated mail must not land in the human queue"

def test_automated_mail_does_not_count_toward_contact_frequency(agent, make_email, store):
    for _ in range(5):
        agent.process(make_email("Your report is ready.", sender="notifications@service.com"))

    assert store.count_recent_contacts("notifications@service.com") == 0

def test_critical_email_skips_drafting_entirely(agent, make_email):
    state = agent.process(make_email("We suffered data loss after the sync last night."))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.route_reason == "critical_keyword:data_loss"
    assert state.priority == Priority.CRITICAL
    assert state.draft is None, "a critical email must never reach the drafting node"
    assert [event.node for event in state.trace] == ["triage", "precheck", "route_human"]

def test_frequent_contact_is_escalated_before_classification(agent, store, make_email):
    now = datetime.now(timezone.utc)
    sender = "loud@customer.example"
    for days_ago in (5, 3, 2, 1):
        store.record_contact(sender, "again", when=now - timedelta(days=days_ago))

    state = agent.process(make_email("Where is my invoice?", sender=sender))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.route_reason == "frequent_contact"
    assert state.classification is None

def test_ordinary_billing_email_gets_a_grounded_draft(agent, make_email):
    state = agent.process(make_email("Where can I download a copy of my invoice for finance?"))

    assert state.final_action == FinalAction.AUTO_REPLY
    assert state.draft is not None
    assert state.draft.citations == ["KB-FAQ-002"]
    assert state.verification.fully_grounded
    assert "classify" in [event.node for event in state.trace]

def test_empty_retrieval_escalates_instead_of_drafting(agent, make_email, monkeypatch):
    monkeypatch.setattr(agent.kb, "retrieve", lambda *a, **k: [])

    state = agent.process(make_email("Can I get a refund for the classroom training fee?"))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.route_reason == "no_kb_context"
    assert state.draft is None

def test_invalid_citation_blocks_the_reply(agent, make_email, monkeypatch):
    from part1_email_agent.models import DraftResponse

    monkeypatch.setattr(
        "part1_email_agent.drafter.draft_response",
        lambda *a, **k: DraftResponse(
            text="Per our policy you get 30 days.", citations=["KB-POLICY-999"], fully_answerable=True
        ),
    )

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.route_reason == "invalid_citation"

def test_ungrounded_claim_blocks_the_reply(agent, make_email, monkeypatch):
    from part1_email_agent.models import VerificationResult

    monkeypatch.setattr(
        "part1_email_agent.verifier.verify_draft",
        lambda *a, **k: VerificationResult(fully_grounded=False, unsupported_claims=["refunds take 3 days"]),
    )

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.route_reason == "unsupported_claims"
    assert state.verification.unsupported_claims == ["refunds take 3 days"]

def test_node_failure_degrades_to_escalation(agent, make_email, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("classifier exploded")

    monkeypatch.setattr("part1_email_agent.classifier.classify_email", boom)

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.route_reason == "pipeline_error:classify"
    assert "classifier exploded" in state.error

def test_grounded_reply_is_sent_when_smtp_is_configured(agent, make_email, monkeypatch):
    from part1_email_agent.smtp_sender import SendResult

    calls = []

    def fake_send(original, text, trace_id):
        calls.append((original.sender, text))
        return SendResult(sent=True, reason="sent")

    monkeypatch.setattr(agent.sender, "send_reply", fake_send)

    state = agent.process(make_email("Where can I download a copy of my invoice for finance?"))

    assert state.final_action == FinalAction.AUTO_REPLY
    assert state.email_sent is True
    assert state.send_status == "sent"
    assert len(calls) == 1

def test_disabled_smtp_still_returns_the_draft(agent, make_email):
    state = agent.process(make_email("Where can I download a copy of my invoice for finance?"))

    assert state.final_action == FinalAction.AUTO_REPLY
    assert state.draft is not None
    assert state.email_sent is False
    assert state.send_status == "smtp_not_configured"

def test_escalated_ticket_is_persisted_with_context(agent, store, make_email):
    agent.process(make_email("Our system is down since this morning."))

    queue = store.list_tickets(status="open")
    assert len(queue) == 1
    assert queue[0]["priority"] == "critical"
    assert queue[0]["payload"]["email"]["subject"]
    assert queue[0]["payload"]["trace"], "the agent must inherit the full decision trace"

def test_every_outcome_is_recorded_in_history(agent, store, make_email):
    agent.process(make_email("Where can I download a copy of my invoice?"))
    agent.process(make_email("We suffered data loss after the sync."))
    agent.process(make_email("Your report is ready.", sender="no-reply@svc.com"))

    counts = store.counts_by_status()
    assert counts == {"auto_replied": 1, "open": 1, "ignored": 1}

def test_auto_replied_ticket_stores_what_was_sent(agent, store, make_email):
    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    ticket = store.get_ticket(state.trace_id)
    assert ticket["status"] == "auto_replied"
    assert ticket["replied_by"] == "agent"
    assert ticket["reply_text"] == state.draft.text

def test_rejected_draft_is_revised_with_verifier_feedback(agent, make_email, monkeypatch):
    from part1_email_agent import drafter
    from part1_email_agent.models import VerificationResult

    feedback_seen = []
    real_draft = drafter.draft_response

    def recording_draft(llm, email_text, chunks, feedback=None):
        feedback_seen.append(list(feedback or []))
        return real_draft(llm, email_text, chunks, feedback=feedback)

    verdicts = iter([
        VerificationResult(fully_grounded=False, unsupported_claims=["refunds take 3 days"]),
        VerificationResult(fully_grounded=True),
    ])
    monkeypatch.setattr("part1_email_agent.drafter.draft_response", recording_draft)
    monkeypatch.setattr("part1_email_agent.verifier.verify_draft", lambda *a, **k: next(verdicts))

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert state.final_action == FinalAction.AUTO_REPLY
    assert state.draft_attempts == 2
    assert feedback_seen == [[], ["refunds take 3 days"]], "the redraft must see why the first draft failed"
    nodes = [event.node for event in state.trace]
    assert nodes.count("draft_reply") == 2 and nodes.count("verify") == 2
    assert [e.outcome for e in state.trace if e.node == "verify"] == ["revise", "grounded"]

def test_redraft_feedback_reaches_the_prompt():
    from part1_email_agent.drafter import build_prompt
    from part1_email_agent.models import RetrievedChunkView

    chunk = RetrievedChunkView(text="Invoices live in Account Settings.", doc_id="KB-FAQ-002", section="Q3", score=1.0)

    assert "refunds take 3 days" in build_prompt("Where?", [chunk], ["refunds take 3 days"])
    assert "rejected" not in build_prompt("Where?", [chunk])

def test_redraft_budget_is_bounded(agent, make_email, monkeypatch):
    from core.config import settings
    from part1_email_agent.models import VerificationResult

    monkeypatch.setattr(
        "part1_email_agent.verifier.verify_draft",
        lambda *a, **k: VerificationResult(fully_grounded=False, unsupported_claims=["invented SLA"]),
    )

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert state.draft_attempts == 1 + settings.max_redraft_attempts

def test_redraft_can_be_disabled(agent, make_email, monkeypatch):
    import dataclasses

    from core.config import settings
    from part1_email_agent.models import VerificationResult

    monkeypatch.setattr("part1_email_agent.graph.settings", dataclasses.replace(settings, max_redraft_attempts=0))
    monkeypatch.setattr(
        "part1_email_agent.verifier.verify_draft",
        lambda *a, **k: VerificationResult(fully_grounded=False, unsupported_claims=["x"]),
    )

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert state.route_reason == "unsupported_claims"
    assert state.draft_attempts == 1

def test_escalated_email_sends_an_acknowledgement(agent, store, make_email, monkeypatch):
    from part1_email_agent.smtp_sender import SendResult

    calls = []

    def fake_ack(original, trace_id):
        calls.append((original.sender, trace_id))
        return SendResult(sent=True, reason="sent")

    monkeypatch.setattr(agent.sender, "send_acknowledgement", fake_ack)

    state = agent.process(make_email("We suffered data loss after the sync last night."))

    assert state.final_action == FinalAction.ROUTE_TO_HUMAN
    assert calls == [("customer@example.com", state.trace_id)]
    assert state.email_sent is True
    ticket = store.get_ticket(state.trace_id)
    assert ticket["status"] == "open", "the acknowledgement must not close the ticket for the human"
    assert ticket["send_status"] == "sent"
    assert ticket["reply_text"] is None

def test_auto_reply_does_not_send_an_acknowledgement(agent, make_email, monkeypatch):
    monkeypatch.setattr(
        agent.sender, "send_acknowledgement", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no ack"))
    )

    state = agent.process(make_email("Where can I download a copy of my invoice for finance?"))

    assert state.final_action == FinalAction.AUTO_REPLY

def test_trace_id_is_bound_to_every_log_line_inside_the_pipeline(agent, make_email, monkeypatch):
    import structlog

    from part1_email_agent import classifier

    seen = {}
    real_classify = classifier.classify_email

    def spying_classify(llm, text):
        seen.update(structlog.contextvars.get_contextvars())
        return real_classify(llm, text)

    monkeypatch.setattr("part1_email_agent.classifier.classify_email", spying_classify)

    state = agent.process(make_email("Where can I download a copy of my invoice?"))

    assert seen.get("trace_id") == state.trace_id
    assert "trace_id" not in structlog.contextvars.get_contextvars(), "the binding must not leak past the email"
