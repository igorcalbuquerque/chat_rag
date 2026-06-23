"""Integration test for the real RediSearch vector path.

Unlike the unit tests (which mock ``retrieve``), this exercises the full
``ensure_index`` -> ``ingest_file`` -> ``retrieve`` -> ``delete_document``
flow against a **real Redis Stack** (RediSearch module required for KNN).

Safety / isolation:
- Marked ``integration`` and excluded from the default suite (see
  ``pyproject.toml``), so a plain ``pytest`` never runs it.
- Uses a dedicated **test index and key prefix**, so even when pointed at a
  shared Redis it never touches the application's ``docs`` index or ``doc:``
  keys. The destructive ``dropindex`` only ever targets the test index.
- Locally it self-skips when no Redis Stack is reachable. In the dedicated CI
  job (``REQUIRE_INTEGRATION=1``) it waits for Redis and **fails loudly**
  instead of skipping, so the job can't go green without actually testing.

Embeddings are deterministic and produced locally (no torch, no paid API):
each vector has exactly ``settings.embedding_dimension`` dimensions, so it
always matches the index dimension.
"""

from __future__ import annotations

import hashlib
import os
import time

import pytest
import redis

from app.config import get_settings
from app.services import documents, ingestion, redis_client, retriever

pytestmark = pytest.mark.integration

# Dedicated namespace so the test never collides with real app data.
_TEST_INDEX = "test_docs"
_TEST_PREFIX = "test:doc:"

# In the dedicated CI job this is set so missing Redis/RediSearch fails the
# build instead of silently skipping.
REQUIRE_INTEGRATION = os.environ.get("REQUIRE_INTEGRATION") == "1"


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


def _unavailable(message: str) -> None:
    """Fail when integration is required, otherwise skip."""
    if REQUIRE_INTEGRATION:
        pytest.fail(message)
    pytest.skip(message)


def _wait_for_redis(client: redis.Redis, attempts: int = 30, delay: float = 1.0):
    """Poll Redis until it answers PING; return True or the last error."""
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            client.ping()
            return True
        except redis.exceptions.RedisError as exc:
            last_exc = exc
            time.sleep(delay)
    return last_exc


@pytest.fixture(scope="module", autouse=True)
def real_redis():
    """Provision an isolated test index on a real Redis Stack."""
    # Point the app at a test-only index/prefix for the duration of the module.
    previous = {
        "REDIS_INDEX_NAME": os.environ.get("REDIS_INDEX_NAME"),
        "REDIS_KEY_PREFIX": os.environ.get("REDIS_KEY_PREFIX"),
    }
    os.environ["REDIS_INDEX_NAME"] = _TEST_INDEX
    os.environ["REDIS_KEY_PREFIX"] = _TEST_PREFIX
    get_settings.cache_clear()
    redis_client.set_redis(None)  # rebuild the client against test settings

    client = redis_client.get_redis()
    ready = _wait_for_redis(client)
    if ready is not True:
        _unavailable(f"Redis Stack not reachable: {ready}")

    # Fresh test index (drops ONLY the test index, never the app's).
    try:
        client.ft(_TEST_INDEX).dropindex(delete_documents=True)
    except redis.exceptions.ResponseError:
        pass  # index did not exist
    try:
        redis_client.ensure_index()
    except redis.exceptions.RedisError as exc:
        _unavailable(f"RediSearch module not available: {exc}")

    yield client

    # Cleanup: remove test keys + index, then restore env and client.
    for key in client.scan_iter(match=f"{_TEST_PREFIX}*"):
        client.delete(key)
    try:
        client.ft(_TEST_INDEX).dropindex(delete_documents=True)
    except redis.exceptions.ResponseError:
        pass
    for name, value in previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    get_settings.cache_clear()
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
