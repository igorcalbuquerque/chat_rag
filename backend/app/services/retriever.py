"""Semantic retrieval: KNN vector search over the Redis index."""

from __future__ import annotations

import numpy as np
from redis.commands.search.query import Query

from app.config import get_settings
from app.services.embeddings import get_embeddings
from app.services.redis_client import get_redis


def _decode(value: bytes | str | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8") if isinstance(value, bytes) else value


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    """Embed the question and return the ``top_k`` most similar chunks.

    Each result dict contains ``chunk``, ``source``, ``chunk_index`` and a
    cosine-similarity ``score`` in ``[0, 1]`` (1 = most similar).
    """
    settings = get_settings()
    k = top_k or settings.top_k

    query_vector = get_embeddings().embed_query(question)
    query_bytes = np.asarray(query_vector, dtype=np.float32).tobytes()

    # RediSearch KNN syntax: return the closest k vectors by cosine distance.
    redis_query = (
        Query(f"*=>[KNN {k} @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("content", "source", "chunk_index", "score")
        .dialect(2)
    )

    client = get_redis()
    result = client.ft(settings.redis_index_name).search(
        redis_query, query_params={"vec": query_bytes}
    )

    chunks: list[dict] = []
    for doc in result.docs:
        # RediSearch returns cosine *distance*; similarity = 1 - distance.
        distance = float(_decode(getattr(doc, "score", "1")) or 1.0)
        chunks.append(
            {
                "chunk": _decode(getattr(doc, "content", "")),
                "source": _decode(getattr(doc, "source", "")),
                "chunk_index": int(_decode(getattr(doc, "chunk_index", "0")) or 0),
                "score": round(1.0 - distance, 4),
            }
        )
    return chunks
