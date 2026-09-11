from __future__ import annotations

import time
import uuid
from typing import Any, Callable

import structlog
from langgraph.graph import END, START, StateGraph

from core.config import settings
from core.llm import LLMClient, build_llm_client
from core.logging_config import get_logger
from core.rag import KnowledgeBase
from part1_email_agent import automated_sender, classifier, drafter, verifier
from part1_email_agent.entities import check_refund_thresholds, extract_refund_entities
from part1_email_agent.models import (
    FinalAction,
    IncomingEmail,
    Priority,
    RetrievedChunkView,
    TicketState,
    TraceEvent,
)
from part1_email_agent.mock_llm import MockLLM
from part1_email_agent.precheck import CriticalSignalDetector
from part1_email_agent.smtp_sender import EmailSender
from part1_email_agent.ticketing import TicketStore

log = get_logger(__name__)

NodeResult = tuple[dict[str, Any], str, dict[str, Any]]

def _run_node(name: str, state: TicketState, fn: Callable[[TicketState], NodeResult]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        update, outcome, detail = fn(state)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        log.error("node_failed", node=name, error=str(exc)[:300])
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "final_action": FinalAction.ROUTE_TO_HUMAN,
            "route_reason": f"pipeline_error:{name}",
            "trace": [TraceEvent(node=name, outcome="error", detail={"error": str(exc)[:300]}, elapsed_ms=elapsed_ms)],
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    log.info("node_done", node=name, outcome=outcome, elapsed_ms=elapsed_ms, **detail)
    update["trace"] = [TraceEvent(node=name, outcome=outcome, detail=detail, elapsed_ms=elapsed_ms)]
    return update

class EmailAgent:
    def __init__(
        self,
        llm: LLMClient | None = None,
        kb: KnowledgeBase | None = None,
        store: TicketStore | None = None,
        detector: CriticalSignalDetector | None = None,
        sender: EmailSender | None = None,
    ) -> None:
        self.llm = llm or build_llm_client(mock_factory=MockLLM)
        self.kb = kb or KnowledgeBase.load_or_build()
        self.store = store or TicketStore()
        self.detector = detector or CriticalSignalDetector()
        self.sender = sender or EmailSender()
        self.graph = self._build_graph()

    def _node_triage(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            result = automated_sender.check(
                state.email.sender,
                state.email.headers,
                own_addresses={settings.smtp_from_address, settings.imap_user},
            )
            if result.is_automated:
                return (
                    {
                        "final_action": FinalAction.IGNORED,
                        "route_reason": result.reason,
                        "precheck_evidence": result.evidence,
                    },
                    result.reason,
                    {"evidence": result.evidence},
                )
            return ({}, "customer_email", {})

        return _run_node("triage", state, run)

    def _node_precheck(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            text = state.email.as_text()
            outcome = self.detector.detect(text)
            if outcome.triggered:
                return (
                    {
                        "precheck_triggered": True,
                        "precheck_reason": outcome.reason,
                        "precheck_evidence": outcome.evidence,
                        "priority": Priority.CRITICAL,
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": outcome.reason,
                    },
                    "critical_signal",
                    {"reason": outcome.reason, "evidence": outcome.evidence},
                )

            is_frequent, count = self.store.is_frequent_contact(state.email.sender)
            if is_frequent:
                reason = "frequent_contact"
                evidence = f"{count} contacts in {settings.contact_frequency_window_days} days"
                return (
                    {
                        "precheck_triggered": True,
                        "precheck_reason": reason,
                        "precheck_evidence": evidence,
                        "priority": Priority.CRITICAL,
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": reason,
                    },
                    "frequent_contact",
                    {"contacts": count},
                )

            return ({"precheck_triggered": False}, "clear", {"contacts": count})

        return _run_node("precheck", state, run)

    def _node_classify(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            result = classifier.classify_email(self.llm, state.email.as_text())
            if result.top_confidence < settings.classification_confidence_threshold:
                return (
                    {
                        "classification": result,
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": "low_classification_confidence",
                    },
                    "low_confidence",
                    {"labels": result.category_names, "top_confidence": round(result.top_confidence, 2)},
                )
            return (
                {"classification": result},
                "classified",
                {"labels": result.category_names, "top_confidence": round(result.top_confidence, 2)},
            )

        return _run_node("classify", state, run)

    def _node_retrieve(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            chunks = self.kb.retrieve(state.email.as_text())
            views = [
                RetrievedChunkView(text=c.text, doc_id=c.doc_id, section=c.section, score=round(c.score, 4))
                for c in chunks
            ]
            if not views:
                return (
                    {
                        "retrieved": [],
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": "no_kb_context",
                    },
                    "no_context",
                    {"min_score": settings.retrieval_min_score},
                )
            return (
                {"retrieved": views},
                "retrieved",
                {"chunks": len(views), "sources": sorted({v.doc_id for v in views}), "top_score": views[0].score},
            )

        return _run_node("retrieve", state, run)

    def _node_refund_guard(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            categories = state.classification.category_names if state.classification else []
            if "billing" not in categories:
                return ({}, "skipped", {"why": "not a billing email"})

            entities = extract_refund_entities(self.llm, state.email.as_text())
            if not entities.mentions_refund:
                return ({"refund_entities": entities}, "no_refund_request", {})

            check = check_refund_thresholds(entities)
            if check.exceeded:
                return (
                    {
                        "refund_entities": entities,
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": check.reason,
                    },
                    "threshold_exceeded",
                    {"reason": check.reason, "detail": check.detail},
                )
            return ({"refund_entities": entities}, "within_policy_limits", {"product": entities.product})

        return _run_node("refund_guard", state, run)

    def _node_draft(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            attempt = state.draft_attempts + 1
            draft = drafter.draft_response(
                self.llm, state.email.as_text(), state.retrieved, feedback=state.revision_feedback
            )
            if draft is None:
                return (
                    {
                        "draft_attempts": attempt,
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": "no_kb_context",
                    },
                    "no_context",
                    {"attempt": attempt},
                )
            if not draft.fully_answerable:
                return (
                    {
                        "draft": draft,
                        "draft_attempts": attempt,
                        "final_action": FinalAction.ROUTE_TO_HUMAN,
                        "route_reason": "kb_context_incomplete",
                    },
                    "incomplete_context",
                    {"citations": draft.citations, "attempt": attempt},
                )
            return (
                {"draft": draft, "draft_attempts": attempt},
                "drafted" if attempt == 1 else "redrafted",
                {"citations": draft.citations, "chars": len(draft.text), "attempt": attempt},
            )

        return _run_node("draft_reply", state, run)

    @staticmethod
    def _reject_draft(
        state: TicketState,
        route_reason: str,
        outcome: str,
        problems: list[str],
        detail: dict[str, Any],
        update: dict[str, Any] | None = None,
    ) -> NodeResult:
        update = dict(update or {})
        if state.draft_attempts <= settings.max_redraft_attempts:
            update["revision_feedback"] = problems
            return update, "revise", {**detail, "attempt": state.draft_attempts}
        update.update({"final_action": FinalAction.ROUTE_TO_HUMAN, "route_reason": route_reason})
        return update, outcome, {**detail, "attempt": state.draft_attempts}

    def _node_verify(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            draft = state.draft
            citation_check = verifier.check_citations(draft, state.retrieved)
            if not citation_check.valid:
                available = sorted({chunk.doc_id for chunk in state.retrieved})
                problems = [
                    f"cited document {c} does not exist; only these IDs are valid: {available}"
                    for c in citation_check.invalid_citations
                ] or [f"no documents were cited; cite the IDs you used from {available}"]
                return self._reject_draft(
                    state, "invalid_citation", "invalid_citation", problems,
                    {"invalid": citation_check.invalid_citations, "cited": draft.citations},
                )

            result = verifier.verify_draft(self.llm, draft, state.retrieved)
            if not result.fully_grounded:
                return self._reject_draft(
                    state, "unsupported_claims", "ungrounded", result.unsupported_claims,
                    {"unsupported_claims": result.unsupported_claims},
                    update={"verification": result},
                )
            return (
                {"verification": result, "final_action": FinalAction.AUTO_REPLY, "route_reason": None},
                "grounded",
                {"attempt": state.draft_attempts},
            )

        return _run_node("verify", state, run)

    def _node_route_human(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            result = self.sender.send_acknowledgement(state.email, state.trace_id)
            return (
                {
                    "final_action": FinalAction.ROUTE_TO_HUMAN,
                    "email_sent": result.sent,
                    "send_status": result.reason,
                },
                "queued_for_human",
                {"reason": state.route_reason, "priority": state.priority.value, "ack_sent": result.sent},
            )

        return _run_node("route_human", state, run)

    def _node_auto_reply(self, state: TicketState) -> dict[str, Any]:
        def run(state: TicketState) -> NodeResult:
            result = self.sender.send_reply(state.email, state.draft.text, state.trace_id)
            return (
                {"final_action": FinalAction.AUTO_REPLY, "email_sent": result.sent, "send_status": result.reason},
                "sent" if result.sent else result.reason,
                {"citations": state.draft.citations if state.draft else [], "detail": result.detail},
            )

        return _run_node("auto_reply", state, run)

    @staticmethod
    def _after(next_node: str) -> Callable[[TicketState], str]:
        def router(state: TicketState) -> str:
            return "route_human" if state.final_action == FinalAction.ROUTE_TO_HUMAN else next_node

        return router

    @staticmethod
    def _after_verify(state: TicketState) -> str:
        if state.final_action == FinalAction.ROUTE_TO_HUMAN:
            return "route_human"
        if state.final_action == FinalAction.AUTO_REPLY:
            return "auto_reply"
        return "draft_reply"

    def _build_graph(self):
        graph = StateGraph(TicketState)
        graph.add_node("triage", self._node_triage)
        graph.add_node("precheck", self._node_precheck)
        graph.add_node("classify", self._node_classify)
        graph.add_node("retrieve", self._node_retrieve)
        graph.add_node("refund_guard", self._node_refund_guard)
        graph.add_node("draft_reply", self._node_draft)
        graph.add_node("verify", self._node_verify)
        graph.add_node("route_human", self._node_route_human)
        graph.add_node("auto_reply", self._node_auto_reply)

        graph.add_edge(START, "triage")
        graph.add_conditional_edges(
            "triage",
            lambda s: END if s.final_action == FinalAction.IGNORED else "precheck",
            {END: END, "precheck": "precheck"},
        )
        for source, target in (
            ("precheck", "classify"),
            ("classify", "retrieve"),
            ("retrieve", "refund_guard"),
            ("refund_guard", "draft_reply"),
            ("draft_reply", "verify"),
        ):
            graph.add_conditional_edges(
                source, self._after(target), {"route_human": "route_human", target: target}
            )
        graph.add_conditional_edges(
            "verify",
            self._after_verify,
            {"route_human": "route_human", "auto_reply": "auto_reply", "draft_reply": "draft_reply"},
        )

        graph.add_edge("route_human", END)
        graph.add_edge("auto_reply", END)
        return graph.compile()

    def _record_ticket(self, final: TicketState) -> None:
        payload = {
            "email": final.email.model_dump(),
            "classification": final.classification.model_dump() if final.classification else None,
            "retrieved": [chunk.model_dump() for chunk in final.retrieved],
            "draft_attempt": final.draft.model_dump() if final.draft else None,
            "draft_attempts": final.draft_attempts,
            "verification": final.verification.model_dump() if final.verification else None,
            "precheck_evidence": final.precheck_evidence,
            "error": final.error,
            "trace": [event.model_dump() for event in final.trace],
        }
        self.store.record_ticket(
            trace_id=final.trace_id,
            customer_email=final.email.sender,
            subject=final.email.subject,
            final_action=final.final_action.value if final.final_action else "route_to_human",
            route_reason=final.route_reason,
            priority=final.priority.value,
            payload=payload,
            reply_text=final.draft.text if (final.final_action == FinalAction.AUTO_REPLY and final.draft) else None,
            send_status=final.send_status,
        )

    def process_exactly_once(self, incoming: IncomingEmail, record_contact: bool = True) -> TicketState | None:
        message_id = incoming.message_id
        if message_id and not self.store.claim_message(message_id):
            log.debug("skip_message_not_claimed", message_id=message_id)
            return None
        try:
            state = self.process(incoming, record_contact=record_contact)
        except Exception as exc:
            if message_id:
                dead = self.store.release_failed_message(message_id, f"{type(exc).__name__}: {exc}")
                log.error(
                    "message_processing_failed", message_id=message_id, dead_lettered=dead, error=str(exc)[:300]
                )
            raise
        if message_id:
            self.store.mark_message_processed(message_id, state.trace_id)
        return state

    def process_new_emails(self, emails: list[IncomingEmail], record_contact: bool = True) -> list[TicketState]:
        results: list[TicketState] = []
        for incoming in emails:
            try:
                state = self.process_exactly_once(incoming, record_contact=record_contact)
            except Exception:
                continue
            if state is not None:
                results.append(state)
        return results

    def process(self, incoming: IncomingEmail, record_contact: bool = True) -> TicketState:
        state = TicketState(trace_id=uuid.uuid4().hex[:12], email=incoming)
        with structlog.contextvars.bound_contextvars(trace_id=state.trace_id):
            log.info("email_received", sender=incoming.sender, subject=incoming.subject[:80], llm=self.llm.name)

            raw_result = self.graph.invoke(state)
            final = TicketState.model_validate(raw_result)
            self._record_ticket(final)

            if record_contact and final.final_action != FinalAction.IGNORED:
                self.store.record_contact(incoming.sender, incoming.subject)

            log.info(
                "email_processed",
                action=final.final_action.value if final.final_action else None,
                reason=final.route_reason,
                draft_attempts=final.draft_attempts,
                email_sent=final.email_sent,
                send_status=final.send_status,
            )
        return final
