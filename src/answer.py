"""Answer questions using retrieved knowledge base context.

Retrieves the top-K chunks for a question, packs them into a single
context block inside the system message, and asks the local chat model.
"""

from retrieve import get_top_chunks
from foundry_local_sdk import FoundryLocalManager

from ingest import setup_embedding_client

CHAT_MODEL = "qwen2.5-0.5b"

FALLBACK_ANSWER = "I don't know based on the provided documentation."
SIMILARITY_THRESHOLD = 0.6

SYSTEM_PROMPT = (
    "You are a helpful assistant for Microsoft Foundry Local documentation.\n"
    "Answer using ONLY the context below.\n"
    "If the context does not actually answer the question, reply with exactly:\n"
    f'"{FALLBACK_ANSWER}"\n'
    "Do not use outside knowledge. Do not guess.\n"
    "\n"
    "Context:\n"
    "{context}"
)


def build_context(chunks: list[tuple[float, str]]) -> str:
    """Join retrieved (score, content) pairs into one context block."""
    return "\n\n---\n\n".join(content for score, content in chunks)

def setup_chat_client():
    """Return the chat model and client from the already-initialized manager."""
    manager = FoundryLocalManager.instance
    model = manager.catalog.get_model(CHAT_MODEL)
    if model is None:
        raise RuntimeError(f"Model not found in catalog: {CHAT_MODEL}")
    model.download()
    model.load()
    return model, model.get_chat_client()


def answer_query(question: str, embedding_client, chat_client) -> str:
    """Answer a question using only retrieved documentation context."""
    top_chunks = get_top_chunks(question, embedding_client)
    if not top_chunks or top_chunks[0][0] < SIMILARITY_THRESHOLD:
        return FALLBACK_ANSWER
    context = build_context(top_chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]
    response = chat_client.complete_chat(messages)
    return response.choices[0].message.content


def main() -> None:
    embedding_model, embedding_client = setup_embedding_client()
    chat_model, chat_client = setup_chat_client()

    questions = [
        "Do I need an Azure subscription to use Foundry Local?",
        "What is the capital of Turkey?",
        "How do I make sourdough bread?",
        "What is the best Python web framework?",
    ]
    for question in questions:
        print(f"Q: {question}")
        print(f"A: {answer_query(question, embedding_client, chat_client)}")

    chat_model.unload()
    embedding_model.unload()


if __name__ == "__main__":
    main()