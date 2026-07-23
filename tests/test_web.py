import anyio
import httpx

import web


async def api_request(method, path, payload=None):
    transport = httpx.ASGITransport(app=web.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, json=payload)


def test_split_answer_and_sources():
    answer, sources = web.split_answer_and_sources(
        "Local answer.\n\nSources: first.md, second.md"
    )

    assert answer == "Local answer."
    assert sources == ["first.md", "second.md"]


def test_split_fallback_has_no_sources():
    answer, sources = web.split_answer_and_sources(web.FALLBACK_ANSWER)

    assert answer == web.FALLBACK_ANSWER
    assert sources == []


def test_source_list_returns_document_names(tmp_path, monkeypatch):
    (tmp_path / "second.txt").write_text("text", encoding="utf-8")
    (tmp_path / "first_document.md").write_text("text", encoding="utf-8")
    monkeypatch.setattr(web, "DATA_DIR", tmp_path)

    result = web.sources()

    assert result == [
        web.SourceItem(name="first_document.md", title="First Document"),
        web.SourceItem(name="second.txt", title="Second"),
    ]


def test_service_returns_structured_answer(monkeypatch):
    service = web.LocalRagService()
    service.embedding_client = object()
    service.chat_client = object()
    monkeypatch.setattr(
        web,
        "answer_query",
        lambda question, embedding_client, chat_client: (
            "Answer.\n\nSources: source.md"
        ),
    )

    result = service.ask("Question")

    assert result.answer == "Answer."
    assert result.sources == ["source.md"]


def test_service_removes_sources_from_fallback(monkeypatch):
    service = web.LocalRagService()
    service.embedding_client = object()
    service.chat_client = object()
    monkeypatch.setattr(
        web,
        "answer_query",
        lambda question, embedding_client, chat_client: (
            f"{web.FALLBACK_ANSWER}\n\nSources: unrelated.md"
        ),
    )

    result = service.ask("Unsupported")

    assert result.answer == web.FALLBACK_ANSWER
    assert result.sources == []


def test_home_page_is_served():
    response = anyio.run(api_request, "GET", "/")

    assert response.status_code == 200
    assert "Foundry Local Guide" in response.text


def test_health_endpoint_is_available():
    response = anyio.run(api_request, "GET", "/api/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"idle", "ready"}


def test_ask_endpoint_returns_answer_and_sources(monkeypatch):
    monkeypatch.setattr(
        web.service,
        "ask",
        lambda question: web.AskResponse(
            answer="Local answer.",
            sources=["source.md"],
        ),
    )

    response = anyio.run(
        api_request,
        "POST",
        "/api/ask",
        {"question": "Question"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Local answer.",
        "sources": ["source.md"],
    }
