from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

class SectionSummary(BaseModel):
    summary: str = Field(description="Summary of this section only")

class DocumentSummary(BaseModel):
    summary: str = Field(description="Summary of the whole document")
    key_points: list[str] = Field(default_factory=list, description="At most 5 short bullet points")

@dataclass
class FetchResult:
    url: str
    html: str
    status_code: int
    content_type: str
    bytes_downloaded: int
    elapsed_ms: int

@dataclass
class ExtractedContent:
    title: str
    text: str
    char_count: int
    strategy: str
    link_density: float
    reduction_ratio: float

@dataclass
class Chunk:
    text: str
    index: int
    estimated_tokens: int

@dataclass
class GuardrailResult:
    text: str
    word_count: int
    attempts: int
    enforced_by: str
    within_budget: bool

@dataclass
class PageSummary:
    url: str
    title: str
    summary: str
    key_points: list[str] = field(default_factory=list)

    strategy: str = ""
    extraction_strategy: str = ""
    raw_bytes: int = 0
    extracted_chars: int = 0
    reduction_ratio: float = 0.0
    chunk_count: int = 0
    llm_calls: int = 0
    reduce_rounds: int = 0
    word_count: int = 0
    guardrail_enforced_by: str = ""
    guardrail_attempts: int = 0
    within_budget: bool = True
    elapsed_ms: int = 0
