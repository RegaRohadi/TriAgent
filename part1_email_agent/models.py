from __future__ import annotations

import operator
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field

class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    FEEDBACK = "feedback"
    ACCOUNT = "account"
    GENERAL = "general"

class FinalAction(str, Enum):
    AUTO_REPLY = "auto_reply"
    ROUTE_TO_HUMAN = "route_to_human"
    IGNORED = "ignored"

class Priority(str, Enum):
    CRITICAL = "critical"
    STANDARD = "standard"

class CategoryScore(BaseModel):
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="Short quote or paraphrase from the email supporting this label")

class ClassificationResult(BaseModel):
    labels: list[CategoryScore]

    @property
    def top_confidence(self) -> float:
        return max((label.confidence for label in self.labels), default=0.0)

    @property
    def category_names(self) -> list[str]:
        return [label.category.value for label in self.labels]

class RefundEntities(BaseModel):

    mentions_refund: bool = Field(description="True if the customer asks about a refund, cancellation or money back")
    amount: float | None = Field(default=None, description="Refund amount if stated, else null")
    currency: str | None = Field(default=None, description="Currency code if stated, e.g. USD, SGD, MYR, IDR")
    purchase_date: str | None = Field(default=None, description="ISO date YYYY-MM-DD if stated, else null")
    product: str | None = Field(default=None, description="Product named by the customer, else null")

class DraftResponse(BaseModel):
    text: str = Field(description="The reply to the customer, grounded only in the provided context")
    citations: list[str] = Field(description="Document IDs used, e.g. ['KB-POLICY-001']")
    fully_answerable: bool = Field(description="False if the context does not fully answer the question")

class VerificationResult(BaseModel):
    fully_grounded: bool = Field(description="True only if every claim in the draft appears in the context")
    unsupported_claims: list[str] = Field(default_factory=list)

class TraceEvent(BaseModel):
    node: str
    outcome: str
    detail: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: int = 0
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class IncomingEmail(BaseModel):
    sender: str
    subject: str
    body: str
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    def as_text(self) -> str:
        return f"Subject: {self.subject}\n\n{self.body}".strip()

class RetrievedChunkView(BaseModel):
    text: str
    doc_id: str
    section: str
    score: float

class TicketState(BaseModel):
    trace_id: str
    email: IncomingEmail

    precheck_triggered: bool = False
    precheck_reason: str | None = None
    precheck_evidence: str | None = None

    classification: ClassificationResult | None = None
    refund_entities: RefundEntities | None = None
    retrieved: list[RetrievedChunkView] = Field(default_factory=list)
    draft: DraftResponse | None = None
    draft_attempts: int = 0
    revision_feedback: list[str] = Field(default_factory=list)
    verification: VerificationResult | None = None

    final_action: FinalAction | None = None
    route_reason: str | None = None
    priority: Priority = Priority.STANDARD
    error: str | None = None

    email_sent: bool = False
    send_status: str | None = None

    trace: Annotated[list[TraceEvent], operator.add] = Field(default_factory=list)
