"""OAuth login router (Google / GitHub).

Mounted always, but only meaningful when ``AUTH_ENABLED`` is true (the OAuth
clients need configured credentials and the SessionMiddleware used by the
handshake is only installed in that case).

Flow:
    GET  /auth/login/{provider}     -> redirect to the provider's consent screen
    GET  /auth/callback/{provider}  -> exchange code, issue token, redirect to UI
    GET  /auth/me                   -> current user (validates the bearer token)
    POST /auth/logout               -> clear the handshake session cookie
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import AUTH_PROVIDERS, get_settings
from app.dependencies import get_current_user
from app.services.auth import get_oauth, make_token, normalize_user

router = APIRouter(prefix="/auth")


def _check_provider(provider: str) -> None:
    if provider not in AUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'.")


def _redirect_uri(request: Request, provider: str) -> str:
    """Build the callback URL, preferring the explicit configured backend URL."""
    base = get_settings().backend_url
    if base:
        return f"{base.rstrip('/')}/auth/callback/{provider}"
    return str(request.url_for("auth_callback", provider=provider))


@router.get("/login/{provider}")
async def auth_login(provider: str, request: Request):
    """Start the OAuth handshake by redirecting to the provider."""
    _check_provider(provider)
    client = get_oauth().create_client(provider)
    if client is None:
        raise HTTPException(status_code=503, detail=f"{provider} login not configured.")
    return await client.authorize_redirect(request, _redirect_uri(request, provider))


@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(provider: str, request: Request):
    """Finish the handshake: fetch the profile, issue a token, return to the UI."""
    _check_provider(provider)
    client = get_oauth().create_client(provider)
    if client is None:
        raise HTTPException(status_code=503, detail=f"{provider} login not configured.")

    token = await client.authorize_access_token(request)

    if provider == "google":
        profile = token.get("userinfo") or await client.userinfo(token=token)
    else:  # github
        profile = (await client.get("user", token=token)).json()
        if not profile.get("email"):
            emails = (await client.get("user/emails", token=token)).json()
            primary = next(
                (e["email"] for e in emails if e.get("primary")),
                emails[0]["email"] if emails else "",
            )
            profile["email"] = primary

    user = normalize_user(provider, dict(profile))
    login_token = make_token(user)

    frontend = get_settings().frontend_url
    return RedirectResponse(url=f"{frontend}#token={login_token}")


@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)) -> dict:
    """Return the current user (used by the UI to validate the token)."""
    return user


@router.post("/logout")
def auth_logout(request: Request) -> dict:
    """Clear the OAuth handshake session cookie (token is dropped client-side)."""
    if "session" in request.scope:
        request.session.clear()
    return {"ok": True}
