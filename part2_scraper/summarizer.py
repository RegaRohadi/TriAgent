from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from core.config import settings
from core.llm import LLMClient
from core.logging_config import get_logger
from part2_scraper.chunker import chunk_text, estimate_tokens
from part2_scraper.models import Chunk, DocumentSummary, ExtractedContent, SectionSummary

log = get_logger(__name__)

MAX_REDUCE_ROUNDS = 3

MAP_SYSTEM = (
    "You summarize one section of a longer document. Preserve concrete facts: numbers, "
    "dates, names, prices and technical terms — the later stages never see the original "
    "text, so anything you drop is lost for good. Do not write an introduction or a "
    "conclusion: you are looking at a fragment, not the whole document."
)

REDUCE_SYSTEM = (
    "You merge section summaries of a single document into one coherent summary. "
    "Remove repetition, keep concrete facts, and write flowing prose — never a list "
    "of sections, and never a sentence about the sections themselves."
)

class SummarizationError(RuntimeError):
    pass

@dataclass
class SummaryResult:
    summary: str
    key_points: list[str]
    strategy: str
    chunk_count: int
    llm_calls: int
    reduce_rounds: int

def _summarize_section(llm: LLMClient, chunk: Chunk, total: int, title: str) -> str:
    prompt = f"""Document title: {title}
This is section {chunk.index + 1} of {total}.

Summarize ONLY this section, in at most 120 words.

Section content:
{chunk.text}"""
    return llm.generate_structured(prompt, SectionSummary, system=MAP_SYSTEM).summary

def _map_phase(llm: LLMClient, chunks: list[Chunk], title: str) -> list[str]:
    if len(chunks) == 1:
        return [_summarize_section(llm, chunks[0], 1, title)]

    workers = max(1, min(settings.map_workers, len(chunks)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_summarize_section, llm, c, len(chunks), title) for c in chunks]
        return [future.result() for future in futures]

def _reduce(llm: LLMClient, parts: list[str], title: str, max_words: int) -> DocumentSummary:
    joined = "\n\n".join(f"[Section {i + 1}] {part}" for i, part in enumerate(parts))
    prompt = f"""Document title: {title}

Write one summary of the whole document in at most {max_words} words,
followed by at most 5 short key points.

Section summaries:
{joined}"""
    return llm.generate_structured(prompt, DocumentSummary, system=REDUCE_SYSTEM)

def summarize(
    llm: LLMClient,
    content: ExtractedContent,
    max_words: int | None = None,
    max_chunk_tokens: int | None = None,
) -> SummaryResult:
    max_words = max_words or settings.summary_max_words
    max_chunk_tokens = max_chunk_tokens or settings.chunk_max_tokens

    chunks = chunk_text(content.text, max_tokens=max_chunk_tokens)
    if not chunks:
        raise SummarizationError("nothing to summarize")

    if len(chunks) == 1:
        final = _reduce(llm, [chunks[0].text], content.title, max_words)
        log.info("summarized", strategy="single_pass", chunks=1, llm_calls=1)
        return SummaryResult(final.summary, final.key_points, "single_pass", 1, 1, 0)

    summaries = _map_phase(llm, chunks, content.title)
    calls = len(chunks)

    rounds = 0
    while estimate_tokens("\n\n".join(summaries)) > max_chunk_tokens:
        rounds += 1
        if rounds > MAX_REDUCE_ROUNDS:
            raise SummarizationError(f"summaries did not converge after {MAX_REDUCE_ROUNDS} reduce rounds")
        grouped = chunk_text("\n\n".join(summaries), max_tokens=max_chunk_tokens, overlap_tokens=0)
        summaries = _map_phase(llm, grouped, content.title)
        calls += len(grouped)

    final = _reduce(llm, summaries, content.title, max_words)
    calls += 1
    log.info("summarized", strategy="map_reduce", chunks=len(chunks), llm_calls=calls, reduce_rounds=rounds)
    return SummaryResult(final.summary, final.key_points, "map_reduce", len(chunks), calls, rounds)
