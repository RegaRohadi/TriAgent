from __future__ import annotations

import pytest

from core.rag import RetrievedChunk
from part3_doc_agent import document
from part3_doc_agent.graph import DocumentAgent
from part3_doc_agent.memory import ConversationMemory
from part3_doc_agent.mock_llm import MockAgentLLM
from part3_doc_agent.models import CalculationPlan, GroundedAnswer, RouterDecision

class StubLLM:

    name = "stub"

    def __init__(self, **by_schema):
        self.by_schema = by_schema
        self.calls: list[str] = []

    def generate_structured(self, prompt, schema, *, system=None):
        self.calls.append(schema.__name__)
        value = self.by_schema.get(schema.__name__)
        if value is None:
            raise AssertionError(f"StubLLM was asked for {schema.__name__}, which the test did not expect")
        if isinstance(value, Exception):
            raise value
        return value

@pytest.fixture(scope="module")
def kb(embedder):
    return document.build_index(embedder=embedder)

@pytest.fixture
def agent(kb):
    return DocumentAgent(llm=MockAgentLLM(), kb=kb)

@pytest.fixture
def memory(tmp_path):
    return ConversationMemory("test", session_dir=tmp_path)

@pytest.mark.parametrize(
    "question,needs_document,needs_calculation",
    [
        ("Hi, I'm Rega from the Jakarta office.", False, False),
        ("Thanks, that's really helpful!", False, False),
        ("What is my name?", False, False),
        ("How much is the Business plan per seat?", True, False),
        ("What's 15% of 4800?", False, True),
        ("We need 14 Business seats for a year. What do we pay in total?", True, True),
    ],
)
def test_router_calls_a_tool_only_when_one_is_needed(agent, memory, question, needs_document, needs_calculation):
    state = agent.chat(question, memory)

    assert state.decision is not None
    assert state.decision.needs_document is needs_document, state.decision.reasoning
    assert state.decision.needs_calculation is needs_calculation, state.decision.reasoning

def test_a_greeting_runs_no_tools_at_all(agent, memory):
    state = agent.chat("Hi there!", memory)

    assert state.tool_calls == []
    assert state.answer is not None

def test_recalling_a_name_runs_no_tools(agent, memory):
    agent.chat("Hi, I'm Rega.", memory)
    state = agent.chat("What is my name?", memory)

    assert state.tools_used == []
    assert "Rega" in state.answer.answer

def test_pure_arithmetic_runs_the_calculator_and_not_the_search(agent, memory):
    state = agent.chat("What's 15% of 4800?", memory)

    assert state.tools_used == ["calculator"]
    assert state.tool_calls[0].output == "720"

def test_a_handbook_question_searches_the_document(agent, memory):
    state = agent.chat("How much is the Business plan per seat?", memory)

    assert "document_search" in state.tools_used
    assert "calculator" not in state.tools_used
    assert state.retrieved

def test_a_turn_writes_durable_facts_to_memory(agent, memory):
    agent.chat("Hi, I'm Rega.", memory)

    assert memory.recall("name") == "Rega"

def test_memory_is_persisted_after_every_turn(agent, memory):
    agent.chat("Hi, I'm Rega.", memory)

    reloaded = ConversationMemory.load("test", session_dir=memory.session_dir)
    assert reloaded.recall("name") == "Rega"

def test_the_conversation_is_buffered(agent, memory):
    agent.chat("Hi, I'm Rega.", memory)

    assert [t.role for t in memory.turns] == ["user", "agent"]

def test_a_failing_router_still_produces_an_answer(agent, memory):
    agent.llm = StubLLM(
        RouterDecision=RuntimeError("provider exploded"),
        GroundedAnswer=GroundedAnswer(answer="I am still here.", citations=[], fully_answerable=True),
    )

    state = agent.chat("How much is Business?", memory)

    assert state.answer.answer == "I am still here."
    assert state.error is not None
    assert state.tool_calls == [], "no tool should run without a decision to run one"

def test_a_calculator_error_does_not_end_the_turn(agent, memory):
    agent.llm = StubLLM(
        RouterDecision=RouterDecision(
            needs_document=False,
            needs_calculation=True,
            calculation_expression="1 / 0",
            reasoning="forced",
        ),
        GroundedAnswer=GroundedAnswer(answer="I could not compute that.", citations=[], fully_answerable=False),
    )

    state = agent.chat("What is 1 divided by 0?", memory)

    assert state.tool_calls[0].ok is False
    assert state.tool_calls[0].error == "division by zero"
    assert state.answer is not None

def test_the_calculator_is_skipped_when_the_handbook_lacks_the_numbers(agent, memory):
    agent.llm = StubLLM(
        RouterDecision=RouterDecision(
            needs_document=True,
            needs_calculation=True,
            document_queries=["something the handbook does not price"],
            reasoning="forced",
        ),
        CalculationPlan=CalculationPlan(expression="0", explanation="The context has no rate for this."),
        GroundedAnswer=GroundedAnswer(answer="The handbook does not cover that.", citations=[], fully_answerable=False),
    )

    state = agent.chat("What does the Platinum plan cost for 40 seats?", memory)

    assert "calculator" not in state.tools_used
    assert any(event.outcome == "skipped_missing_numbers" for event in state.trace)

class StubKB:

    def __init__(self, results: dict[str, list[RetrievedChunk]]):
        self.results = results

    def retrieve(self, query, k=None, min_score=None):
        return self.results.get(query, [])[: k or 6]

def chunk(section: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(text=f"text of {section}", doc_id="KB-PLAN-100", section=section, score=score)

def test_each_query_is_guaranteed_slots_in_the_results():
    kb = StubKB(
        {
            "price": [chunk(f"price-{i}", 0.90 - i * 0.01) for i in range(6)],
            "discount": [chunk(f"discount-{i}", 0.50 - i * 0.01) for i in range(6)],
        }
    )

    hits = document.search(kb, ["price", "discount"], k=6, min_score=0.0)
    sections = [h.section for h in hits]

    assert sum(s.startswith("discount") for s in sections) == 3, sections
    assert sum(s.startswith("price") for s in sections) == 3, sections
    assert "discount-0" in sections, "the top match for the second query must survive"

def test_a_chunk_matching_several_queries_appears_once_with_its_best_score():
    shared = chunk("shared", 0.4)
    better = chunk("shared", 0.8)
    kb = StubKB({"a": [shared], "b": [better]})

    hits = document.search(kb, ["a", "b"], k=6, min_score=0.0)

    assert len(hits) == 1
    assert hits[0].score == pytest.approx(0.8)

def test_no_queries_retrieves_nothing():
    assert document.search(StubKB({}), ["", "   "]) == []

def test_the_document_is_chunked_with_citable_sections():
    chunks = document.load_chunks()
    sections = {c.section for c in chunks}

    assert all(c.doc_id == "KB-PLAN-100" for c in chunks)
    assert any(s.startswith("2.") for s in sections), sections
    assert "Preamble" in sections or len(sections) > 5
