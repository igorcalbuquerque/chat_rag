"""Shared FastAPI dependencies.

``get_current_user`` is the single auth gate used by the protected endpoints.
It is a no-op when auth is disabled (local dev), returning a fixed public user
so the rest of the code always has a ``user_id`` to scope data by.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import PUBLIC_USER_ID, get_settings
from app.services.auth import read_token


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict:
    """Resolve the current user from the bearer token.

    With ``AUTH_ENABLED`` off, returns the public user (no token required).
    With it on, a valid ``Authorization: Bearer <token>`` is mandatory.
    """
    if not get_settings().auth_enabled:
        return {"user_id": PUBLIC_USER_ID, "name": "local", "provider": "none"}

    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[len("bearer ") :].strip()

    user = read_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
