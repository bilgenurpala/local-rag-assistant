"""Unit tests for the "I don't know" threshold logic in src/answer.py."""

from types import SimpleNamespace

import answer
from answer import FALLBACK_ANSWER, answer_query, build_context, format_sources


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
    low_chunks = [
        (0.32, "chunk one", "one.md"),
        (0.30, "chunk two", "two.md"),
        (0.29, "chunk three", "three.md"),
    ]
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
    good_chunks = [
        (0.83, "relevant chunk", "licensing.md"),
        (0.75, "another one", "overview.md"),
        (0.70, "third one", "overview.md"),
    ]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: good_chunks)
    chat_client = FakeChatClient()

    result = answer_query("Do I need an Azure subscription?", None, chat_client)

    assert chat_client.was_called is True
    assert result == "a model answer\n\nSources: licensing.md, overview.md"


def test_model_fallback_does_not_append_irrelevant_sources(monkeypatch):
    chunks = [(0.83, "related but insufficient", "overview.md")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: chunks)
    chat_client = FakeChatClient()
    chat_client.messages = None

    def fallback_response(messages):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=FALLBACK_ANSWER)
                )
            ]
        )

    chat_client.complete_chat = fallback_response

    result = answer_query("An unsupported question", None, chat_client)

    assert result == FALLBACK_ANSWER


def test_score_exactly_at_threshold_calls_model(monkeypatch):
    """The threshold is exclusive: a score equal to it is good enough."""
    chunks = [(answer.SIMILARITY_THRESHOLD, "borderline chunk", "source.md")]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: chunks)
    chat_client = FakeChatClient()

    result = answer_query("A borderline question", None, chat_client)

    assert chat_client.was_called is True
    assert result == "a model answer\n\nSources: source.md"


def test_score_just_below_threshold_returns_fallback(monkeypatch):
    chunks = [
        (answer.SIMILARITY_THRESHOLD - 0.001, "borderline chunk", "source.md")
    ]
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
    chunks = [
        (0.90, "the first chunk", "first.md"),
        (0.80, "the second chunk", "second.md"),
    ]
    monkeypatch.setattr(answer, "get_top_chunks", lambda question, client: chunks)
    chat_client = FakeChatClient()

    answer_query("Any question", None, chat_client)

    system_message, user_message = chat_client.messages
    assert system_message["role"] == "system"
    assert "the first chunk" in system_message["content"]
    assert "the second chunk" in system_message["content"]
    assert "[Source: first.md]" in system_message["content"]
    assert "[Source: second.md]" in system_message["content"]
    assert user_message == {"role": "user", "content": "Any question"}


def test_build_context_separates_chunks_and_labels_sources():
    context = build_context(
        [(0.9, "first", "first.md"), (0.8, "second", "second.md")]
    )

    assert context == (
        "[Source: first.md]\nfirst\n\n---\n\n"
        "[Source: second.md]\nsecond"
    )


def test_format_sources_deduplicates_and_preserves_rank_order():
    chunks = [
        (0.9, "first", "a.md"),
        (0.8, "second", "b.md"),
        (0.7, "third", "a.md"),
    ]

    assert format_sources(chunks) == "Sources: a.md, b.md"
