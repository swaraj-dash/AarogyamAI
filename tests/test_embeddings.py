from embeddings import DeterministicHashEmbedder
from vector_store import cosine_similarity


def test_embedding_is_deterministic():
    embedder = DeterministicHashEmbedder(dim=128)
    v1 = embedder.embed_one("high protein breakfast")
    v2 = embedder.embed_one("high protein breakfast")
    assert v1 == v2


def test_embedding_dimension():
    embedder = DeterministicHashEmbedder(dim=64)
    v = embedder.embed_one("some text")
    assert len(v) == 64


def test_similar_strings_score_higher_than_dissimilar():
    embedder = DeterministicHashEmbedder(dim=256)
    query = embedder.embed_one("high protein vegetarian breakfast")
    close = embedder.embed_one("high protein vegetarian meal")
    far = embedder.embed_one("completely unrelated topic about cars")

    sim_close = cosine_similarity(query, close)
    sim_far = cosine_similarity(query, far)
    assert sim_close > sim_far


def test_batch_embed_matches_embed_one():
    embedder = DeterministicHashEmbedder(dim=32)
    texts = ["alpha", "beta", "gamma"]
    batch = embedder.embed(texts)
    singles = [embedder.embed_one(t) for t in texts]
    assert batch == singles
