from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from core.config import settings
from core.embeddings import Embedder, get_embedder
from core.logging_config import get_logger
from core.rag import DOC_ID_PATTERN, Chunk, KnowledgeBase, chunk_document
from part3_doc_agent.models import RetrievedChunkView

log = get_logger(__name__)

_HEADING = re.compile(r"^#{1,6}\s+")
_BLOCKQUOTE = re.compile(r"^>\s?")
_EMPHASIS = re.compile(r"\*\*|__|(?<!\*)\*(?!\*)")
_TABLE_RULE = re.compile(r"^\|[\s:|-]+\|$")

def normalise_markdown(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if _TABLE_RULE.match(line.strip()):
            continue
        line = _HEADING.sub("", line)
        line = _BLOCKQUOTE.sub("", line)
        line = _EMPHASIS.sub("", line)
        lines.append(line)
    return "\n".join(lines)

def load_chunks(path: Path | None = None) -> list[Chunk]:
    path = path or settings.chat_document_path
    if not path.exists():
        raise FileNotFoundError(f"Sample document not found: {path}")

    text = normalise_markdown(path.read_text(encoding="utf-8"))
    match = DOC_ID_PATTERN.search(text)
    doc_id = match.group(1) if match else path.stem.upper()
    chunks = chunk_document(text, doc_id, path.name)
    log.info("document_chunked", doc_id=doc_id, file=path.name, chunks=len(chunks))
    return chunks

def build_index(path: Path | None = None, embedder: Embedder | None = None) -> KnowledgeBase:
    embedder = embedder or get_embedder()
    chunks = load_chunks(path)
    embeddings = np.asarray(embedder.encode([c.text for c in chunks]), dtype=np.float32)
    return KnowledgeBase(chunks, embeddings, embedder)

def search(
    kb: KnowledgeBase,
    queries: str | list[str],
    k: int | None = None,
    min_score: float | None = None,
) -> list[RetrievedChunkView]:
    k = k or settings.chat_retrieval_top_k
    min_score = settings.chat_retrieval_min_score if min_score is None else min_score

    if isinstance(queries, str):
        queries = [queries]
    cleaned = [q.strip() for q in queries if q and q.strip()]
    if not cleaned:
        return []

    rankings = [kb.retrieve(q, k=k, min_score=min_score) for q in cleaned]

    selected: dict[str, RetrievedChunkView] = {}
    for rank in range(k):
        for hits in rankings:
            if len(selected) >= k:
                break
            if rank >= len(hits):
                continue
            hit = hits[rank]
            existing = selected.get(hit.text)
            if existing is None:
                selected[hit.text] = RetrievedChunkView(
                    text=hit.text, doc_id=hit.doc_id, section=hit.section, score=hit.score
                )
            elif hit.score > existing.score:
                existing.score = hit.score
        if len(selected) >= k:
            break

    return sorted(selected.values(), key=lambda c: c.score, reverse=True)

def format_context(chunks: list[RetrievedChunkView]) -> str:
    if not chunks:
        return "NO RELEVANT CONTEXT FOUND IN THE HANDBOOK."
    return "\n\n".join(f"[{c.citation}]\n{c.text}" for c in chunks)
