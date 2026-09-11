from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from core.config import settings

class Embedder(Protocol):
    dimension: int

    def encode(self, texts: str | list[str]) -> np.ndarray:
        pass

def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)

class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        get_dim = getattr(self._model, "get_embedding_dimension", None) or self._model.get_sentence_embedding_dimension
        self.dimension = int(get_dim())

    def encode(self, texts: str | list[str]) -> np.ndarray:
        return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

class HashingEmbedder:
    def __init__(self, dimension: int = 384, ngram: int = 4) -> None:
        self.dimension = dimension
        self._ngram = ngram

    def _encode_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        normalized = " ".join(text.lower().split())
        for i in range(max(len(normalized) - self._ngram + 1, 1)):
            gram = normalized[i : i + self._ngram]
            digest = hashlib.md5(gram.encode("utf-8")).digest()
            vec[int.from_bytes(digest[:4], "little") % self.dimension] += 1.0
        return vec

    def encode(self, texts: str | list[str]) -> np.ndarray:
        if isinstance(texts, str):
            return _normalize(self._encode_one(texts))
        return _normalize(np.vstack([self._encode_one(t) for t in texts]))

_cached: Embedder | None = None

def get_embedder(backend: str | None = None) -> Embedder:
    global _cached
    backend = (backend or settings.embedding_backend).lower()
    if _cached is not None:
        return _cached

    if backend == "hash":
        _cached = HashingEmbedder()
    else:
        _cached = SentenceTransformerEmbedder(settings.embedding_model)
    return _cached
