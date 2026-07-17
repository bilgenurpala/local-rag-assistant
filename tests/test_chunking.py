"""Unit tests for the chunking logic in src/ingest.py."""

from ingest import split_into_paragraphs


def test_single_paragraph_returns_single_chunk():
    text = "Foundry Local runs models fully on-device."
    assert split_into_paragraphs(text) == [text]


def test_paragraphs_are_split_on_blank_lines():
    text = "First paragraph.\n\nSecond paragraph."
    assert split_into_paragraphs(text) == ["First paragraph.", "Second paragraph."]


def test_surrounding_whitespace_is_stripped():
    text = "  First paragraph.  \n\n\nSecond paragraph.\n"
    assert split_into_paragraphs(text) == ["First paragraph.", "Second paragraph."]


def test_empty_text_returns_no_chunks():
    assert split_into_paragraphs("") == []


def test_blank_lines_only_returns_no_chunks():
    assert split_into_paragraphs("\n\n\n\n") == []

