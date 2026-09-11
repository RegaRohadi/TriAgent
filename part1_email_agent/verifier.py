from __future__ import annotations

import re
from dataclasses import dataclass

from core.config import settings
from core.llm import LLMClient
from core.logging_config import get_logger
from part1_email_agent.models import DraftResponse, RetrievedChunkView, VerificationResult

log = get_logger(__name__)

VERIFIER_SYSTEM = (
    "You are a strict fact-checker for customer support replies. Your job is to find claims "
    "in a draft that are NOT supported by the provided source excerpts. Be conservative: if a "
    "specific number, timeframe, eligibility rule or promise does not appear in the sources, it "
    "is unsupported, even if it sounds plausible.\n\n"
    "Only statements about the customer's situation or our policy count as claims. These do NOT: "
    "greetings, the customer's own name, sign-offs, the name of the support desk sending the "
    "reply, generic courtesy, and offers to escalate to a specialist. The sender's own identity "
    "is never something the knowledge base needs to support."
)

@dataclass
class CitationCheck:
    valid: bool
    invalid_citations: list[str]

def check_citations(draft: DraftResponse, chunks: list[RetrievedChunkView]) -> CitationCheck:
    retrieved_ids = {chunk.doc_id for chunk in chunks}
    invalid = [c for c in draft.citations if c.split(" ")[0] not in retrieved_ids]
    return CitationCheck(valid=not invalid and bool(draft.citations), invalid_citations=invalid)

def build_prompt(draft: DraftResponse, chunks: list[RetrievedChunkView]) -> str:
    context = "\n\n".join(chunk.text for chunk in chunks)
    return f"""Check the draft reply against the source excerpts.

Source excerpts:
{context}

Draft reply:
{draft.text}

List every claim, number, date, policy rule or eligibility statement in the draft that does
not explicitly appear in the excerpts. Set fully_grounded=true only if you find none."""

def _normalize(text: str) -> str:
    without_apostrophes = re.sub(r"['‘’]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", without_apostrophes).strip()

def is_identity_only(claim: str, desk_name: str) -> bool:
    normalized = _normalize(claim)
    if not normalized:
        return True
    desk = _normalize(desk_name)
    if not desk:
        return False
    return normalized in {desk, f"{desk} team", f"best regards {desk}", f"regards {desk}", f"sincerely {desk}"}

def verify_draft(
    llm: LLMClient,
    draft: DraftResponse,
    chunks: list[RetrievedChunkView],
    desk_name: str | None = None,
) -> VerificationResult:
    desk_name = settings.smtp_from_name if desk_name is None else desk_name
    result = llm.generate_structured(build_prompt(draft, chunks), VerificationResult, system=VERIFIER_SYSTEM)

    remaining = [claim for claim in result.unsupported_claims if not is_identity_only(claim, desk_name)]
    if len(remaining) != len(result.unsupported_claims):
        log.info("verifier_ignored_identity_claims", dropped=len(result.unsupported_claims) - len(remaining))
    return VerificationResult(fully_grounded=not remaining, unsupported_claims=remaining)
