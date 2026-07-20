"""Unit tests for the "I don't know" threshold logic in src/answer.py."""

from types import SimpleNamespace

import answer
from answer import FALLBACK_ANSWER, answer_query


class FakeChatClient:
    """Records whether the chat model was called."""

    def __init__(self):
        self.was_called = False

    def complete_chat(self, messages):
        self.was_called = True
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="a model answer"))]
        )


def test_low_similarity_returns_fallback_without_calling_model(monkeypatch):
    low_chunks = [(0.32, "chunk one"), (0.30, "chunk two"), (0.29, "chunk three")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: low_chunks)
    chat_client = FakeChatClient()

    result = answer_query("How do I make sourdough bread?", None, chat_client)

    assert result == FALLBACK_ANSWER
    assert chat_client.was_called is False


def test_empty_database_returns_fallback_without_calling_model(monkeypatch):
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: [])
    chat_client = FakeChatClient()

    result = answer_query("Any question at all", None, chat_client)

    assert result == FALLBACK_ANSWER
    assert chat_client.was_called is False


def test_high_similarity_calls_model(monkeypatch):
    good_chunks = [(0.83, "relevant chunk"), (0.75, "another one"), (0.70, "third one")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: good_chunks)
    chat_client = FakeChatClient()

    result = answer_query("Do I need an Azure subscription?", None, chat_client)

    assert chat_client.was_called is True
    assert result == "a model answer"