"""Integration test for the real RediSearch vector path.

Unlike the unit tests (which mock ``retrieve``), this exercises the full
``ensure_index`` -> ``ingest_file`` -> ``retrieve`` -> ``delete_document``
flow against a **real Redis Stack** (RediSearch module required for KNN).

It self-skips when no Redis Stack is reachable, so the default unit suite and
the standard CI job stay fast and green. A dedicated CI job runs it with a
``redis/redis-stack`` service.

Embeddings are deterministic and produced locally (no torch, no paid API):
each vector has exactly ``settings.embedding_dimension`` dimensions, so it
always matches the index dimension.
"""

from __future__ import annotations

import hashlib

import pytest
import redis

from app.config import get_settings
from app.services import documents, ingestion, redis_client, retriever

pytestmark = pytest.mark.integration


class IntegrationEmbeddings:
    """Deterministic embeddings sized to the configured index dimension."""

    def _vec(self, text: str) -> list[float]:
        dim = get_settings().embedding_dimension
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Repeat the hash bytes to fill the dimension, normalized to [0, 1].
        return [digest[i % len(digest)] / 255.0 for i in range(dim)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


@pytest.fixture(scope="module", autouse=True)
def real_redis():
    """Connect to a real Redis Stack or skip the whole module."""
    settings = get_settings()
    # Use the app's own connection factory so the test exercises the same
    # client configuration (RESP2, etc.) as production code.
    client = redis_client.get_redis()
    try:
        client.ping()
    except redis.exceptions.RedisError as exc:
        pytest.skip(f"Redis Stack not available: {exc}")

    # Drop any pre-existing index so the dimension matches this test's
    # embeddings, then (re)create it. Requires the RediSearch module.
    try:
        client.ft(settings.redis_index_name).dropindex(delete_documents=True)
    except redis.exceptions.ResponseError:
        pass  # index did not exist
    try:
        redis_client.ensure_index()
    except redis.exceptions.RedisError as exc:
        pytest.skip(f"RediSearch module not available: {exc}")

    yield client

    # Clean up any keys created by this module.
    for key in client.scan_iter(match=f"{settings.redis_key_prefix}*"):
        client.delete(key)
    redis_client.set_redis(None)


@pytest.fixture(autouse=True)
def patch_embeddings(monkeypatch):
    emb = IntegrationEmbeddings()
    monkeypatch.setattr(ingestion, "get_embeddings", lambda: emb)
    monkeypatch.setattr(retriever, "get_embeddings", lambda: emb)
    return emb


def test_index_ingest_retrieve_delete(real_redis):
    # Two clearly distinct documents.
    doc_a = ingestion.ingest_file(
        "finance.txt", b"O lucro do terceiro trimestre cresceu vinte por cento."
    )
    doc_b = ingestion.ingest_file(
        "weather.txt", b"A previsao do tempo indica chuva forte no fim de semana."
    )
    assert doc_a["chunks_indexed"] >= 1
    assert doc_b["chunks_indexed"] >= 1

    # KNN search returns scored chunks ordered by similarity.
    results = retriever.retrieve("Qual foi o lucro do trimestre?", top_k=3)
    assert results, "expected at least one retrieved chunk"
    assert all(0.0 <= r["score"] <= 1.0 for r in results)
    sources = {r["source"] for r in results}
    assert "finance.txt" in sources

    # Deleting a document removes its vectors from the index.
    assert documents.delete_document(doc_a["file_id"]) is True
    after = retriever.retrieve("Qual foi o lucro do trimestre?", top_k=5)
    assert all(r["source"] != "finance.txt" for r in after)
