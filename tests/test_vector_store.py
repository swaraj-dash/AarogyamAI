from vector_store import cosine_similarity, top_k_similar


def test_cosine_similarity_identical_vectors():
    assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors():
    assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9


def test_cosine_similarity_zero_vector_is_safe():
    assert cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0


def test_top_k_similar_ranks_correctly():
    query = [1, 0, 0]
    candidates = [
        {"id": "a", "embedding": [1, 0, 0]},      # identical -> score 1.0
        {"id": "b", "embedding": [0.9, 0.1, 0]},   # close
        {"id": "c", "embedding": [0, 1, 0]},       # orthogonal -> score 0.0
    ]
    ranked = top_k_similar(query, candidates, k=2)
    assert len(ranked) == 2
    assert ranked[0]["id"] == "a"
    assert ranked[1]["id"] == "b"
    assert ranked[0]["similarity_score"] > ranked[1]["similarity_score"]


def test_top_k_similar_respects_min_score():
    query = [1, 0]
    candidates = [{"id": "a", "embedding": [0, 1]}]  # orthogonal, score 0.0
    ranked = top_k_similar(query, candidates, k=5, min_score=0.5)
    assert ranked == []


def test_top_k_similar_empty_candidates():
    assert top_k_similar([1, 0], [], k=3) == []
