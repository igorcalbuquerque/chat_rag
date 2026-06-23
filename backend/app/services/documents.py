"""Document-level operations: list indexed documents and delete them.

Documents are groups of chunk hashes sharing the same ``file_id``. These
helpers aggregate over those hashes for listing and remove them on deletion.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.redis_client import get_redis


def _decode(value: bytes | str | None) -> str:
    """Decode a Redis byte value to ``str`` (no-op for already-decoded)."""
    if value is None:
        return ""
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _iter_chunk_keys() -> list[bytes]:
    """Return all chunk keys matching the configured key prefix."""
    settings = get_settings()
    client = get_redis()
    pattern = f"{settings.redis_key_prefix}*"
    return list(client.scan_iter(match=pattern, count=500))


def list_documents() -> list[dict]:
    """Aggregate indexed chunks into one entry per document."""
    client = get_redis()
    docs: dict[str, dict] = {}

    for key in _iter_chunk_keys():
        fields = client.hmget(key, "file_id", "source", "uploaded_at")
        file_id = _decode(fields[0])
        if not file_id:
            continue
        entry = docs.setdefault(
            file_id,
            {
                "file_id": file_id,
                "name": _decode(fields[1]),
                "uploaded_at": _decode(fields[2]),
                "chunks": 0,
            },
        )
        entry["chunks"] += 1

    return sorted(docs.values(), key=lambda d: d["uploaded_at"], reverse=True)


def delete_document(file_id: str) -> bool:
    """Delete every chunk belonging to ``file_id``. Returns ``True`` if any
    keys were removed."""
    settings = get_settings()
    client = get_redis()
    pattern = f"{settings.redis_key_prefix}{file_id}:chunk:*"
    keys = list(client.scan_iter(match=pattern, count=500))
    if not keys:
        return False
    client.delete(*keys)
    return True
