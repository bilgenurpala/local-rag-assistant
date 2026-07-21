"""Unit tests for the "I don't know" threshold logic in src/answer.py."""

from types import SimpleNamespace

import answer
from answer import FALLBACK_ANSWER, answer_query, build_context


class FakeChatClient:
    """Records whether the chat model was called, and with which messages."""

    def __init__(self):
        self.was_called = False
        self.messages = None

    def complete_chat(self, messages):
        self.was_called = True
        self.messages = messages
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


def test_score_exactly_at_threshold_calls_model(monkeypatch):
    """The threshold is exclusive: a score equal to it is good enough."""
    chunks = [(answer.SIMILARITY_THRESHOLD, "borderline chunk")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: chunks)
    chat_client = FakeChatClient()

    result = answer_query("A borderline question", None, chat_client)

    assert chat_client.was_called is True
    assert result == "a model answer"


def test_score_just_below_threshold_returns_fallback(monkeypatch):
    chunks = [(answer.SIMILARITY_THRESHOLD - 0.001, "borderline chunk")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: chunks)
    chat_client = FakeChatClient()

    result = answer_query("A borderline question", None, chat_client)

    assert result == FALLBACK_ANSWER
    assert chat_client.was_called is False


def test_threshold_is_the_calibrated_value():
    """Pinned on purpose.

    0.5 was not chosen by feel: it sits in the widest empty band of the
    score distribution measured in docs/evaluation.md. Changing it should
    be a deliberate edit backed by new measurements, not a silent tweak.
    """
    assert answer.SIMILARITY_THRESHOLD == 0.5


def test_retrieved_context_reaches_the_model(monkeypatch):
    """Every retrieved chunk must appear in the system message."""
    chunks = [(0.90, "the first chunk"), (0.80, "the second chunk")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: chunks)
    chat_client = FakeChatClient()

    answer_query("Any question", None, chat_client)

    system_message, user_message = chat_client.messages
    assert system_message["role"] == "system"
    assert "the first chunk" in system_message["content"]
    assert "the second chunk" in system_message["content"]
    assert user_message == {"role": "user", "content": "Any question"}


def test_build_context_separates_chunks():
    context = build_context([(0.9, "first"), (0.8, "second")])

    assert context == "first\n\n---\n\nsecond"