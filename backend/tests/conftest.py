"""Shared pytest fixtures.

Real external dependencies are replaced with fakes so tests never hit Redis,
OpenAI, Anthropic or Ollama:

* Redis        -> fakeredis (supports hashes, lists, scan_iter)
* Embeddings   -> deterministic local vectors
* LLM          -> canned answer with invoke()/stream()
"""

from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import config
from app.services import documents, history, ingestion, rag_graph, redis_client


# --- Fakes ---
class FakeEmbeddings:
    """Deterministic embeddings: hash-based vectors of fixed dimension."""

    DIM = 8

    def _vec(self, text: str) -> list[float]:
        return [((hash(text) >> (i * 3)) & 0xFF) / 255.0 for i in range(self.DIM)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class _FakeChunk:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Minimal chat model stub supporting invoke() and stream()."""

    ANSWER = "Resposta de teste baseada no contexto."

    def invoke(self, messages):
        return _FakeChunk(self.ANSWER)

    def stream(self, messages):
        for word in self.ANSWER.split():
            yield _FakeChunk(word + " ")


# --- Fixtures ---
@pytest.fixture(autouse=True)
def reset_settings():
    """Ensure each test gets fresh, default settings."""
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def fake_redis():
    """Install a fakeredis client as the global Redis connection."""
    client = fakeredis.FakeStrictRedis(decode_responses=False)
    redis_client.set_redis(client)
    yield client
    client.flushall()
    redis_client.set_redis(None)


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Patch the embeddings factory everywhere it is used."""
    emb = FakeEmbeddings()
    monkeypatch.setattr(ingestion, "get_embeddings", lambda api_key=None: emb)
    return emb


@pytest.fixture
def fake_llm(monkeypatch):
    """Patch the LLM factory used inside the RAG graph."""
    llm = FakeLLM()
    monkeypatch.setattr(rag_graph, "get_llm", lambda api_key=None, provider=None: llm)
    return llm


@pytest.fixture
def fake_retriever(monkeypatch):
    """Patch retrieval so chat tests don't need RediSearch vector support."""
    chunks = [
        {
            "chunk": "O lucro do Q3 cresceu 20%.",
            "source": "relatorio_q3.pdf",
            "chunk_index": 0,
            "score": 0.91,
        }
    ]
    monkeypatch.setattr(rag_graph, "retrieve", lambda q, k=None, api_key=None: chunks)
    return chunks


@pytest.fixture
def client(fake_redis):
    """FastAPI TestClient with Redis faked (no lifespan side effects)."""
    from app.main import app

    return TestClient(app)
