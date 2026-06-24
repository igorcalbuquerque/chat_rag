"""Tests for the POST /chat RAG endpoint (Redis + LLM mocked)."""

from __future__ import annotations

from app.services import history, rag_graph


def test_chat_returns_answer_and_sources(client, fake_retriever, fake_llm):
    response = client.post(
        "/chat",
        json={"question": "Quais foram os resultados do Q3?", "session_id": "s1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == fake_llm.ANSWER
    assert body["session_id"] == "s1"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["source"] == "relatorio_q3.pdf"
    assert body["sources"][0]["score"] == 0.91


def test_chat_persists_history(client, fake_redis, fake_retriever, fake_llm):
    client.post("/chat", json={"question": "Pergunta 1", "session_id": "hist"})

    stored = history.get_history("hist")
    roles = [m["role"] for m in stored]
    assert "user" in roles and "assistant" in roles


def test_run_rag_builds_context_from_history(
    fake_redis, fake_retriever, fake_llm
):
    history.append_message("ctx", "user", "pergunta anterior")
    history.append_message("ctx", "assistant", "resposta anterior")

    result = rag_graph.run_rag("nova pergunta", "ctx")
    assert result["answer"] == fake_llm.ANSWER
    assert result["sources"][0]["source"] == "relatorio_q3.pdf"


def test_chat_forwards_api_key_header(client, monkeypatch):
    from app.routers import chat as chat_router

    captured = {}

    def fake_run_rag(
        question, session_id, top_k=None, api_key=None, llm_provider=None, user_id="public"
    ):
        captured["api_key"] = api_key
        return {"answer": "ok", "sources": [], "session_id": session_id}

    monkeypatch.setattr(chat_router, "run_rag", fake_run_rag)
    response = client.post(
        "/chat",
        json={"question": "oi", "session_id": "s"},
        headers={"X-API-Key": "sk-byok"},
    )
    assert response.status_code == 200
    assert captured["api_key"] == "sk-byok"


def test_chat_forwards_llm_provider_header(client, monkeypatch):
    from app.routers import chat as chat_router

    captured = {}

    def fake_run_rag(
        question, session_id, top_k=None, api_key=None, llm_provider=None, user_id="public"
    ):
        captured["provider"] = llm_provider
        return {"answer": "ok", "sources": [], "session_id": session_id}

    monkeypatch.setattr(chat_router, "run_rag", fake_run_rag)
    response = client.post(
        "/chat",
        json={"question": "oi", "session_id": "s"},
        headers={"X-LLM-Provider": "gemini"},
    )
    assert response.status_code == 200
    assert captured["provider"] == "gemini"


def test_chat_rejects_unsupported_provider(client):
    response = client.post(
        "/chat",
        json={"question": "oi", "session_id": "s"},
        headers={"X-LLM-Provider": "bogus"},
    )
    assert response.status_code == 400


def test_chat_stream_emits_sse(client, fake_retriever, fake_llm):
    response = client.post(
        "/chat/stream",
        json={"question": "Resuma o Q3", "session_id": "stream"},
    )
    assert response.status_code == 200
    text = response.text
    assert "event: token" in text
    assert "event: done" in text


def test_chat_stream_emits_error_event_on_llm_failure(client, monkeypatch):
    from app.routers import chat as chat_router

    def boom():
        raise RuntimeError("provider exploded")
        yield  # pragma: no cover - makes this a generator

    monkeypatch.setattr(
        chat_router,
        "stream_rag",
        lambda *a, **k: (boom(), []),
    )
    response = client.post(
        "/chat/stream",
        json={"question": "oi", "session_id": "boom"},
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "provider exploded" in response.text
