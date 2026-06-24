"""Tests for optional OAuth login and per-request user resolution.

Authlib is never called for real: the OAuth client is replaced with a fake so
the login/callback routes are exercised without network or credentials.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.responses import RedirectResponse

from app import config
from app.dependencies import get_current_user
from app.services import auth as auth_service


# --- Token signing -------------------------------------------------------
def test_make_and_read_token_roundtrip():
    user = {"user_id": "google_42", "name": "Ana", "email": "a@x.com"}
    token = auth_service.make_token(user)
    assert auth_service.read_token(token) == user


def test_read_token_rejects_tampered():
    token = auth_service.make_token({"user_id": "u"})
    assert auth_service.read_token(token + "x") is None


def test_read_token_rejects_expired(monkeypatch):
    token = auth_service.make_token({"user_id": "u"})
    monkeypatch.setenv("TOKEN_TTL_SECONDS", "-1")
    config.get_settings.cache_clear()
    assert auth_service.read_token(token) is None


def test_read_token_rejects_non_dict_payload():
    # A validly-signed but non-dict payload is rejected.
    signed = auth_service._serializer().dumps([1, 2, 3])
    assert auth_service.read_token(signed) is None


# --- Profile normalization ----------------------------------------------
def test_normalize_user_google():
    user = auth_service.normalize_user(
        "google", {"sub": "123", "name": "Ana", "email": "a@x.com"}
    )
    assert user == {
        "user_id": "google_123",
        "name": "Ana",
        "email": "a@x.com",
        "provider": "google",
    }


def test_normalize_user_github_and_sanitizes_id():
    user = auth_service.normalize_user(
        "github", {"id": 99, "login": "octocat", "email": None, "name": None}
    )
    assert user["user_id"] == "github_99"
    assert user["name"] == "octocat"  # falls back to login
    assert user["provider"] == "github"


def test_normalize_user_sanitizes_special_chars():
    user = auth_service.normalize_user("google", {"sub": "a.b@c", "email": "e"})
    assert user["user_id"] == "google_a_b_c"  # only alnum/underscore


# --- OAuth registry ------------------------------------------------------
def test_get_oauth_registers_configured_providers(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "gid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "gsecret")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "hid")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "hsecret")
    config.get_settings.cache_clear()
    auth_service.get_oauth.cache_clear()

    oauth = auth_service.get_oauth()
    assert oauth.create_client("google") is not None
    assert oauth.create_client("github") is not None
    auth_service.get_oauth.cache_clear()


# --- get_current_user dependency ----------------------------------------
def test_get_current_user_public_when_auth_off():
    user = get_current_user(authorization=None)
    assert user["user_id"] == config.PUBLIC_USER_ID


def test_get_current_user_requires_token_when_auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    config.get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None)
    assert exc.value.status_code == 401


def test_get_current_user_rejects_bad_token(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    config.get_settings.cache_clear()
    with pytest.raises(HTTPException):
        get_current_user(authorization="Bearer nope")
    with pytest.raises(HTTPException):
        get_current_user(authorization="Basic abc")  # non-bearer scheme


def test_get_current_user_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    config.get_settings.cache_clear()
    token = auth_service.make_token({"user_id": "google_7", "name": "Z"})
    user = get_current_user(authorization=f"Bearer {token}")
    assert user["user_id"] == "google_7"


# --- OAuth routes (Authlib faked) ---------------------------------------
class _FakeResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeOAuthClient:
    def __init__(self, token=None, user=None, emails=None):
        self._token = token
        self._user = user
        self._emails = emails

    async def authorize_redirect(self, request, redirect_uri):
        return RedirectResponse(url=f"https://provider/authorize?redirect_uri={redirect_uri}")

    async def authorize_access_token(self, request):
        return self._token

    async def userinfo(self, token=None):
        return self._token["userinfo"]

    async def get(self, path, token=None):
        return _FakeResp(self._user if path == "user" else self._emails)


class _FakeOAuth:
    def __init__(self, client):
        self._client = client

    def create_client(self, name):
        return self._client


def _patch_oauth(monkeypatch, client):
    from app.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "get_oauth", lambda: _FakeOAuth(client))


def test_login_redirects_to_provider(client, monkeypatch):
    _patch_oauth(monkeypatch, _FakeOAuthClient())
    resp = client.get("/auth/login/google", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "auth/callback/google" in resp.headers["location"]


def test_login_uses_configured_backend_url(client, monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "https://api.example.com/")
    config.get_settings.cache_clear()
    _patch_oauth(monkeypatch, _FakeOAuthClient())
    resp = client.get("/auth/login/google", follow_redirects=False)
    assert "https://api.example.com/auth/callback/google" in resp.headers["location"]


def test_login_rejects_unknown_provider(client):
    resp = client.get("/auth/login/twitter", follow_redirects=False)
    assert resp.status_code == 400


def test_login_503_when_provider_not_configured(client, monkeypatch):
    _patch_oauth(monkeypatch, None)
    resp = client.get("/auth/login/google", follow_redirects=False)
    assert resp.status_code == 503


def test_callback_google_issues_token(client, monkeypatch):
    token = {"userinfo": {"sub": "55", "name": "Ana", "email": "a@x.com"}}
    _patch_oauth(monkeypatch, _FakeOAuthClient(token=token))
    resp = client.get("/auth/callback/google", follow_redirects=False)
    assert resp.status_code in (302, 307)
    location = resp.headers["location"]
    assert location.startswith("/#token=")
    issued = location.split("#token=", 1)[1]
    assert auth_service.read_token(issued)["user_id"] == "google_55"


def test_callback_github_fetches_email_when_missing(client, monkeypatch):
    fake = _FakeOAuthClient(
        token={"access_token": "t"},
        user={"id": 9, "login": "octo", "name": "Octo", "email": None},
        emails=[{"email": "octo@x.com", "primary": True}],
    )
    _patch_oauth(monkeypatch, fake)
    resp = client.get("/auth/callback/github", follow_redirects=False)
    location = resp.headers["location"]
    issued = location.split("#token=", 1)[1]
    user = auth_service.read_token(issued)
    assert user["user_id"] == "github_9"
    assert user["email"] == "octo@x.com"


def test_callback_rejects_unknown_provider(client):
    resp = client.get("/auth/callback/twitter", follow_redirects=False)
    assert resp.status_code == 400


def test_callback_503_when_provider_not_configured(client, monkeypatch):
    _patch_oauth(monkeypatch, None)
    resp = client.get("/auth/callback/google", follow_redirects=False)
    assert resp.status_code == 503


def test_me_returns_public_when_auth_off(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == config.PUBLIC_USER_ID


def test_logout_clears_session(client):
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


# --- End-to-end auth gate + isolation -----------------------------------
def test_protected_endpoint_401_without_token(auth_client):
    test_client, _headers, _user = auth_client
    resp = test_client.get("/documents")
    assert resp.status_code == 401


def test_me_with_valid_token(auth_client):
    test_client, headers, user = auth_client
    resp = test_client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user["user_id"]


def test_documents_are_isolated_per_user(auth_client, fake_embeddings):
    from app.services import ingestion

    test_client, headers, user = auth_client

    # Ingest a document owned by another user directly.
    ingestion.ingest_file("outro.txt", b"conteudo de outro usuario", user_id="other")
    # The logged-in user ingests their own.
    ingestion.ingest_file("meu.txt", b"meu conteudo", user_id=user["user_id"])

    resp = test_client.get("/documents", headers=headers)
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()]
    assert names == ["meu.txt"]  # other user's document is not visible
