"""Authentication helpers: OAuth client registry and signed login tokens.

Active only when ``AUTH_ENABLED`` is true. The OAuth handshake (login redirect
+ callback) is handled by Authlib using a short-lived session cookie; once a
user is identified, a signed bearer token is issued (itsdangerous) and the
browser sends it back as ``Authorization: Bearer`` on every request. The API
itself stays stateless — no server-side session store.
"""

from __future__ import annotations

import re
from functools import lru_cache

from authlib.integrations.starlette_client import OAuth
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

_GOOGLE_METADATA = "https://accounts.google.com/.well-known/openid-configuration"
_GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN = "https://github.com/login/oauth/access_token"  # noqa: S105
_GITHUB_API = "https://api.github.com/"

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]")


@lru_cache
def get_oauth() -> OAuth:
    """Build and cache the Authlib OAuth registry from configured credentials.

    Google is registered via OIDC discovery; GitHub via its explicit OAuth
    endpoints. Providers without configured credentials are simply not usable.
    """
    settings = get_settings()
    oauth = OAuth()

    if settings.google_oauth_client_id and settings.google_oauth_client_secret:
        oauth.register(
            name="google",
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            server_metadata_url=_GOOGLE_METADATA,
            client_kwargs={"scope": "openid email profile"},
        )

    if settings.github_oauth_client_id and settings.github_oauth_client_secret:
        oauth.register(
            name="github",
            client_id=settings.github_oauth_client_id,
            client_secret=settings.github_oauth_client_secret,
            authorize_url=_GITHUB_AUTHORIZE,
            access_token_url=_GITHUB_TOKEN,
            api_base_url=_GITHUB_API,
            client_kwargs={"scope": "read:user user:email"},
        )

    return oauth


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="login-token")


def make_token(user: dict) -> str:
    """Return a signed, URL-safe token encoding the user identity."""
    return _serializer().dumps(user)


def read_token(token: str) -> dict | None:
    """Validate a token's signature and age; return the user dict or ``None``."""
    max_age = get_settings().token_ttl_seconds
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return data if isinstance(data, dict) else None


def normalize_user(provider: str, profile: dict) -> dict:
    """Build a normalized user dict from a provider profile.

    ``user_id`` is ``"{provider}_{sub}"`` reduced to alphanumeric/underscore so
    it can be used directly as a RediSearch TAG value without escaping.
    """
    if provider == "google":
        sub = profile.get("sub") or profile.get("email") or ""
        name = profile.get("name") or profile.get("email") or "Google user"
        email = profile.get("email", "")
    else:  # github
        sub = str(profile.get("id") or profile.get("login") or "")
        name = profile.get("name") or profile.get("login") or "GitHub user"
        email = profile.get("email") or ""

    raw_id = f"{provider}_{sub}"
    user_id = _SLUG_RE.sub("_", raw_id)
    return {"user_id": user_id, "name": name, "email": email, "provider": provider}
