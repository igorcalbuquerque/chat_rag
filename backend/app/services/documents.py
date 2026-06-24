"""Document-level operations: list indexed documents and delete them.

Documents are groups of chunk hashes sharing the same ``file_id``. These
helpers aggregate over those hashes for listing and remove them on deletion.
"""

from __future__ import annotations

from app.config import PUBLIC_USER_ID, get_settings
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


def list_documents(user_id: str = PUBLIC_USER_ID) -> list[dict]:
    """Aggregate the caller's indexed chunks into one entry per document.

    Only documents owned by ``user_id`` are returned.
    """
    client = get_redis()
    docs: dict[str, dict] = {}

    keys = _iter_chunk_keys()
    if not keys:
        return []

    # Fetch every chunk's metadata in a single round-trip. Doing one ``hmget``
    # per key is fine on a local Redis but turns into thousands of sequential
    # network calls against a remote Redis (e.g. Redis Cloud in production),
    # which made the document list take many seconds to appear.
    pipe = client.pipeline()
    for key in keys:
        pipe.hmget(key, "file_id", "source", "uploaded_at", "user_id")
    for fields in pipe.execute():
        file_id = _decode(fields[0])
        if not file_id or _decode(fields[3]) != user_id:
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


def delete_document(file_id: str, user_id: str = PUBLIC_USER_ID) -> bool:
    """Delete every chunk of ``file_id`` **owned by ``user_id``**.

    Returns ``True`` if any keys were removed. A document belonging to another
    user is left untouched (returns ``False``), so one user cannot delete
    another's documents.
    """
    settings = get_settings()
    client = get_redis()
    pattern = f"{settings.redis_key_prefix}{file_id}:chunk:*"
    keys = list(client.scan_iter(match=pattern, count=500))
    if not keys:
        return False

    # Check ownership of all chunks in one round-trip (see list_documents).
    pipe = client.pipeline()
    for key in keys:
        pipe.hget(key, "user_id")
    owned = [key for key, owner in zip(keys, pipe.execute()) if _decode(owner) == user_id]
    if not owned:
        return False
    client.delete(*owned)
    return True
