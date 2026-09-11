from __future__ import annotations

import time

from core.llm import LLMClient, build_llm_client
from core.logging_config import get_logger
from part2_scraper import extractor, fetcher, guardrail, summarizer
from part2_scraper.mock_llm import MockSummarizerLLM
from part2_scraper.models import PageSummary

log = get_logger(__name__)

def summarize_url(
    url: str,
    llm: LLMClient | None = None,
    max_words: int | None = None,
) -> PageSummary:
    llm = llm or build_llm_client(mock_factory=MockSummarizerLLM)
    started = time.perf_counter()

    page = fetcher.fetch(url)
    content = extractor.extract(page.html)
    result = summarizer.summarize(llm, content, max_words=max_words)
    checked = guardrail.enforce_length(llm, result.summary, max_words=max_words)

    summary = PageSummary(
        url=page.url,
        title=content.title,
        summary=checked.text,
        key_points=result.key_points,
        strategy=result.strategy,
        extraction_strategy=content.strategy,
        raw_bytes=page.bytes_downloaded,
        extracted_chars=content.char_count,
        reduction_ratio=content.reduction_ratio,
        chunk_count=result.chunk_count,
        llm_calls=result.llm_calls + checked.attempts,
        reduce_rounds=result.reduce_rounds,
        word_count=checked.word_count,
        guardrail_enforced_by=checked.enforced_by,
        guardrail_attempts=checked.attempts,
        within_budget=checked.within_budget,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
    )
    log.info(
        "page_summarized", url=summary.url, strategy=summary.strategy,
        chunks=summary.chunk_count, llm_calls=summary.llm_calls,
        words=summary.word_count, enforced_by=summary.guardrail_enforced_by,
        elapsed_ms=summary.elapsed_ms,
    )
    return summary
