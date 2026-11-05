from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from core.config import settings
from core.logging_config import configure_logging, get_logger
from part1_email_agent import email_loader
from part1_email_agent.graph import EmailAgent
from part1_email_agent.mock_llm import MockLLM
from part1_email_agent.models import FinalAction, IncomingEmail, TicketState
from part1_email_agent.ticketing import TicketStore

log = get_logger(__name__)

ACTION_MARK = {
    FinalAction.AUTO_REPLY: "[AUTO]",
    FinalAction.ROUTE_TO_HUMAN: "[HUMAN]",
    FinalAction.IGNORED: "[IGNORED]",
}

def print_result(state: TicketState, show_draft: bool = True) -> None:
    mark = ACTION_MARK.get(state.final_action, "[?]")
    print("\n" + "=" * 78)
    print(f"{mark} {state.email.subject}")
    print(f"       from {state.email.sender}   trace_id={state.trace_id}")
    print("-" * 78)

    for event in state.trace:
        detail = ", ".join(f"{k}={v}" for k, v in event.detail.items() if v not in (None, [], {}))
        print(f"  {event.node:<13} {event.outcome:<20} {event.elapsed_ms:>5}ms  {detail}")

    if state.classification:
        labels = ", ".join(f"{l.category.value}({l.confidence:.2f})" for l in state.classification.labels)
        print(f"\n  categories : {labels}")
    if state.retrieved:
        sources = ", ".join(f"{c.doc_id} §{c.section[:28]} ({c.score:.2f})" for c in state.retrieved[:3])
        print(f"  kb sources : {sources}")

    if state.final_action == FinalAction.IGNORED:
        print(f"\n  IGNORED -> not a customer email ({state.route_reason})")
        if state.precheck_evidence:
            print(f"  evidence   : {state.precheck_evidence}")
    elif state.final_action == FinalAction.ROUTE_TO_HUMAN:
        print(f"\n  ROUTED TO HUMAN -> reason: {state.route_reason}  priority: {state.priority.value}")
        if state.precheck_evidence:
            print(f"  evidence   : {state.precheck_evidence}")
        if state.draft:
            print("  (a draft was attempted and is attached to the ticket for the agent)")
    elif show_draft and state.draft:
        sent_line = {
            "sent": f"  EMAIL SENT to {state.email.sender}",
            "smtp_not_configured": "  NOT SENT — SMTP is not configured (set SMTP_* in .env to enable sending)",
            "undeliverable_recipient": f"  NOT SENT — {state.email.sender} is a reserved test domain",
            "smtp_error": "  SEND FAILED — SMTP is configured but the send attempt errored (see logs)",
        }.get(state.send_status, "")
        if sent_line:
            print(f"\n{sent_line}")
        print(f"\n  DRAFT REPLY (citations: {', '.join(state.draft.citations)}):")
        for line in state.draft.text.splitlines():
            print(f"    {line}")
    print("=" * 78)

def cmd_process(args: argparse.Namespace) -> int:
    agent = EmailAgent()
    if args.path == "-":
        incoming = email_loader.parse_pasted_text(sys.stdin.read())
    else:
        incoming = email_loader.load_eml(Path(args.path))

    state = agent.process(incoming)
    if args.json:
        print(state.model_dump_json(indent=2))
    else:
        print_result(state)
    return 0

def cmd_samples(args: argparse.Namespace) -> int:
    agent = EmailAgent()
    samples = email_loader.load_sample_emails()
    if not samples:
        print(f"No .eml files found in {settings.sample_email_dir}")
        return 1

    pacing_seconds = settings.llm_pacing_seconds

    results: list[tuple[str, TicketState]] = []
    for index, (path, incoming) in enumerate(samples):
        if index > 0 and pacing_seconds:
            time.sleep(pacing_seconds)
        state = agent.process(incoming, record_contact=False)
        results.append((path.name, state))
        if not args.summary_only:
            print_result(state)

    print("\nSUMMARY")
    print("-" * 78)
    for name, state in results:
        mark = ACTION_MARK.get(state.final_action, "[?]")
        print(f"  {mark:<8} {name:<42} {state.route_reason or 'grounded draft ready'}")
    return 0

def cmd_queue(args: argparse.Namespace) -> int:
    store = TicketStore()
    rows = store.list_tickets(status=args.status, limit=args.limit)
    counts = store.counts_by_status()
    if not rows:
        print(f"No tickets{'' if not args.status else ' with status ' + args.status}.")
        return 0

    summary = "  ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    print(f"{summary}\n")
    for row in rows:
        replied = f" replied_by={row['replied_by']}" if row["replied_by"] else ""
        print(f"#{row['id']:<4} [{row['status']:<12}] {(row['route_reason'] or '-'):<32} {(row['subject'] or '')[:38]}")
        print(f"      from {row['customer_email']}  trace_id={row['trace_id']}{replied}  at {row['created_at']}")
    return 0

