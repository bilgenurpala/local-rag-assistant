"""Run the Sprint 4 evaluation question set through the assistant.

Prints, for each question, the top retrieval score, the elapsed time and
the assistant's answer, so the results can be pasted into
docs/evaluation.md. Run from the repository root:  python prototypes/evaluation_run.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from answer import CHAT_MODEL, answer_query, setup_chat_client
from ingest import setup_embedding_client
from retrieve import get_top_chunks

ANSWERABLE = [
    "Do I need an Azure subscription to use Foundry Local?",
    "Which platforms does Foundry Local support?",
    "Which Python version is required, and which package should I install on Windows?",
    "What runtime does Foundry Local use for inference?",
    "Is Foundry Local suitable for serving many concurrent users?",
]

UNANSWERABLE = [
    "How do I make sourdough bread?",
    "Which company acquired GitHub?",
    "How do I fine-tune a model in Foundry Local?",
    "Does Foundry Local support Android or iOS?",
    "How much does Foundry Local cost per month?",
]


def run(question: str, embedding_client, chat_client) -> None:
    """Ask one question and print its score, latency and answer."""
    top_chunks = get_top_chunks(question, embedding_client)
    top_score = top_chunks[0][0] if top_chunks else 0.0

    start = time.perf_counter()
    answer = answer_query(question, embedding_client, chat_client)
    elapsed = time.perf_counter() - start

    print(f"Q: {question}")
    print(f"   top_score={top_score:.3f}  time={elapsed:.1f}s")
    print(f"A: {answer}\n")


def main() -> None:
    print("Loading embedding model...", flush=True)
    embedding_model, embedding_client = setup_embedding_client()

    print(f"Loading chat model {CHAT_MODEL} (first run downloads it)...", flush=True)
    chat_model, chat_client = setup_chat_client()

    print("\n===== ANSWERABLE =====\n")
    for question in ANSWERABLE:
        run(question, embedding_client, chat_client)

    print("===== UNANSWERABLE =====\n")
    for question in UNANSWERABLE:
        run(question, embedding_client, chat_client)

    chat_model.unload()
    embedding_model.unload()


if __name__ == "__main__":
    main()