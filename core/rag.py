from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from pypdf import PdfReader

from core.config import settings
from core.embeddings import Embedder, get_embedder
from core.logging_config import get_logger

log = get_logger(__name__)

DOC_ID_PATTERN = re.compile(r"Document ID:\s*([A-Z0-9\-]+)")
SECTION_PATTERNS = (
    re.compile(r"^(\d+\.\s+[A-Z].{2,80})$"),
    re.compile(r"^(Q\d+\.\s+.{3,120})$"),
)
MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120

@dataclass
class Chunk:
    text: str
    doc_id: str
    section: str
    source_file: str

@dataclass
class RetrievedChunk:
    text: str
    doc_id: str
    section: str
    score: float

    @property
    def citation(self) -> str:
        return f"{self.doc_id} §{self.section}" if self.section else self.doc_id

def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def _detect_section(line: str) -> str | None:
    for pattern in SECTION_PATTERNS:
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None

PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
BOILERPLATE = re.compile(
    r"^(subject:|(hi|hello|hey|dear|thanks?|thank you|regards|best regards|salam|halo|hai|selamat|"
    r"terima kasih|hormat kami|mohon bantuannya)\b)",
    re.I,
)
MIN_SUBQUERY_CHARS = 25
MAX_SUBQUERIES = 6

def split_into_subqueries(text: str, max_queries: int = MAX_SUBQUERIES) -> list[str]:
    queries = [" ".join(text.split())]

    for paragraph in PARAGRAPH_SPLIT.split(text):
        unwrapped = " ".join(paragraph.split())
        for sentence in SENTENCE_SPLIT.split(unwrapped):
            sentence = sentence.strip()
            if len(sentence) < MIN_SUBQUERY_CHARS or BOILERPLATE.match(sentence):
                continue
            if sentence not in queries:
                queries.append(sentence)

    return queries[:max_queries]

def chunk_document(text: str, doc_id: str, source_file: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_section = "Preamble"
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        body = " ".join(" ".join(buffer).split())
        if not body:
            buffer.clear()
            return
        start = 0
        while start < len(body):
            piece = body[start : start + MAX_CHUNK_CHARS]
            chunks.append(
                Chunk(
                    text=f"[{doc_id} §{current_section}] {piece}",
                    doc_id=doc_id,
                    section=current_section,
                    source_file=source_file,
                )
            )
            if start + MAX_CHUNK_CHARS >= len(body):
                break
            start += MAX_CHUNK_CHARS - CHUNK_OVERLAP_CHARS
        buffer.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _detect_section(line)
        if heading:
            flush()
            current_section = heading
        buffer.append(line)
    flush()
    return chunks

class KnowledgeBase:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, embedder: Embedder) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self._embedder = embedder

    @property
    def document_ids(self) -> set[str]:
        return {c.doc_id for c in self.chunks}

    @classmethod
    def build(cls, pdf_dir: Path | None = None, embedder: Embedder | None = None) -> "KnowledgeBase":
        pdf_dir = pdf_dir or settings.kb_pdf_dir
        embedder = embedder or get_embedder()

        pdf_files = sorted(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDFs found in {pdf_dir}. Run: python knowledge_base/md_to_pdf.py")

        chunks: list[Chunk] = []
        for pdf_path in pdf_files:
            text = _extract_text(pdf_path)
            match = DOC_ID_PATTERN.search(text)
            doc_id = match.group(1) if match else pdf_path.stem.upper()
            doc_chunks = chunk_document(text, doc_id, pdf_path.name)
            chunks.extend(doc_chunks)
            log.info("kb_indexed_document", doc_id=doc_id, file=pdf_path.name, chunks=len(doc_chunks))

        embeddings = embedder.encode([c.text for c in chunks])
        return cls(chunks, np.asarray(embeddings, dtype=np.float32), embedder)

    def retrieve(self, query: str, k: int | None = None, min_score: float | None = None) -> list[RetrievedChunk]:
        k = k or settings.retrieval_top_k
        min_score = settings.retrieval_min_score if min_score is None else min_score

        queries = split_into_subqueries(query)
        query_vecs = np.asarray(self._embedder.encode(queries), dtype=np.float32)
        if query_vecs.ndim == 1:
            query_vecs = query_vecs[np.newaxis, :]

        per_query = self.embeddings @ query_vecs.T
        best_score = per_query.max(axis=1)
        rankings = [np.argsort(per_query[:, q])[::-1] for q in range(per_query.shape[1])]

        selected: list[int] = []
        seen: set[int] = set()
        for rank in range(len(self.chunks)):
            if len(selected) >= k:
                break
            for ranking in rankings:
                if len(selected) >= k:
                    break
                idx = int(ranking[rank])
                if idx in seen or float(best_score[idx]) < min_score:
                    continue
                seen.add(idx)
                selected.append(idx)

        selected.sort(key=lambda i: float(best_score[i]), reverse=True)
        return [
            RetrievedChunk(
                text=self.chunks[i].text,
                doc_id=self.chunks[i].doc_id,
                section=self.chunks[i].section,
                score=float(best_score[i]),
            )
            for i in selected
        ]

    @staticmethod
    def _fingerprint(pdf_dir: Path, embedder: Embedder) -> str:
        parts = [f"{p.name}:{p.stat().st_mtime_ns}" for p in sorted(pdf_dir.glob("*.pdf"))]
        parts.append(f"{type(embedder).__name__}:{embedder.dimension}")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    @classmethod
    def load_or_build(cls, pdf_dir: Path | None = None, embedder: Embedder | None = None) -> "KnowledgeBase":
        pdf_dir = pdf_dir or settings.kb_pdf_dir
        embedder = embedder or get_embedder()
        cache_dir = settings.index_cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = cls._fingerprint(pdf_dir, embedder)
        meta_path = cache_dir / f"{key}.json"
        vec_path = cache_dir / f"{key}.npy"

        if meta_path.exists() and vec_path.exists():
            chunks = [Chunk(**c) for c in json.loads(meta_path.read_text(encoding="utf-8"))]
            embeddings = np.load(vec_path)
            log.info("kb_cache_hit", chunks=len(chunks), key=key)
            return cls(chunks, embeddings, embedder)

        kb = cls.build(pdf_dir, embedder)
        meta_path.write_text(json.dumps([asdict(c) for c in kb.chunks], ensure_ascii=False), encoding="utf-8")
        np.save(vec_path, kb.embeddings)
        log.info("kb_cache_written", chunks=len(kb.chunks), key=key)
        return kb
