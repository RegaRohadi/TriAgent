from __future__ import annotations

import pytest

def record(store, trace_id="t1", action="route_to_human", **overrides):
    defaults = dict(
        trace_id=trace_id,
        customer_email="Customer@Company.com",
        subject="Invoice question",
        final_action=action,
        route_reason="kb_context_incomplete",
        priority="standard",
        payload={"email": {"sender": "customer@company.com", "subject": "Invoice question", "body": "..."}},
    )
    return store.record_ticket(**{**defaults, **overrides})

def test_escalated_ticket_starts_open(store):
    record(store)
    assert store.get_ticket("t1")["status"] == "open"

def test_auto_replied_ticket_is_closed_on_arrival(store):
    record(store, action="auto_reply", reply_text="Here is your answer.", send_status="sent")

    ticket = store.get_ticket("t1")
    assert ticket["status"] == "auto_replied"
    assert ticket["replied_by"] == "agent"
    assert ticket["replied_at"]

def test_ignored_ticket_is_recorded_but_needs_nobody(store):
    record(store, action="ignored", route_reason="no_reply_sender")
    assert store.get_ticket("t1")["status"] == "ignored"

def test_customer_address_is_normalised(store):
    record(store)
    assert store.get_ticket("t1")["customer_email"] == "customer@company.com"

def test_human_reply_closes_the_ticket(store):
    record(store)

    assert store.mark_replied_by_human("t1", "Sorry for the delay — here is the answer.", "sent") is True

    ticket = store.get_ticket("t1")
    assert ticket["status"] == "resolved"
    assert ticket["replied_by"] == "human"
    assert ticket["reply_text"].startswith("Sorry for the delay")
    assert ticket["send_status"] == "sent"

def test_a_ticket_cannot_be_answered_twice(store):
    record(store)
    store.mark_replied_by_human("t1", "First answer.", "sent")

    assert store.mark_replied_by_human("t1", "Second answer.", "sent") is False
    assert store.get_ticket("t1")["reply_text"] == "First answer."

def test_auto_replied_tickets_are_not_open_for_human_reply(store):
    record(store, action="auto_reply", reply_text="Agent answer.")
    assert store.mark_replied_by_human("t1", "Human answer.", "sent") is False

def test_history_can_be_filtered_by_status(store):
    record(store, trace_id="a", action="auto_reply")
    record(store, trace_id="b", action="route_to_human")
    record(store, trace_id="c", action="ignored")

    assert [t["trace_id"] for t in store.list_tickets(status="open")] == ["b"]
    assert len(store.list_tickets()) == 3
    assert store.counts_by_status() == {"auto_replied": 1, "open": 1, "ignored": 1}

def test_history_is_newest_first(store):
    for trace_id in ("a", "b", "c"):
        record(store, trace_id=trace_id)

    assert [t["trace_id"] for t in store.list_tickets()] == ["c", "b", "a"]

def test_reprocessing_the_same_trace_does_not_duplicate(store):
    record(store)
    record(store, route_reason="something_else")

    assert len(store.list_tickets()) == 1

def test_unknown_ticket_returns_none(store):
    assert store.get_ticket("does-not-exist") is None

def test_a_claimed_message_cannot_be_claimed_again(store):
    assert store.claim_message("<m1>") is True
    assert store.claim_message("<m1>") is False, "a second worker must not pick up an in-flight message"

def test_a_processed_message_cannot_be_claimed(store):
    store.claim_message("<m1>")
    store.mark_message_processed("<m1>", "t1")

    assert store.claim_message("<m1>") is False
    assert store.message_attempt_counts() == {}

def test_a_failed_message_is_retried_then_dead_lettered(tmp_path):
    from part1_email_agent.ticketing import TicketStore

    store = TicketStore(db_path=tmp_path / "dl.db", max_message_attempts=2)

    assert store.claim_message("<poison>") is True
    assert store.release_failed_message("<poison>", "RuntimeError: boom") is False
    assert store.claim_message("<poison>") is True, "a failed message gets another attempt"
    assert store.release_failed_message("<poison>", "RuntimeError: boom") is True

    assert store.claim_message("<poison>") is False
    dead = store.list_dead_letters()
    assert [d["message_id"] for d in dead] == ["<poison>"]
    assert dead[0]["attempts"] == 2
    assert "boom" in dead[0]["last_error"]

def test_a_stale_claim_from_a_crashed_worker_is_reclaimed(tmp_path):
    from part1_email_agent.ticketing import TicketStore

    store = TicketStore(db_path=tmp_path / "stale.db", claim_ttl_seconds=60)
    store.claim_message("<m1>")
    with store._connect() as conn:
        conn.execute("UPDATE message_attempts SET updated_at = '2000-01-01T00:00:00+00:00'")

    assert store.claim_message("<m1>") is True

def test_concurrent_claims_have_exactly_one_winner(store):
    import threading

    barrier = threading.Barrier(8)
    wins: list[bool] = []

    def worker():
        barrier.wait()
        wins.append(store.claim_message("<race>"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert wins.count(True) == 1
