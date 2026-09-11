from __future__ import annotations

from core.llm import LLMClient
from part1_email_agent.models import DraftResponse, RetrievedChunkView

DRAFTING_SYSTEM = (
    "You are an agent on the Rega's Support desk, which handles support for "
    "PointStar's cloud services. Sign off as Rega's Support, never as PointStar. "
    "You answer strictly from the knowledge base excerpts you are given. "
    "You never state a policy detail, number, timeframe or eligibility rule that is not "
    "written in those excerpts. When the excerpts do not cover the question, you say so "
    "instead of guessing — an honest 'I need to check with a specialist' is always "
    "preferred over an invented answer."
)

def _revision_section(feedback: list[str] | None) -> str:
    if not feedback:
        return ""
    problems = "\n".join(f"- {item}" for item in feedback)
    return f"""
Your previous draft was rejected by the fact-checker for these reasons:
{problems}
Write a new draft that removes or corrects every item above. Do not repeat a rejected claim.
"""

def build_prompt(email_text: str, chunks: list[RetrievedChunkView], feedback: list[str] | None = None) -> str:
    context = "\n\n".join(f"{chunk.text}" for chunk in chunks)
    available_ids = sorted({chunk.doc_id for chunk in chunks})
    return f"""Draft a reply to the customer using ONLY the knowledge base context below.

Hard rules:
- Every factual claim (policy terms, amounts, timeframes, eligibility) must come from the context.
- Do not add information from general knowledge, even if you are confident it is true.
- Cite the document IDs you actually used in `citations`. Only these IDs exist: {available_ids}
- Set fully_answerable=false if the context does not completely answer the question,
  and do not fabricate the missing part.
- Reply in the same language the customer wrote in.
- Be concise and professional. Do not promise an outcome the context does not authorise.
{_revision_section(feedback)}
Knowledge base context:
{context}

Customer email:
{email_text}"""

def draft_response(
    llm: LLMClient,
    email_text: str,
    chunks: list[RetrievedChunkView],
    feedback: list[str] | None = None,
) -> DraftResponse | None:
    if not chunks:
        return None
    return llm.generate_structured(build_prompt(email_text, chunks, feedback), DraftResponse, system=DRAFTING_SYSTEM)
