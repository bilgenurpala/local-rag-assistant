"""Ingest knowledge base documents into the vector store.

Reads every .md and .txt file in data/, splits each into paragraph chunks, 
embeds each chunk, and stores (source, content, embedding) rows in SQLite.
The table is rebuilt from scratch on every run (idempotent).
"""

import json
import sqlite3
from pathlib import Path

from foundry_local_sdk import Configuration, FoundryLocalManager

DATA_DIR = Path("data")
DB_PATH = Path("rag.db")
EMBEDDING_MODEL = "qwen3-embedding-0.6b"

def split_into_paragraphs(text):
    """Split raw document text into paragraph chunks.
    
    Paragraphs are separated by blank lines. 
    Surrounding whitespace is stripped and empty results are dropped.
    """
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]

def load_documents(data_dir: Path = DATA_DIR) -> list[tuple[str, str]]:
    """Load every .md and .txt file from the data directory.
    
    Returns (filename, text) tuples, sorted by filename.
    """
    paths = sorted(list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt")))
    documents =[]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        documents.append((path.name, text))
    return documents

def setup_database(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database and reset the chunks table.

    The table is cleared on every run so ingestion is an idempotent
    rebuild: re-runnig never creates duplicate rows.
    """
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS chunks("
        "id INTEGER PRIMARY KEY,"
        "source TEXT NOT NULL,"
        "content TEXT NOT NULL,"
        "embedding TEXT NOT NULL)"
    )
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(chunks)").fetchall()
    }
    if "source" not in columns:
        connection.execute(
            "ALTER TABLE chunks ADD COLUMN source TEXT NOT NULL DEFAULT 'unknown'"
        )
    connection.execute("DELETE FROM chunks")
    connection.commit()
    return connection

def setup_embedding_client():
    """Initialize Foundry Local and return the embedding model and client."""
    config = Configuration(app_name="local_rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    model = manager.catalog.get_model(EMBEDDING_MODEL)
    if model is None:
        raise RuntimeError(f"Model not found in catalog: {EMBEDDING_MODEL}")
    
    model.download()
    model.load()
    return model, model.get_embedding_client()

def main() -> None:
    documents = load_documents()
    print(f"Found {len(documents)} documents in {DATA_DIR}/")

    model = None
    connection = None
    total_chunks = 0
    try:
        model, client = setup_embedding_client()
        connection = setup_database()

        for filename, text in documents:
            paragraphs = split_into_paragraphs(text)
            for paragraph in paragraphs:
                response = client.generate_embedding(paragraph)
                vector = response.data[0].embedding
                connection.execute(
                    "INSERT INTO chunks "
                    "(source, content, embedding) VALUES (?, ?, ?)",
                    (filename, paragraph, json.dumps(vector)),
                )
            total_chunks += len(paragraphs)
            print(f" {filename}: {len(paragraphs)} chunks")

        connection.commit()
    finally:
        if connection is not None:
            connection.close()
        if model is not None:
            model.unload()
    print(f"Done. {total_chunks} chunks written to {DB_PATH}")

if __name__ == "__main__":
    main()
