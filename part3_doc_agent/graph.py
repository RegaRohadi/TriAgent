from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from core.llm import LLMClient, build_llm_client
from core.logging_config import get_logger
from core.rag import KnowledgeBase
from part3_doc_agent import document, responder, router
from part3_doc_agent.memory import ConversationMemory
from part3_doc_agent.mock_llm import MockAgentLLM
from part3_doc_agent.models import AgentState, GroundedAnswer, ToolResult, TraceEvent
from part3_doc_agent.tools import run_tool

log = get_logger(__name__)

NodeResult = tuple[dict[str, Any], str, dict[str, Any]]

def _run_node(name: str, state: AgentState, fn: Callable[[AgentState], NodeResult]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        update, outcome, detail = fn(state)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        log.error("node_failed", node=name, turn_id=state.turn_id, error=str(exc)[:300])
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "trace": [TraceEvent(node=name, outcome="error", detail={"error": str(exc)[:300]}, elapsed_ms=elapsed_ms)],
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    log.info("node_done", node=name, outcome=outcome, turn_id=state.turn_id, elapsed_ms=elapsed_ms, **detail)
    update["trace"] = [TraceEvent(node=name, outcome=outcome, detail=detail, elapsed_ms=elapsed_ms)]
    return update

class DocumentAgent:
    def __init__(self, llm: LLMClient | None = None, kb: KnowledgeBase | None = None) -> None:
        self.llm = llm or build_llm_client(mock_factory=MockAgentLLM)
        self.kb = kb or document.build_index()
        self.toc = self._table_of_contents()
        self.graph = self._build_graph()

    def _table_of_contents(self) -> str:
        sections = dict.fromkeys(c.section for c in self.kb.chunks if c.section != "Preamble")
        return "\n".join(f"   - {s}" for s in sections)

    def _node_route(self, state: AgentState) -> dict[str, Any]:
        def run(state: AgentState) -> NodeResult:
            decision = router.route(self.llm, state.question, state.memory_context, self.toc)
            tools = [
                name
                for name, needed in (("document_search", decision.needs_document), ("calculator", decision.needs_calculation))
                if needed
            ]
            return (
                {"decision": decision},
                "tools:" + (",".join(tools) if tools else "none"),
                {"reasoning": decision.reasoning[:200], "facts_found": len(decision.memory_updates)},
            )

        return _run_node("route", state, run)

    def _node_retrieve(self, state: AgentState) -> dict[str, Any]:
        def run(state: AgentState) -> NodeResult:
            queries = (state.decision.document_queries if state.decision else None) or [state.question]
            query = " | ".join(queries)
            started = time.perf_counter()
            hits = document.search(self.kb, queries)
            outcome = "hits" if hits else "no_relevant_context"
            call = ToolResult(
                tool="document_search",
                tool_input=query,
                output=(
                    f"{len(hits)} section(s): " + "; ".join(dict.fromkeys(h.citation for h in hits))
                    if hits
                    else "no match above the relevance floor"
                ),
                ok=bool(hits),
                error=None if hits else "nothing in the handbook scored above the relevance floor",
                elapsed_ms=round((time.perf_counter() - started) * 1000),
            )
            return (
                {"retrieved": hits, "tool_calls": [call]},
                outcome,
                {"query": query[:120], "count": len(hits), "top_score": round(hits[0].score, 3) if hits else 0.0},
            )

        return _run_node("retrieve", state, run)

    def _node_calculate(self, state: AgentState) -> dict[str, Any]:
        def run(state: AgentState) -> NodeResult:
            decision = state.decision
            expression = decision.calculation_expression if decision else None
            plan = None

            if not expression:
                if not state.retrieved:
                    return ({}, "skipped_no_context", {"reason": "no handbook context to take numbers from"})
                plan = router.plan_calculation(
                    self.llm,
                    state.question,
                    document.format_context(state.retrieved),
                    state.memory_context,
                )
                expression = plan.expression
                if expression.strip() in {"", "0"}:
                    return (
                        {"calculation": plan},
                        "skipped_missing_numbers",
                        {"explanation": plan.explanation[:200]},
                    )

            result = run_tool("calculator", expression)
            update: dict[str, Any] = {"tool_calls": [result]}
            if plan:
                update["calculation"] = plan
            return (
                update,
                "computed" if result.ok else "tool_error",
                {"expression": expression[:120], "result": result.output, "error": result.error},
            )

        return _run_node("calculate", state, run)

    def _node_respond(self, state: AgentState) -> dict[str, Any]:
        def run(state: AgentState) -> NodeResult:
            answer = responder.respond(
                self.llm,
                state.question,
                state.memory_context,
                document.format_context(state.retrieved),
                state.tool_calls,
            )
            return (
                {"answer": answer},
                "answered" if answer.fully_answerable else "partially_answerable",
                {"citations": answer.citations, "tools_used": state.tools_used},
            )

        return _run_node("respond", state, run)

    @staticmethod
    def _after_route(state: AgentState) -> str:
        if state.decision is None:
            return "respond"
        if state.decision.needs_document:
            return "retrieve"
        if state.decision.needs_calculation:
            return "calculate"
        return "respond"

    @staticmethod
    def _after_retrieve(state: AgentState) -> str:
        return "calculate" if state.decision and state.decision.needs_calculation else "respond"

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("route", self._node_route)
        graph.add_node("retrieve", self._node_retrieve)
        graph.add_node("calculate", self._node_calculate)
        graph.add_node("respond", self._node_respond)

        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route",
            self._after_route,
            {"retrieve": "retrieve", "calculate": "calculate", "respond": "respond"},
        )
        graph.add_conditional_edges(
            "retrieve", self._after_retrieve, {"calculate": "calculate", "respond": "respond"}
        )
        graph.add_edge("calculate", "respond")
        graph.add_edge("respond", END)
        return graph.compile()

    def chat(self, question: str, memory: ConversationMemory) -> AgentState:
        state = AgentState(
            turn_id=uuid.uuid4().hex[:12],
            session_id=memory.session_id,
            question=question.strip(),
            memory_context=memory.as_prompt_context(),
        )
        log.info("turn_received", turn_id=state.turn_id, session=memory.session_id, llm=self.llm.name)

        final = AgentState.model_validate(self.graph.invoke(state))

        if final.answer is None:
            final.answer = GroundedAnswer(
                answer="Something went wrong while I was working that out. Could you ask me again?",
                citations=[],
                fully_answerable=False,
            )

        changed = memory.remember(final.decision.memory_updates) if final.decision else []
        memory.add_turn("user", final.question)
        memory.add_turn("agent", final.answer.answer)
        memory.save()
        if changed:
            final.trace.append(TraceEvent(node="memory", outcome="remembered", detail={"keys": changed}))

        log.info(
            "turn_answered",
            turn_id=final.turn_id,
            tools=final.tools_used or ["none"],
            citations=final.answer.citations,
            remembered=changed,
        )
        return final
