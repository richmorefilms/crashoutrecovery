"""Google / YouTube OAuth foundation — login URL, code exchange, token store."""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

from app.config import (
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPES,
)
from app.db import get_conn, row_to_dict, utc_now_iso

logger = logging.getLogger("crashout.oauth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class OAuthError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def oauth_configured() -> bool:
    return bool(OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET and OAUTH_REDIRECT_URI)


def build_google_oauth_url(*, state: str | None = None) -> str:
    """Build Google OAuth consent URL for YouTube scopes."""
    if not OAUTH_CLIENT_ID or not OAUTH_REDIRECT_URI:
        raise OAuthError(
            "OAuth not configured. Set OAUTH_CLIENT_ID and OAUTH_REDIRECT_URI.",
            status_code=503,
        )
    params: dict[str, str] = {
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange an authorization code for access + refresh tokens."""
    if not oauth_configured():
        raise OAuthError(
            "OAuth not configured. Set OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET.",
            status_code=503,
        )
    if not (code or "").strip():
        raise OAuthError("code is required", status_code=400)

    try:
        resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code.strip(),
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        raise OAuthError(f"Token exchange unreachable: {exc}", status_code=502) from exc

    try:
        payload = resp.json()
    except ValueError as exc:
        raise OAuthError("Token endpoint returned non-JSON", status_code=502) from exc

    if resp.status_code >= 400 or payload.get("error"):
        message = payload.get("error_description") or payload.get("error") or resp.text[:400]
        raise OAuthError(
            f"Token exchange failed: {message}",
            status_code=resp.status_code if resp.status_code >= 400 else 502,
            payload=payload if isinstance(payload, dict) else {},
        )

    return {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token"),
        "expires_in": payload.get("expires_in"),
        "token_type": payload.get("token_type"),
        "scope": payload.get("scope"),
    }


def store_tokens(user_id: int, tokens: dict[str, Any]) -> dict[str, Any]:
    """Upsert youtube_tokens row for user_id (SQLite migration ladder)."""
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not access:
        raise OAuthError("access_token missing from token payload", status_code=502)

    expires_in = tokens.get("expires_in")
    expires_at = None
    if expires_in is not None:
        try:
            expires_at = int(time.time()) + int(expires_in)
        except (TypeError, ValueError):
            expires_at = None

    now = utc_now_iso()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM youtube_tokens WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE youtube_tokens SET
                    access_token = ?,
                    refresh_token = COALESCE(?, refresh_token),
                    expires_at = COALESCE(?, expires_at),
                    updated_at = ?
                WHERE user_id = ?
                """,
                (access, refresh, expires_at, now, user_id),
            )
            row_id = int(existing["id"])
        else:
            cur = conn.execute(
                """
                INSERT INTO youtube_tokens (
                    user_id, access_token, refresh_token, expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, access, refresh, expires_at, now, now),
            )
            row_id = int(cur.lastrowid)

        row = conn.execute(
            "SELECT * FROM youtube_tokens WHERE id = ?",
            (row_id,),
        ).fetchone()
    return row_to_dict(row) if row else {"id": row_id, "user_id": user_id}


def get_tokens(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM youtube_tokens WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def build_oauth_linked_response(*, user_id: int) -> dict[str, Any]:
    return {
        "ok": True,
        "platform": "youtube",
        "lane": "oauth",
        "title": "YouTube OAuth",
        "items": [],
        "count": 0,
        "meta": {"linked": True, "user_id": user_id},
    }
