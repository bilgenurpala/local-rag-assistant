import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from answer import FALLBACK_ANSWER, answer_query, setup_chat_client
from ingest import setup_embedding_client
from retrieve import get_top_chunks

OUTPUT_PATH = Path("docs/blind-evaluation-results.json")


@dataclass(frozen=True)
class Case:
    question: str
    answerable: bool
    expected_terms: tuple[str, ...] = ()


CASES = [
    Case(
        "Where are prompts and model outputs processed during normal inference?",
        True,
        ("device",),
    ),
    Case(
        "When can Foundry Local still need an internet connection after setup?",
        True,
        ("download",),
    ),
    Case(
        "What happens when a supported GPU or NPU accelerator is unavailable?",
        True,
        ("cpu",),
    ),
    Case(
        "Which method gives a chat client after a model has been loaded?",
        True,
        ("get_chat_client",),
    ),
    Case(
        "Why is the Foundry Local model catalog curated instead of open-ended?",
        True,
        ("production", "consumer hardware"),
    ),
    Case("Does Foundry Local encrypt the application's SQLite database?", False),
    Case("Can Foundry Local import and parse PDF files automatically?", False),
    Case("What is the maximum number of chat messages in one request?", False),
    Case("Which license applies to every model in the catalog?", False),
    Case("How do I deploy this assistant to Kubernetes?", False),
]


def automatic_pass(case: Case, answer: str) -> bool:
    answer_body = answer.split("\n\nSources:", maxsplit=1)[0].strip()
    normalized = answer_body.casefold()
    if not case.answerable:
        return normalized == FALLBACK_ANSWER.casefold()
    return all(term.casefold() in normalized for term in case.expected_terms)


def main() -> None:
    embedding_model = None
    chat_model = None
    results = []
    try:
        embedding_model, embedding_client = setup_embedding_client()
        chat_model, chat_client = setup_chat_client()

        for index, case in enumerate(CASES, start=1):
            top_chunks = get_top_chunks(case.question, embedding_client)
            top_score = top_chunks[0][0] if top_chunks else 0.0
            started = time.perf_counter()
            answer = answer_query(case.question, embedding_client, chat_client)
            elapsed = time.perf_counter() - started
            passed = automatic_pass(case, answer)
            result = {
                "id": index,
                "question": case.question,
                "answerable": case.answerable,
                "expected_terms": list(case.expected_terms),
                "answer": answer,
                "top_score": round(top_score, 3),
                "latency_seconds": round(elapsed, 2),
                "automatic_pass": passed,
            }
            results.append(result)
            status = "PASS" if passed else "FAIL"
            print(f"{index:02d} {status} score={top_score:.3f} time={elapsed:.2f}s")
            print(f"Q: {case.question}")
            print(f"A: {answer}\n")
    finally:
        if chat_model is not None:
            chat_model.unload()
        if embedding_model is not None:
            embedding_model.unload()

    report = {
        "method": (
            "Frozen ten-question blind set: five answerable and five "
            "unanswerable. Configuration was not tuned after this run."
        ),
        "passed": sum(result["automatic_pass"] for result in results),
        "total": len(results),
        "results": results,
    }
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {report['passed']}/{report['total']} results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
