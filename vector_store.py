"""
Vector similarity utilities — the actual "R" in RAG that v1 never had.

Deliberately NOT a wrapper around FAISS/Chroma. At this data scale (a
few hundred dishes, a few hundred memory facts per user) a brute-force
cosine similarity scan in numpy is faster to develop, has zero extra
service dependencies, needs no on-disk index files to go stale, and is
easy to unit-test deterministically. ARCHITECTURE.md documents exactly
where this stops scaling (~100k+ vectors) and what to swap in (pgvector /
a managed vector DB) at that point — the interface below
(`top_k_similar`) is the seam you'd swap behind, nothing upstream would
need to change.
"""
from __future__ import annotations

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def top_k_similar(query_embedding: list[float], candidates: list[dict], k: int,
                   embedding_key: str = "embedding", min_score: float = 0.0) -> list[dict]:
    """Rank candidates by cosine similarity to query_embedding.

    candidates: list of dicts, each containing an `embedding_key` field.
    Returns the input dicts (copied, with a "similarity_score" field added),
    sorted descending, filtered by min_score, truncated to k.
    """
    if not candidates:
        return []

    query = np.asarray(query_embedding, dtype=np.float64)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return []

    matrix = np.array([c[embedding_key] for c in candidates], dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1e-12  # avoid div-by-zero for any degenerate rows
    scores = (matrix @ query) / (norms * query_norm)

    scored = []
    for cand, score in zip(candidates, scores):
        if score >= min_score:
            enriched = dict(cand)
            enriched["similarity_score"] = float(score)
            scored.append(enriched)

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:k]
