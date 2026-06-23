"""Unit test for retriever result parsing (no real RediSearch needed)."""

from __future__ import annotations

from app.services import redis_client, retriever


class _FakeDoc:
    def __init__(self, content, source, chunk_index, score):
        self.content = content
        self.source = source
        self.chunk_index = chunk_index
        self.score = score


class _FakeResult:
    def __init__(self, docs):
        self.docs = docs


class _FakeFT:
    def __init__(self, result):
        self.result = result
        self.last_query = None

    def search(self, query, query_params=None):
        self.last_query = (query, query_params)
        return self.result


class _FakeClient:
    def __init__(self, result):
        self._ft = _FakeFT(result)

    def ft(self, name):
        return self._ft


class _FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


def test_retrieve_parses_and_scores(monkeypatch):
    monkeypatch.setattr(retriever, "get_embeddings", lambda api_key=None: _FakeEmbeddings())
    docs = [
        _FakeDoc("primeiro", "a.pdf", "2", "0.1"),
        _FakeDoc("segundo", "b.pdf", "0", "0.4"),
        # A doc with missing/None fields must decode to safe defaults.
        _FakeDoc(None, None, None, None),
    ]
    redis_client.set_redis(_FakeClient(_FakeResult(docs)))

    out = retriever.retrieve("pergunta", top_k=3)

    assert len(out) == 3
    assert out[0] == {
        "chunk": "primeiro",
        "source": "a.pdf",
        "chunk_index": 2,
        "score": round(1.0 - 0.1, 4),  # cosine distance -> similarity
    }
    assert out[2] == {"chunk": "", "source": "", "chunk_index": 0, "score": 0.0}
    redis_client.set_redis(None)


def test_retrieve_defaults_top_k_from_settings(monkeypatch):
    monkeypatch.setattr(retriever, "get_embeddings", lambda api_key=None: _FakeEmbeddings())
    client = _FakeClient(_FakeResult([]))
    redis_client.set_redis(client)

    assert retriever.retrieve("pergunta") == []  # top_k falls back to settings
    assert client._ft.last_query is not None
    redis_client.set_redis(None)
