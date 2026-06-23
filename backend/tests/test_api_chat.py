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


def test_chat_stream_emits_sse(client, fake_retriever, fake_llm):
    response = client.post(
        "/chat/stream",
        json={"question": "Resuma o Q3", "session_id": "stream"},
    )
    assert response.status_code == 200
    text = response.text
    assert "event: token" in text
    assert "event: done" in text
