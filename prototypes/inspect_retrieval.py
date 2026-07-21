"""Inspect which chunks are retrieved for a single question.

Diagnostic used in the Sprint 4 evaluation to tell a retrieval failure
apart from a context-selection failure. The question and the number of
chunks can be passed on the command line:

    python prototypes/inspect_retrieval.py "Which platforms are supported?" 5
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingest import setup_embedding_client
from retrieve import get_top_chunks

DEFAULT_QUESTION = "What runtime does Foundry Local use for inference?"

QUESTION = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
TOP_K = int(sys.argv[2]) if len(sys.argv) > 2 else 3


def main() -> None:
    model, client = setup_embedding_client()

    print(f"Q: {QUESTION}  (top {TOP_K})\n")
    for rank, (score, content) in enumerate(get_top_chunks(QUESTION, client, TOP_K), start=1):
        print(f"{rank}. {score:.3f}  {content[:150]}...\n")

    model.unload()


if __name__ == "__main__":
    main()