def cmd_imap(args: argparse.Namespace) -> int:
    agent = EmailAgent()
    fetched = email_loader.fetch_from_imap(limit=args.limit)
    states = agent.process_new_emails(fetched, record_contact=not args.reprocess)

    skipped = len(fetched) - len(states)
    for state in states:
        print_result(state)
    if skipped:
        print(f"\nSkipped {skipped} message(s) already processed (matched by Message-ID).")
    if not states:
        print("No new emails to process.")
    return 0

def cmd_poll(args: argparse.Namespace) -> int:
    import asyncio

    from part1_email_agent.poller import InboxPoller

    poller = InboxPoller(EmailAgent(), interval_seconds=args.interval, batch_size=args.limit)

    async def run() -> None:
        if args.once:
            count = await poller.poll_once()
            print(f"Processed {count} new email(s).")
            return
        print(f"Polling every {args.interval}s. Ctrl-C to stop.")
        poller.start()
        await asyncio.Event().wait()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0

def cmd_seed(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(settings.data_dir))
    from seed_db import seed

    seed(reset=args.reset)
    return 0

def cmd_health(args: argparse.Namespace) -> int:
    from core.embeddings import get_embedder
    from core.llm import build_llm_client
    from core.rag import KnowledgeBase

    report: dict[str, object] = {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model or None,
        "llm_fallback_providers": settings.llm_fallback_providers or None,
        "embedding_backend": settings.embedding_backend,
        "imap_enabled": settings.imap_enabled,
        "smtp_enabled": settings.smtp_enabled,
    }
    try:
        embedder = get_embedder()
        report["embedder"] = f"{type(embedder).__name__} dim={embedder.dimension}"
        kb = KnowledgeBase.load_or_build(embedder=embedder)
        report["kb_chunks"] = len(kb.chunks)
        report["kb_documents"] = sorted(kb.document_ids)
        llm = build_llm_client(mock_factory=MockLLM)
        report["llm_provider"] = llm.name
        from part1_email_agent.models import ClassificationResult

        probe = llm.generate_structured(
            "Now classify this email:\nEmail:\nSubject: test\n\nMy invoice is wrong.\nOutput:",
            ClassificationResult,
        )
        active = getattr(llm, "active_model", None)
        report["llm"] = f"{llm.name} ok ({probe.category_names})"
        if active:
            report["active_model"] = active
            report["llm_model"] = active
        report["status"] = "ok"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(report, indent=2))
    return 0 if report.get("status") == "ok" else 1

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="part1_email_agent", description="Nimbus Support email agent")
    parser.add_argument("--log-json", action="store_true", help="emit machine-readable logs")
    parser.add_argument("--quiet", action="store_true", help="only warnings and errors")
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process", help="process a single .eml file or stdin")
    p_process.add_argument("path", help="path to .eml, or '-' to read from stdin")
    p_process.add_argument("--json", action="store_true", help="print the full state as JSON")
    p_process.set_defaults(func=cmd_process)

    p_samples = sub.add_parser("samples", help="process the bundled golden-set emails")
    p_samples.add_argument("--summary-only", action="store_true")
    p_samples.set_defaults(func=cmd_samples)

    p_queue = sub.add_parser("queue", help="show ticket history (all outcomes, not just escalations)")
    p_queue.add_argument("--limit", type=int, default=20)
    p_queue.add_argument(
        "--status", choices=["open", "resolved", "auto_replied", "ignored"],
        help="filter by status; omit to see everything",
    )
    p_queue.set_defaults(func=cmd_queue)

    p_imap = sub.add_parser("imap", help="fetch and process new emails from a live inbox, once")
    p_imap.add_argument("--limit", type=int, default=5)
    p_imap.add_argument(
        "--reprocess", action="store_true",
        help="do not count these emails towards the contact-frequency rule (for re-runs)",
    )
    p_imap.set_defaults(func=cmd_imap)

    p_poll = sub.add_parser("poll", help="watch the inbox continuously and process new mail")
    p_poll.add_argument("--interval", type=float, default=settings.poll_interval_seconds)
    p_poll.add_argument("--limit", type=int, default=settings.poll_batch_size)
    p_poll.add_argument("--once", action="store_true", help="run a single cycle and exit")
    p_poll.set_defaults(func=cmd_poll)

    p_seed = sub.add_parser("seed", help="seed the demo contact history")
    p_seed.add_argument("--reset", action="store_true")
    p_seed.set_defaults(func=cmd_seed)

    sub.add_parser("health", help="check LLM, embedder and knowledge base").set_defaults(func=cmd_health)

    args = parser.parse_args(argv)
    configure_logging(json_output=args.log_json, level="WARNING" if args.quiet else "INFO")
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
