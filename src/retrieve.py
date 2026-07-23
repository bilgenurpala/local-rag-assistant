"""Retrieve the most relevant knowledge base chunks for a query.

Embeds the query, scores it against every chunk in SQLite 
with cosine similarity (brute force), and returns the top-K matches.
"""

import json
import math
import sqlite3
from pathlib import Path

DB_PATH = Path("rag.db")
TOP_K = 3

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Return the cosine similarity between two vectors.

    1.0 means identical direction (same meaning); values near 0 mean the vectors are unrelated.

    Raises ValueError if the vectors have different lengths, which means the
    query and the stored chunks were embedded with different models.
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"Vector length mismatch: {len(vec_a)} != {len(vec_b)}. "
            "The query and the stored chunks were embedded with different "
            "models; re-run src/ingest.py to rebuild the database."
        )
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def load_chunks(
    db_path: Path = DB_PATH,
) -> list[tuple[int, str, str, list[float]]]:
    """Load all chunks from the database.
    
    Returns (id, source, content, vector) tuples, with each stored JSON
    embedding parsed back into a list of floats.
    """
    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        "SELECT id, source, content, embedding FROM chunks"
    ).fetchall()
    connection.close()
    return [
        (cid, source, content, json.loads(emb))
        for cid, source, content, emb in rows
    ]

def get_top_chunks(
    query: str, client, top_k: int = TOP_K
) -> list[tuple[float, str, str]]:
    """Return the topk-k most relevant chunks for a query.
    
    Embeds the query, scores every stored chunk with cosine
    similarity, and returns (score, content, source) tuples, best first.
    """
    response = client.generate_embedding(query)
    query_vector = response.data[0].embedding

    scored = []
    for cid, source, content, vector in load_chunks():
        score = cosine_similarity(query_vector, vector)
        scored.append((score, content, source))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:top_k]

if __name__ == "__main__":
    from ingest import setup_embedding_client

    model, client = setup_embedding_client()

    questions = [
        "Do I need an Azure subscription to use Foundry Local?",
        "Which platforms does Foundry Local support?",
        "How do I load a model in Python?",
    ]

    for question in questions:
        print(f"\nQ: {question}")
        for score, content, source in get_top_chunks(question, client):
            print(f"  {score:.3f}  [{source}] {content[:80]}...")

    model.unload()
