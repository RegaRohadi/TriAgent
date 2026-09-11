from __future__ import annotations

from part1_email_agent import metrics

def ticket(action, reason=None, send_status=None, trace=None):
    return {
        "final_action": action,
        "route_reason": reason,
        "send_status": send_status,
        "payload": {"trace": trace or []},
    }

def event(node, elapsed_ms, outcome="ok"):
    return {"node": node, "elapsed_ms": elapsed_ms, "outcome": outcome}

def test_summary_counts_outcomes_and_resolution_rate():
    summary = metrics.summarize([
        ticket("auto_reply", send_status="sent"),
        ticket("route_to_human", reason="unsupported_claims", send_status="sent"),
        ticket("route_to_human", reason="unsupported_claims"),
        ticket("ignored", reason="no_reply_sender"),
    ])

    assert summary["window"] == 4
    assert summary["tickets_by_action"] == {"auto_reply": 1, "route_to_human": 2, "ignored": 1}
    assert summary["auto_resolution_rate"] == round(1 / 3, 3), "ignored mail must not dilute the rate"
    assert summary["route_reasons"]["unsupported_claims"] == 2
    assert summary["send_status"] == {"sent": 2}

def test_summary_reports_node_latency_errors_and_redrafts():
    summary = metrics.summarize([
        ticket("auto_reply", trace=[event("classify", 100), event("draft_reply", 400), event("draft_reply", 600)]),
        ticket("route_to_human", trace=[event("classify", 300, outcome="error")]),
    ])

    assert summary["node_latency_ms"]["classify"] == {"count": 2, "p50": 100, "p95": 300, "max": 300}
    assert summary["node_errors"] == {"classify": 1}
    assert summary["redrafted_tickets"] == 1

def test_empty_window_is_safe():
    summary = metrics.summarize([])

    assert summary["window"] == 0
    assert summary["auto_resolution_rate"] is None
    assert summary["node_latency_ms"] == {}
