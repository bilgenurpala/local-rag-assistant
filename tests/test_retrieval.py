"""Unit tests for the similarity math and retrieval logic in src/retrieve.py."""

from types import SimpleNamespace

import pytest

import ingest
import retrieve
from retrieve import cosine_similarity, get_top_chunks


class FakeEmbeddingClient:
    """Stands in for the Foundry embedding client with a fixed vector."""

    def __init__(self, vector):
        self.vector = vector

    def generate_embedding(self, text):
        return SimpleNamespace(data=[SimpleNamespace(embedding=self.vector)])


def test_identical_vectors_score_one():
    vec = [1.0, 2.0, 3.0]
    assert cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_orthogonal_vectors_score_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_opposite_vectors_score_minus_one():
    assert cosine_similarity([1.0, 2.0], [-1.0, -2.0]) == pytest.approx(-1.0)


def test_scale_does_not_change_score():
    assert cosine_similarity([1.0, 2.0], [10.0, 20.0]) == pytest.approx(1.0)


def test_zero_vector_scores_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == pytest.approx(0.0)


def test_vectors_of_different_lengths_raise():
    """Silently comparing a truncated prefix would produce plausible nonsense."""
    with pytest.raises(ValueError, match="length mismatch"):
        cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0])


def test_ingest_and_retrieve_agree_on_the_database_path():
    """ingest.py writes the database that retrieve.py reads."""
    assert ingest.DB_PATH == retrieve.DB_PATH


def test_get_top_chunks_ranks_by_similarity(monkeypatch):
    fake_chunks = [
        (1, "licensing.md", "about licensing", [0.0, 1.0]),
        (2, "installation.md", "about installation", [1.0, 0.0]),
        (3, "overview.md", "half related", [1.0, 1.0]),
    ]
    monkeypatch.setattr(retrieve, "load_chunks", lambda: fake_chunks)
    client = FakeEmbeddingClient([1.0, 0.0])

    results = get_top_chunks("How do I install it?", client, top_k=2)

    assert len(results) == 2
    assert results[0][1] == "about installation"
    assert results[0][2] == "installation.md"
    assert results[1][1] == "half related"
    
