"""Retrieve the most relevant knowledge base chunks for a query.

Embeds the query, scores it against every chunk in SQLite 
with cosine similarity (brute force), and returns the top-K matches.
"""

import json
import math
import sqlite3
from pathlib import Path

from foundry_local_sdk import Configuration, FoundryLocalManager

DB_PATH = Path("rag.db")
EMBEDDING_MODEL = "qwen3-embedding-0.6b"
TOP_K = 3

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Return the cosine similarity between two vectors.

    1.0 means identical direction (same meaning); values near 0 mean the vectors are unrelated.
    """
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def load_chunks(db_path: Path = DB_PATH) -> list[tuple[int, str, list[float]]]:
    """Load all chunks from the database.
    
    Returns (id, content, vector) tuples, with each stored JSON
    embedding parsed back into a list of floats.
    """
    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        "SELECT id, content, embedding FROM chunks"
    ).fetchall()
    connection.close()
    return [(cid, content, json.loads(emb)) for cid, content, emb in rows]

def get_top_chunks(query: str, client, top_k: int = TOP_K) -> list[tuple[float, str]]:
    """Return the topk-k most relevant chunks for a query.
    
    Embeds the query, scores every stored chunk with cosine
    similarity, and returns (score, content) pairs, best first.
    """
    response = client.generate_embedding(query)
    query_vector = response.data[0].embedding

    scored = []
    for cid, content, vector in load_chunks():
        score = cosine_similarity(query_vector, vector)
        scored.append((score, content))
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
        for score, content in get_top_chunks(question, client):
            print(f"  {score:.3f}  {content[:80]}...")

    model.unload()