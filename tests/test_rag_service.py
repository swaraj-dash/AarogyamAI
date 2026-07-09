import database as db
from embeddings import DeterministicHashEmbedder
from services import rag_service


def _seed_dishes(embedder):
    rows = [
        {"state": "Kerala", "dish_name": "Fish Moilee", "meal_type": "lunch",
         "description": "Fish simmered in coconut milk", "preference": "non-vegetarian",
         "primary_nutrient": "protein", "secondary_nutrient": "omega_3",
         "tertiary_nutrient": "iodine", "quaternary_nutrient": "vitamin_d"},
        {"state": "Kerala", "dish_name": "Puttu with Kadala Curry", "meal_type": "breakfast",
         "description": "Steamed rice cylinders with chickpea curry", "preference": "vegan",
         "primary_nutrient": "protein", "secondary_nutrient": "fiber",
         "tertiary_nutrient": "iron", "quaternary_nutrient": "carbohydrates"},
        {"state": "Punjab", "dish_name": "Tandoori Chicken", "meal_type": "dinner",
         "description": "Marinated chicken roasted in a clay oven", "preference": "non-vegetarian",
         "primary_nutrient": "protein", "secondary_nutrient": "iron",
         "tertiary_nutrient": "zinc", "quaternary_nutrient": "vitamin_b12"},
    ]
    texts = [rag_service._dish_embedding_text(r) for r in rows]
    embeddings = embedder.embed(texts)
    db_rows = []
    for row, emb in zip(rows, embeddings):
        db_rows.append({**row, "embedding": rag_service._to_json(emb)})
    db.bulk_insert_rag_dishes(db_rows)


def test_retrieve_dishes_filters_out_incompatible_preference():
    embedder = DeterministicHashEmbedder(dim=64)
    _seed_dishes(embedder)
    results = rag_service.retrieve_dishes(
        food_preference="vegan", query_text="high protein breakfast",
        embedder=embedder, top_k=5,
    )
    dish_names = [r["dish_name"] for r in results]
    assert "Tandoori Chicken" not in dish_names
    assert "Fish Moilee" not in dish_names
    assert "Puttu with Kadala Curry" in dish_names


def test_retrieve_dishes_vegetarian_allows_vegan_dishes_too():
    embedder = DeterministicHashEmbedder(dim=64)
    _seed_dishes(embedder)
    results = rag_service.retrieve_dishes(
        food_preference="vegetarian", query_text="protein rich meal",
        embedder=embedder, top_k=5,
    )
    dish_names = [r["dish_name"] for r in results]
    assert "Puttu with Kadala Curry" in dish_names
    assert "Tandoori Chicken" not in dish_names


def test_retrieve_dishes_non_vegetarian_sees_everything():
    embedder = DeterministicHashEmbedder(dim=64)
    _seed_dishes(embedder)
    results = rag_service.retrieve_dishes(
        food_preference="non-vegetarian", query_text="protein rich dinner",
        embedder=embedder, top_k=5,
    )
    assert len(results) == 3


def test_retrieve_dishes_home_state_boost():
    embedder = DeterministicHashEmbedder(dim=64)
    _seed_dishes(embedder)
    results = rag_service.retrieve_dishes(
        food_preference="non-vegetarian", query_text="protein rich meal",
        home_state="Kerala", embedder=embedder, top_k=5,
    )
    assert all("similarity_score" in r for r in results)
    assert all("embedding" not in r for r in results)


def test_retrieve_dishes_meal_type_filter():
    embedder = DeterministicHashEmbedder(dim=64)
    _seed_dishes(embedder)
    results = rag_service.retrieve_dishes(
        food_preference="non-vegetarian", query_text="anything",
        meal_type="breakfast", embedder=embedder, top_k=5,
    )
    assert all(r["meal_type"].lower() == "breakfast" for r in results)


def test_retrieve_dishes_empty_index_returns_empty():
    embedder = DeterministicHashEmbedder(dim=64)
    results = rag_service.retrieve_dishes(
        food_preference="vegan", query_text="anything", embedder=embedder,
    )
    assert results == []


def test_build_index_from_csv_is_idempotent(tmp_path, monkeypatch):
    embedder = DeterministicHashEmbedder(dim=32)
    count_first = rag_service.build_index(embedder=embedder)
    assert count_first == db.rag_dishes_count()
    assert count_first > 0

    count_second = rag_service.build_index(embedder=embedder)
    assert count_second == 0  # no-op since table already populated
    assert db.rag_dishes_count() == count_first
