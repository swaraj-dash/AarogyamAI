"""
Embedding providers.

Why an abstraction at all: v1 had faiss-cpu and langchain sitting in
requirements.txt completely unused — infra that was aspired to but never
wired up. To avoid repeating that, every consumer in this codebase (RAG,
semantic memory) depends only on the `Embedder` interface below, never on
"Gemini" directly. That means:
  1. It's trivially testable offline (DeterministicHashEmbedder needs no
     network and no API key, and is stable across runs so test assertions
     don't flake).
  2. Swapping embedding providers later (e.g. a local sentence-transformers
     model) is a one-file change, not a grep-and-replace across services.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import numpy as np

import config


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
        raise NotImplementedError

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class GeminiEmbeddingProvider(Embedder):
    """Real embeddings via the Gemini embedding API (models/text-embedding-004).

    Only imports google.generativeai lazily, so the offline/test path never
    needs the package installed with a live key to import this module.
    """

    def __init__(self, model: str = None, api_key: str = None):
        import google.generativeai as genai
        genai.configure(api_key=api_key or config.GOOGLE_API_KEY)
        self._genai = genai
        self.model = model or config.EMBEDDING_MODEL

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            resp = self._genai.embed_content(model=self.model, content=t)
            out.append(resp["embedding"])
        return out


class DeterministicHashEmbedder(Embedder):
    """Offline fallback embedder — no network, no API key, fully deterministic.

    Not semantically meaningful the way a real embedding model is, but it
    IS a legitimate fixed-dimension vector space with the property that
    identical/near-identical strings land close together (we hash
    overlapping character shingles, so shared substrings contribute shared
    dimensions). That's enough to keep the retrieval *pipeline* — ranking,
    thresholding, dedup — fully exercised by unit tests without a live
    Gemini key, which is exactly what config.OFFLINE_MODE is for.
    """

    def __init__(self, dim: int = None, shingle_size: int = 3):
        self.dim = dim or config.EMBEDDING_DIM
        self.shingle_size = shingle_size

    def _hash_to_index(self, token: str) -> int:
        h = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return int(h, 16) % self.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float64)
            normalized = text.lower().strip()
            tokens = normalized.split()
            for tok in tokens:
                vec[self._hash_to_index(tok)] += 1.0
            for i in range(len(normalized) - self.shingle_size + 1):
                shingle = normalized[i:i + self.shingle_size]
                vec[self._hash_to_index(shingle)] += 0.5
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec.tolist())
        return vectors


_embedder_singleton: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder_singleton
    if _embedder_singleton is not None:
        return _embedder_singleton
    if config.OFFLINE_MODE:
        _embedder_singleton = DeterministicHashEmbedder()
    else:
        _embedder_singleton = GeminiEmbeddingProvider()
    return _embedder_singleton
