"""Answer questions using retrieved knowledge base context.

Retrieves the top-K chunks for a question, packs them into a single
context block inside the system message, and asks the local chat model.
"""

from retrieve import get_top_chunks
from foundry_local_sdk import FoundryLocalManager

from ingest import setup_embedding_client

CHAT_MODEL = "qwen2.5-1.5b"

FALLBACK_ANSWER = "I don't know based on the provided documentation."
SIMILARITY_THRESHOLD = 0.5

SYSTEM_PROMPT = (
    "You are a helpful assistant for Microsoft Foundry Local documentation.\n"
    "Answer using ONLY the context below.\n"
    "\n"
    "First decide whether the context explicitly states the answer. Being about\n"
    "a related topic is not enough: if the context describes a different\n"
    "capability, or touches the question only in passing, it does not answer it.\n"
    "Never describe a step, method, or feature that is not written in the context.\n"
    "\n"
    "If the context does not explicitly answer the question, reply with exactly:\n"
    f'"{FALLBACK_ANSWER}"\n'
    "Otherwise answer in at most three sentences, using only what the context\n"
    "states. Cite supporting source labels in square brackets. Do not use outside\n"
    "knowledge. Do not guess.\n"
    "\n"
    "Context:\n"
    "{context}"
)


def build_context(chunks: list[tuple[float, str, str]]) -> str:
    return "\n\n---\n\n".join(
        f"[Source: {source}]\n{content}" for score, content, source in chunks
    )


def format_sources(chunks: list[tuple[float, str, str]]) -> str:
    sources = list(dict.fromkeys(source for score, content, source in chunks))
    return "Sources: " + ", ".join(sources)

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
    answer = response.choices[0].message.content.strip()
    if answer.strip('"') == FALLBACK_ANSWER:
        return FALLBACK_ANSWER
    return f"{answer}\n\n{format_sources(top_chunks)}"


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
