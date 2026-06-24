"""Per-session conversation history stored in Redis.

Each session keeps a capped list of the most recent messages so the RAG
pipeline can include short-term context in the prompt.
"""

from __future__ import annotations

import json

from app.config import PUBLIC_USER_ID, get_settings
from app.services.redis_client import get_redis

_HISTORY_PREFIX = "session:"


def _key(session_id: str, user_id: str) -> str:
    # Namespacing by user keeps two users' identically-named sessions apart.
    return f"{_HISTORY_PREFIX}{user_id}:{session_id}"


def get_history(session_id: str, user_id: str = PUBLIC_USER_ID) -> list[dict]:
    """Return the stored messages for a user's session (oldest first)."""
    settings = get_settings()
    client = get_redis()
    raw = client.lrange(_key(session_id, user_id), -settings.history_size, -1)
    messages: list[dict] = []
    for item in raw:
        text = item.decode("utf-8") if isinstance(item, bytes) else item
        try:
            messages.append(json.loads(text))
        except (ValueError, TypeError):
            continue
    return messages


def append_message(
    session_id: str, role: str, content: str, user_id: str = PUBLIC_USER_ID
) -> None:
    """Append a message to the user's session and trim to the configured window."""
    settings = get_settings()
    client = get_redis()
    key = _key(session_id, user_id)
    client.rpush(key, json.dumps({"role": role, "content": content}))
    # Keep only the last ``history_size`` messages.
    client.ltrim(key, -settings.history_size, -1)
