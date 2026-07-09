"""
RAG service — the actual retrieval-augmented generation v1 never had.

v1's `rag_engine.py` did `df['state'].str.lower() == state.lower()` on a
CSV and called that RAG. There was no vector index, no embeddings, no
semantic matching — and a `faiss_index/` folder plus `faiss-cpu` /
`langchain` in requirements.txt that were never actually used anywhere.

v2 approach — hybrid retrieval:
  1. HARD FILTER on dietary preference (a vegan user must never see a
     mutton curry, no matter how semantically similar it scores — this is
     a correctness constraint, not a ranking preference, so it happens
     before embeddings are even considered).
  2. SOFT PREFERENCE for the user's home state (regional dishes score a
     small bonus, but a great semantic match from another state can still
     surface — v1's hard state filter meant zero results for edge-case
     states/typos).
  3. SEMANTIC RERANK: the query text is built from the user's health goal
     plus any nutrient gaps pulled from semantic memory (e.g. "recurring
     protein gap") — so retrieval is actually informed by accumulated
     history, not just today's static profile field.

`build_index()` is the one-time (or on-demand) embedding step that
populates `rag_dishes.embedding` — analogous to the FAISS index v1
imported but never built.
"""
from __future__ import annotations

import csv

import config
import database as db
from embeddings import Embedder, get_embedder
from vector_store import top_k_similar


def _dish_embedding_text(row: dict) -> str:
    nutrients = " ".join(filter(None, [
        row.get("primary_nutrient"), row.get("secondary_nutrient"),
        row.get("tertiary_nutrient"), row.get("quaternary_nutrient"),
    ]))
    return (
        f"{row.get('dish_name', '')} from {row.get('state', '')}, a "
        f"{row.get('meal_type', '')} dish. {row.get('description', '')} "
        f"Key nutrients: {nutrients}."
    )


def load_csv_rows(csv_path: str = None) -> list[dict]:
    csv_path = csv_path or config.RAG_DATA_CSV
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_index(embedder: Embedder = None, force: bool = False) -> int:
    """Embed every dish in the CSV and load it into rag_dishes.

    Idempotent: no-ops if the table is already populated, unless force=True
    (used by tests / after editing the CSV).
    """
    if not force and db.rag_dishes_count() > 0:
        return 0

    embedder = embedder or get_embedder()
    rows = load_csv_rows()
    texts = [_dish_embedding_text(r) for r in rows]
    embeddings = embedder.embed(texts)

    db_rows = []
    for row, emb in zip(rows, embeddings):
        db_rows.append({
            "state": row.get("state"),
            "dish_name": row.get("dish_name"),
            "meal_type": row.get("meal_type"),
            "description": row.get("description"),
            "preference": row.get("preference"),
            "primary_nutrient": row.get("primary_nutrient"),
            "secondary_nutrient": row.get("secondary_nutrient"),
            "tertiary_nutrient": row.get("tertiary_nutrient"),
            "quaternary_nutrient": row.get("quaternary_nutrient"),
            "embedding": _to_json(emb),
        })
    db.bulk_insert_rag_dishes(db_rows)
    return len(db_rows)


def _to_json(vec: list[float]) -> str:
    import json
    return json.dumps(vec)


_PREFERENCE_COMPATIBILITY = {
    "vegan": {"vegan"},
    "vegetarian": {"vegan", "vegetarian"},
    "non-vegetarian": {"vegan", "vegetarian", "non-vegetarian"},
}


def retrieve_dishes(
    food_preference: str,
    query_text: str,
    home_state: str = None,
    meal_type: str = None,
    top_k: int = None,
    embedder: Embedder = None,
) -> list[dict]:
    """Hybrid retrieval: hard-filter on diet compatibility, soft-boost on
    home state, semantic rerank on query_text (health goal + memory-derived
    nutrient gaps)."""
    top_k = top_k or config.RAG_TOP_K
    embedder = embedder or get_embedder()

    all_dishes = db.get_all_rag_dishes(only_embedded=True)
    if not all_dishes:
        return []

    pref_key = (food_preference or "").strip().lower()
    allowed = _PREFERENCE_COMPATIBILITY.get(pref_key, {"vegan", "vegetarian", "non-vegetarian"})
    candidates = [d for d in all_dishes if (d.get("preference") or "").lower() in allowed]
    if meal_type:
        meal_filtered = [d for d in candidates if (d.get("meal_type") or "").lower() == meal_type.lower()]
        if meal_filtered:
            candidates = meal_filtered
    if not candidates:
        return []

    query_embedding = embedder.embed_one(query_text)
    ranked = top_k_similar(query_embedding, candidates, k=top_k * 3, min_score=0.0)

    if home_state:
        for r in ranked:
            if (r.get("state") or "").lower() == home_state.lower():
                r["similarity_score"] += 0.05  # small home-state boost, doesn't override a bad semantic match
        ranked.sort(key=lambda x: x["similarity_score"], reverse=True)

    for r in ranked:
        r.pop("embedding", None)
    return ranked[:top_k]
