"""TikTok Login Kit — OAuth authorize + callback helpers."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

from app.config import (
    TIKTOK_CLIENT_KEY,
    TIKTOK_MOBILE_REDIRECT_URI,
    TIKTOK_REDIRECT_URI,
    TIKTOK_SCOPES,
)
from app.services.tiktok_service import TikTokAPIError, TikTokService, TIKTOK_AUTH_BASE
from app.social_auth import (
    PROVIDER_TIKTOK,
    expires_at_from_expires_in,
    upsert_social_auth,
)

logger = logging.getLogger("crashout.tiktok.auth")

AUTHORIZE_PATH = "/v2/auth/authorize/"
STATE_TTL_SECONDS = 600


def oauth_configured() -> bool:
    return bool(TIKTOK_CLIENT_KEY)


def resolve_redirect_uri(*, mobile: bool = False, override: str | None = None) -> str:
    """Pick web or mobile deep-link redirect. Override must match allowlist."""
    if override:
        allowed = {
            TIKTOK_REDIRECT_URI,
            TIKTOK_MOBILE_REDIRECT_URI,
            "http://127.0.0.1:8777/auth/tiktok/callback",
            "http://localhost:8777/auth/tiktok/callback",
        }
        if override in allowed or override.startswith("crashout://"):
            return override
        raise ValueError("redirect_uri not allowed")
    if mobile:
        return TIKTOK_MOBILE_REDIRECT_URI or TIKTOK_REDIRECT_URI
    return TIKTOK_REDIRECT_URI


def build_authorize_url(
    *,
    state: str,
    redirect_uri: str | None = None,
    scopes: str | None = None,
) -> str:
    if not TIKTOK_CLIENT_KEY:
        raise TikTokAPIError("TIKTOK_CLIENT_KEY not configured")
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "scope": scopes or TIKTOK_SCOPES,
        "response_type": "code",
        "redirect_uri": redirect_uri or TIKTOK_REDIRECT_URI,
        "state": state,
    }
    return f"{TIKTOK_AUTH_BASE}{AUTHORIZE_PATH}?{urlencode(params)}"


def make_oauth_state(*, user_id: int | None = None, mobile: bool = False) -> str:
    """Opaque state: nonce.userId.mobile.timestamp.sig (HMAC with client secret or key)."""
    nonce = secrets.token_urlsafe(16)
    uid = str(user_id or 0)
    mob = "1" if mobile else "0"
    ts = str(int(time.time()))
    body = f"{nonce}.{uid}.{mob}.{ts}"
    sig = _sign(body)
    return f"{body}.{sig}"


def parse_oauth_state(state: str) -> dict[str, Any]:
    parts = (state or "").split(".")
    if len(parts) != 5:
        raise ValueError("Invalid OAuth state")
    nonce, uid, mob, ts, sig = parts
    body = f"{nonce}.{uid}.{mob}.{ts}"
    if not hmac.compare_digest(_sign(body), sig):
        raise ValueError("Invalid OAuth state signature")
    try:
        age = time.time() - int(ts)
    except ValueError as exc:
        raise ValueError("Invalid OAuth state timestamp") from exc
    if age > STATE_TTL_SECONDS or age < -60:
        raise ValueError("OAuth state expired")
    return {
        "nonce": nonce,
        "user_id": int(uid) if uid.isdigit() else None,
        "mobile": mob == "1",
        "ts": int(ts),
    }


def _sign(body: str) -> str:
    from app.config import TIKTOK_CLIENT_SECRET

    secret = (TIKTOK_CLIENT_SECRET or TIKTOK_CLIENT_KEY or "dev").encode("utf-8")
    return hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


async def exchange_and_store(
    *,
    code: str,
    redirect_uri: str,
    user_id: int,
) -> dict[str, Any]:
    """Exchange code, fetch profile, upsert UserSocialAuth."""
    service = TikTokService()
    try:
        token_payload = await service.exchange_code(code, redirect_uri=redirect_uri)
        profile: dict[str, Any] = {}
        try:
            profile = await service.get_user_info()
        except TikTokAPIError as exc:
            logger.warning("TikTok user.info failed after login: %s", exc)

        open_id = str(
            profile.get("open_id")
            or token_payload.get("open_id")
            or ""
        )
        display_name = (
            profile.get("display_name")
            or profile.get("username")
            or open_id
            or "TikTok user"
        )
        avatar = profile.get("avatar_url") or profile.get("avatar_url_100")
        expires_at = expires_at_from_expires_in(token_payload.get("expires_in"))
        row = upsert_social_auth(
            user_id,
            PROVIDER_TIKTOK,
            tiktok_user_id=open_id or None,
            username=str(profile.get("username") or display_name),
            avatar_url=str(avatar) if avatar else None,
            access_token=service.access_token or None,
            refresh_token=service.refresh_token or None,
            expires_at=expires_at,
            scopes=str(token_payload.get("scope") or TIKTOK_SCOPES),
            raw_profile=profile or token_payload,
        )
        return {
            "ok": True,
            "provider": PROVIDER_TIKTOK,
            "user_id": user_id,
            "profile": {
                "tiktok_user_id": row.get("tiktok_user_id"),
                "username": row.get("username"),
                "display_name": row.get("username"),
                "avatar_url": row.get("avatar_url"),
            },
            "scopes": row.get("scopes"),
        }
    finally:
        await service.aclose()
