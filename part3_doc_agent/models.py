from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, Field

class MemoryFact(BaseModel):

    key: str = Field(description="Short snake_case identifier, e.g. name, company, plan, seat_count")
    value: str = Field(description="The value as the user stated it, e.g. Rega")

class RouterDecision(BaseModel):
    needs_document: bool = Field(
        description="True only if answering requires a fact from the handbook (a price, limit, rate, term or rule)"
    )
    needs_calculation: bool = Field(
        description="True only if answering requires arithmetic. Recalling a number is not arithmetic."
    )
    document_queries: list[str] = Field(
        default_factory=list,
        description=(
            "One standalone search query per distinct fact needed, with pronouns and follow-up references "
            "resolved from the conversation. Two facts means two queries. Empty when needs_document is false."
        ),
    )
    calculation_expression: str | None = Field(
        default=None,
        description=(
            "Plain arithmetic to evaluate, e.g. '14 * 14.50 * 12'. Digits and + - * / % ( ) only — no words, "
            "no units, no currency symbols. Null when the numbers must come from the handbook first, "
            "or when needs_calculation is false."
        ),
    )
    memory_updates: list[MemoryFact] = Field(
        default_factory=list,
        description="Durable facts the user revealed about themselves this turn. Empty when they revealed none.",
    )
    reasoning: str = Field(description="One short sentence explaining the tool choice, including choosing no tool")

class CalculationPlan(BaseModel):

    expression: str = Field(description="Plain arithmetic using numbers taken from the provided context")
    explanation: str = Field(description="One line naming where each number came from")

class GroundedAnswer(BaseModel):
    answer: str = Field(description="The reply to the user, grounded only in the provided context and memory")
    citations: list[str] = Field(
        default_factory=list,
        description="Handbook sections actually used, e.g. ['KB-PLAN-100 §3. Billing Cycles and the Annual Discount']",
    )
    fully_answerable: bool = Field(description="False if the provided context does not fully answer the question")

class Turn(BaseModel):
    role: str
    content: str
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TraceEvent(BaseModel):
    node: str
    outcome: str
    detail: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: int = 0
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ToolResult(BaseModel):

    tool: str
    tool_input: str
    output: str | None = None
    ok: bool = True
    error: str | None = None
    elapsed_ms: int = 0

class RetrievedChunkView(BaseModel):
    text: str
    doc_id: str
    section: str
    score: float

    @property
    def citation(self) -> str:
        return f"{self.doc_id} §{self.section}" if self.section else self.doc_id

class AgentState(BaseModel):
    turn_id: str
    session_id: str
    question: str

    memory_context: str = ""

    decision: RouterDecision | None = None
    retrieved: list[RetrievedChunkView] = Field(default_factory=list)
    calculation: CalculationPlan | None = None
    answer: GroundedAnswer | None = None

    error: str | None = None

    tool_calls: Annotated[list[ToolResult], operator.add] = Field(default_factory=list)
    trace: Annotated[list[TraceEvent], operator.add] = Field(default_factory=list)

    @property
    def tools_used(self) -> list[str]:
        return [t.tool for t in self.tool_calls]
