"""YouTube OAuth foundation routes — /api/oauth/youtube/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.oauth_service import (
    OAuthError,
    build_google_oauth_url,
    build_oauth_linked_response,
    exchange_code_for_tokens,
    oauth_configured,
    store_tokens,
)

router = APIRouter(prefix="/api/oauth", tags=["oauth"])


def _oauth_http_error(exc: OAuthError) -> HTTPException:
    code = exc.status_code or 502
    if code < 400:
        code = 502
    return HTTPException(
        status_code=code,
        detail={
            "error": "oauth_error",
            "message": str(exc),
            "payload": exc.payload,
        },
    )


@router.get("/youtube/login")
async def youtube_oauth_login(
    request: Request,
    state: str | None = Query(default=None),
):
    """Redirect to Google OAuth consent screen."""
    if not oauth_configured() and not state:
        # Allow building URL when only client id + redirect are set
        pass
    user = getattr(request.state, "user", None)
    resolved_state = state
    if not resolved_state and isinstance(user, dict) and user.get("id"):
        resolved_state = str(user["id"])
    try:
        url = build_google_oauth_url(state=resolved_state)
    except OAuthError as exc:
        raise _oauth_http_error(exc) from exc
    return RedirectResponse(url=url, status_code=302)


@router.get("/youtube/callback")
async def youtube_oauth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
):
    """Exchange code for tokens and store in youtube_tokens."""
    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    user = getattr(request.state, "user", None)
    user_id = None
    if state and str(state).isdigit():
        user_id = int(state)
    elif isinstance(user, dict) and user.get("id"):
        user_id = int(user["id"])
    else:
        raise HTTPException(
            status_code=400,
            detail="user_id required via state= or authenticated session",
        )

    try:
        tokens = exchange_code_for_tokens(code)
        store_tokens(user_id, tokens)
    except OAuthError as exc:
        raise _oauth_http_error(exc) from exc

    return JSONResponse(build_oauth_linked_response(user_id=user_id))
