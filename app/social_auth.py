"""Persist UserSocialAuth rows (TikTok OAuth tokens + profile)."""
from __future__ import annotations

import json
import time
from typing import Any

from app.db import get_conn, row_to_dict, utc_now_iso

PROVIDER_TIKTOK = "tiktok"


def upsert_social_auth(
    user_id: int,
    provider: str,
    *,
    tiktok_user_id: str | None = None,
    provider_user_id: str | None = None,  # alias
    username: str | None = None,
    display_name: str | None = None,  # alias → username
    avatar_url: str | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
    expires_at: float | int | None = None,
    token_expires_at: float | int | None = None,  # alias
    scopes: str | None = None,
    raw_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    raw_json = json.dumps(raw_profile) if raw_profile is not None else None
    open_id = tiktok_user_id if tiktok_user_id is not None else provider_user_id
    uname = username if username is not None else display_name
    exp = expires_at if expires_at is not None else token_expires_at
    if exp is not None:
        try:
            exp = int(exp)
        except (TypeError, ValueError):
            exp = None

    with get_conn() as conn:
        existing = conn.execute(
            """
            SELECT id FROM user_social_auth
            WHERE user_id = ? AND provider = ?
            """,
            (user_id, provider),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE user_social_auth SET
                    tiktok_user_id = COALESCE(?, tiktok_user_id),
                    username = COALESCE(?, username),
                    avatar_url = COALESCE(?, avatar_url),
                    access_token = COALESCE(?, access_token),
                    refresh_token = COALESCE(?, refresh_token),
                    expires_at = COALESCE(?, expires_at),
                    scopes = COALESCE(?, scopes),
                    raw_profile_json = COALESCE(?, raw_profile_json),
                    updated_at = ?
                WHERE user_id = ? AND provider = ?
                """,
                (
                    open_id,
                    uname,
                    avatar_url,
                    access_token,
                    refresh_token,
                    exp,
                    scopes,
                    raw_json,
                    now,
                    user_id,
                    provider,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO user_social_auth (
                    user_id, provider, access_token, refresh_token, expires_at,
                    tiktok_user_id, username, avatar_url, scopes,
                    raw_profile_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    provider,
                    access_token,
                    refresh_token,
                    exp,
                    open_id,
                    uname,
                    avatar_url,
                    scopes,
                    raw_json,
                    now,
                    now,
                ),
            )
        row = conn.execute(
            """
            SELECT * FROM user_social_auth
            WHERE user_id = ? AND provider = ?
            """,
            (user_id, provider),
        ).fetchone()
    return _normalize_row(row_to_dict(row) or {})


def get_social_auth(user_id: int, provider: str = PROVIDER_TIKTOK) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM user_social_auth
            WHERE user_id = ? AND provider = ?
            """,
            (user_id, provider),
        ).fetchone()
    data = row_to_dict(row)
    return _normalize_row(data) if data else None


def list_social_auth_public(user_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT provider, tiktok_user_id, username, avatar_url,
                   scopes, created_at, updated_at,
                   CASE WHEN access_token IS NOT NULL AND access_token != '' THEN 1 ELSE 0 END AS connected
            FROM user_social_auth
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        d = _normalize_row(row_to_dict(row) or {})
        d["connected"] = bool(d.get("connected"))
        out.append(d)
    return out


def update_tokens(
    user_id: int,
    provider: str,
    *,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: float | int | None = None,
    token_expires_at: float | int | None = None,
) -> None:
    upsert_social_auth(
        user_id,
        provider,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at if expires_at is not None else token_expires_at,
    )


def expires_at_from_expires_in(expires_in: Any) -> int | None:
    try:
        return int(time.time() + float(expires_in))
    except (TypeError, ValueError):
        return None


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Expose both spec column names and legacy aliases used by services."""
    if not row:
        return row
    # Spec names
    if row.get("tiktok_user_id") is None and row.get("provider_user_id"):
        row["tiktok_user_id"] = row["provider_user_id"]
    if row.get("username") is None and row.get("display_name"):
        row["username"] = row["display_name"]
    if row.get("expires_at") is None and row.get("token_expires_at") is not None:
        try:
            row["expires_at"] = int(row["token_expires_at"])
        except (TypeError, ValueError):
            pass
    # Legacy aliases for callers that still use old keys
    row.setdefault("provider_user_id", row.get("tiktok_user_id"))
    row.setdefault("display_name", row.get("username"))
    row.setdefault("token_expires_at", row.get("expires_at"))
    return row
