from __future__ import annotations

import re

from core.config import settings
from core.llm import LLMClient
from core.logging_config import get_logger
from part2_scraper.models import DocumentSummary, GuardrailResult

log = get_logger(__name__)

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

REWRITE_SYSTEM = (
    "You rewrite summaries to fit a length budget. Never introduce facts that were not "
    "in the text you were given."
)

def count_words(text: str) -> int:
    return len(text.split())

def truncate_to_words(text: str, max_words: int) -> str:
    if count_words(text) <= max_words:
        return text

    kept, total = [], 0
    for sentence in SENTENCE_END.split(text):
        words = count_words(sentence)
        if total + words > max_words:
            break
        kept.append(sentence)
        total += words

    if kept:
        return " ".join(kept)

    return " ".join(text.split()[:max_words]) + "…"

def _ask_for_rewrite(llm: LLMClient, text: str, actual: int, max_words: int, min_words: int) -> str:
    if actual > max_words:
        instruction = (
            f"Your summary is {actual} words. The hard limit is {max_words} — you are "
            f"{actual - max_words} words over. Rewrite it to fit, keeping the most important "
            "facts and dropping the least important. Do not add new information."
        )
    else:
        instruction = (
            f"Your summary is only {actual} words, below the {min_words}-word minimum. "
            "Expand it using only information already present. Do not invent anything."
        )

    return llm.generate_structured(
        f"{instruction}\n\nCurrent summary:\n{text}", DocumentSummary, system=REWRITE_SYSTEM
    ).summary

def enforce_length(
    llm: LLMClient,
    summary: str,
    *,
    max_words: int | None = None,
    min_words: int | None = None,
    max_attempts: int = 2,
) -> GuardrailResult:
    max_words = max_words or settings.summary_max_words
    min_words = settings.summary_min_words if min_words is None else min_words

    current, attempts = summary, 0
    while attempts < max_attempts:
        words = count_words(current)
        if min_words <= words <= max_words:
            return GuardrailResult(
                text=current, word_count=words, attempts=attempts,
                enforced_by="model" if attempts == 0 else "retry", within_budget=True,
            )
        log.info("guardrail_rewrite", words=words, max_words=max_words, attempt=attempts + 1)
        attempts += 1
        current = _ask_for_rewrite(llm, current, words, max_words, min_words)

    words = count_words(current)
    if words > max_words:
        truncated = truncate_to_words(current, max_words)
        log.warning("guardrail_truncated", from_words=words, to_words=count_words(truncated))
        return GuardrailResult(truncated, count_words(truncated), attempts, "truncation", True)

    if words < min_words:
        log.warning("guardrail_too_short", words=words, min_words=min_words)
        return GuardrailResult(current, words, attempts, "truncation", False)

    return GuardrailResult(current, words, attempts, "retry", True)
