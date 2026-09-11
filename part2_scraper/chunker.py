from __future__ import annotations

import re
from math import ceil

from core.config import settings
from part2_scraper.models import Chunk

PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

CHARS_PER_TOKEN = 3.5

def estimate_tokens(text: str) -> int:
    return ceil(len(text) / CHARS_PER_TOKEN)

def _split_recursively(text: str, max_tokens: int) -> list[str]:
    if estimate_tokens(text) <= max_tokens:
        return [text]

    for splitter in (PARAGRAPH_SPLIT.split, SENTENCE_SPLIT.split, str.split):
        parts = [part for part in splitter(text) if part.strip()]
        if len(parts) > 1:
            pieces: list[str] = []
            for part in parts:
                pieces.extend(_split_recursively(part, max_tokens))
            return pieces

    size = int(max_tokens * CHARS_PER_TOKEN)
    return [text[i : i + size] for i in range(0, len(text), size)]

def _tail(text: str, overlap_tokens: int) -> str:
    if overlap_tokens <= 0:
        return ""
    tail = text[-int(overlap_tokens * CHARS_PER_TOKEN) :]
    sentences = SENTENCE_SPLIT.split(tail)
    return " ".join(sentences[1:]) if len(sentences) > 1 else tail

def chunk_text(
    text: str,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[Chunk]:
    max_tokens = max_tokens or settings.chunk_max_tokens
    overlap_tokens = settings.chunk_overlap_tokens if overlap_tokens is None else overlap_tokens

    overlap_tokens = min(overlap_tokens, max_tokens // 5)

    if not text.strip():
        return []
    if estimate_tokens(text) <= max_tokens:
        return [Chunk(text=text, index=0, estimated_tokens=estimate_tokens(text))]

    pieces = _split_recursively(text, max_tokens)

    chunks: list[Chunk] = []
    buffer = ""
    for piece in pieces:
        candidate = f"{buffer}\n\n{piece}" if buffer else piece
        if buffer and estimate_tokens(candidate) > max_tokens:
            chunks.append(Chunk(buffer, len(chunks), estimate_tokens(buffer)))
            carry = _tail(buffer, overlap_tokens)
            buffer = f"{carry}\n\n{piece}" if carry else piece
        else:
            buffer = candidate

    if buffer.strip():
        chunks.append(Chunk(buffer, len(chunks), estimate_tokens(buffer)))
    return chunks
