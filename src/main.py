"""CLI entry point for the local RAG assistant.

Runs an interactive loop: the user asks a question, the answer is
printed, and the loop repeats until the user types exit or quit.
"""

from answer import answer_query, setup_chat_client
from ingest import setup_embedding_client


def main() -> None:
    print("Local RAG Assistant")
    print("Loading models, this may take a moment...")

    embedding_model = None
    chat_model = None
    try:
        embedding_model, embedding_client = setup_embedding_client()
        chat_model, chat_client = setup_chat_client()

        print("Ready. Ask a question about Foundry Local.")
        print("Type 'exit' or 'quit' to leave.\n")

        while True:
            question = input("> ").strip()

            if not question:
                print("Please type a question.\n")
                continue

            if question.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break
            answer = answer_query(question, embedding_client, chat_client)
            print(f"\n{answer}\n")
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
    finally:
        if chat_model is not None:
            chat_model.unload()
        if embedding_model is not None:
            embedding_model.unload()


if __name__ == "__main__":
    main()
