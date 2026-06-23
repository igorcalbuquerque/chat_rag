"""Redis connection and RediSearch vector index management.

The index stores one Redis HASH per chunk under the key
``{prefix}{file_id}:chunk:{n}`` with the following fields:

    content      TEXT      the raw chunk text
    source       TAG       original file name
    file_id      TAG       uuid grouping all chunks of a document
    chunk_index  NUMERIC   position of the chunk within the document
    uploaded_at  TEXT      ISO-8601 upload timestamp
    embedding    VECTOR    float32 embedding (HNSW, COSINE distance)
"""

from __future__ import annotations

import redis
from redis.commands.search.field import (
    NumericField,
    TagField,
    TextField,
    VectorField,
)
try:  # redis-py >= 6 renamed this module to snake_case
    from redis.commands.search.index_definition import IndexDefinition, IndexType
except ImportError:  # redis-py < 6
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from app.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return a process-wide Redis client (lazily created).

    ``decode_responses`` is left ``False`` because embeddings are stored as
    raw float32 bytes; text fields are decoded explicitly where needed.
    """
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    return _client


def set_redis(client: redis.Redis) -> None:
    """Override the global client (used by tests with fakeredis)."""
    global _client
    _client = client


def ping() -> bool:
    """Return ``True`` if Redis is reachable."""
    try:
        return bool(get_redis().ping())
    except redis.exceptions.RedisError:
        return False


def ensure_index() -> None:
    """Create the RediSearch vector index if it does not already exist.

    Idempotent: a pre-existing index is treated as success so the call is
    safe to run on every application startup.
    """
    settings = get_settings()
    client = get_redis()

    try:
        client.ft(settings.redis_index_name).info()
        return  # index already exists
    except redis.exceptions.ResponseError:
        pass  # index missing -> create below

    schema = (
        TextField("content"),
        TagField("source"),
        TagField("file_id"),
        NumericField("chunk_index"),
        TextField("uploaded_at"),
        VectorField(
            "embedding",
            "HNSW",
            {
                "TYPE": "FLOAT32",
                "DIM": settings.embedding_dimension,
                "DISTANCE_METRIC": "COSINE",
            },
        ),
    )
    definition = IndexDefinition(
        prefix=[settings.redis_key_prefix], index_type=IndexType.HASH
    )
    client.ft(settings.redis_index_name).create_index(schema, definition=definition)
