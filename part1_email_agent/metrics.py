from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

def _percentile(values: list[int], pct: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))
    return ordered[index]

def summarize(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    actions = Counter(t["final_action"] for t in tickets)
    route_reasons = Counter(t["route_reason"] for t in tickets if t["route_reason"])
    send_status = Counter(t["send_status"] for t in tickets if t["send_status"])

    latencies: dict[str, list[int]] = defaultdict(list)
    node_errors: Counter[str] = Counter()
    redrafted = 0
    for ticket in tickets:
        trace = ticket["payload"].get("trace") or []
        for event in trace:
            latencies[event["node"]].append(int(event.get("elapsed_ms") or 0))
            if event.get("outcome") == "error":
                node_errors[event["node"]] += 1
        if sum(1 for event in trace if event["node"] == "draft_reply") > 1:
            redrafted += 1

    handled = len(tickets) - actions.get("ignored", 0)
    return {
        "window": len(tickets),
        "tickets_by_action": dict(actions),
        "auto_resolution_rate": round(actions.get("auto_reply", 0) / handled, 3) if handled else None,
        "route_reasons": dict(route_reasons.most_common()),
        "send_status": dict(send_status),
        "redrafted_tickets": redrafted,
        "node_latency_ms": {
            node: {
                "count": len(values),
                "p50": _percentile(values, 50),
                "p95": _percentile(values, 95),
                "max": max(values),
            }
            for node, values in sorted(latencies.items())
        },
        "node_errors": dict(node_errors),
    }
