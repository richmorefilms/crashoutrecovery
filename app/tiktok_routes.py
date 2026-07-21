"""TikTok Content, Auth, Share, and Upload API routes."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.auth_deps import get_current_user, load_user
from app.auth_security import issue_session
from app.config import (
    TIKTOK_ACCESS_TOKEN,
    TIKTOK_CLIENT_KEY,
    TIKTOK_MOBILE_REDIRECT_URI,
    TIKTOK_REDIRECT_URI,
    TIKTOK_REFRESH_TOKEN,
)
from app.db import get_conn, row_to_dict, utc_now_iso
from app.integrations import tiktok_auth as tt_auth
from app.integrations import tiktok_content as tt_content
from app.integrations import tiktok_share as tt_share
from app.integrations import tiktok_upload as tt_upload
from app.services.tiktok_service import TikTokAPIError
from app.social_auth import PROVIDER_TIKTOK, get_social_auth, list_social_auth_public

logger = logging.getLogger("crashout.tiktok.routes")

router = APIRouter(tags=["tiktok"])


class ShareRequest(BaseModel):
    video_url: str | None = Field(default=None, max_length=2000)
    caption: str | None = Field(default=None, max_length=2200)
    hashtags: list[str] | str | None = None
    title: str | None = Field(default=None, max_length=200)


def _http_error(exc: TikTokAPIError) -> HTTPException:
    code = exc.status_code or status.HTTP_502_BAD_GATEWAY
    if code < 400:
        code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(
        status_code=code,
        detail={"error": "tiktok_api_error", "message": str(exc), "payload": exc.payload},
    )


# ---------------------------------------------------------------------------
# A) Content feed
# ---------------------------------------------------------------------------


@router.get("/api/tiktok/feed")
async def tiktok_feed(
    request: Request,
    hashtag: str | None = Query(default=None, description="Comma-separated hashtags"),
    tags: str | None = Query(default=None, description="Alias for hashtag"),
):
    """JSON feed for web tab + mobile clients."""
    raw = hashtag or tags or ""
    hashtags = [h.strip() for h in raw.replace("#", "").split(",") if h.strip()] or None

    access = TIKTOK_ACCESS_TOKEN
    refresh = TIKTOK_REFRESH_TOKEN
    expires_at = None
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("id"):
        linked = get_social_auth(int(user["id"]), PROVIDER_TIKTOK)
        if linked and linked.get("access_token"):
            access = linked["access_token"]
            refresh = linked.get("refresh_token") or refresh
            expires_at = linked.get("expires_at") or linked.get("token_expires_at")

    try:
        payload = await tt_content.build_feed_response(
            hashtags=hashtags,
            access_token=access or None,
            refresh_token=refresh or None,
            token_expires_at=float(expires_at) if expires_at is not None else None,
        )
    except TikTokAPIError as exc:
        raise _http_error(exc) from exc
    return JSONResponse(payload)


# ---------------------------------------------------------------------------
# B) Login Kit OAuth
# ---------------------------------------------------------------------------


@router.get("/auth/tiktok/login")
async def tiktok_login(
    request: Request,
    mobile: bool = Query(default=False),
    redirect_uri: str | None = Query(default=None),
):
    """Start TikTok OAuth. Prefer linking to an existing Crashout session."""
    if not tt_auth.oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "tiktok_not_configured",
                "message": "Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in .env",
            },
        )

    user = getattr(request.state, "user", None)
    user_id = int(user["id"]) if isinstance(user, dict) and user.get("id") else None

    try:
        uri = tt_auth.resolve_redirect_uri(mobile=mobile, override=redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = tt_auth.make_oauth_state(user_id=user_id, mobile=mobile)
    try:
        url = tt_auth.build_authorize_url(state=state, redirect_uri=uri)
    except TikTokAPIError as exc:
        raise _http_error(exc) from exc

    # Mobile / XHR clients get JSON; browsers get redirect
    accept = (request.headers.get("accept") or "").lower()
    wants_json = "application/json" in accept or request.query_params.get("format") == "json"
    if wants_json:
        return {
            "ok": True,
            "authorize_url": url,
            "state": state,
            "redirect_uri": uri,
            "mobile": mobile,
            "client_key_configured": bool(TIKTOK_CLIENT_KEY),
        }
    return RedirectResponse(url, status_code=302)


@router.get("/auth/tiktok/callback")
async def tiktok_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    """OAuth callback — stores tokens on UserSocialAuth; supports mobile deep links."""
    if error:
        detail = error_description or error
        return _callback_response(
            request,
            ok=False,
            message=detail,
            mobile=False,
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    try:
        parsed = tt_auth.parse_oauth_state(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mobile = bool(parsed.get("mobile"))
    user_id = parsed.get("user_id") or 0

    # Prefer live session user if present
    session_user = getattr(request.state, "user", None)
    if isinstance(session_user, dict) and session_user.get("id"):
        user_id = int(session_user["id"])

    created_session: dict[str, Any] | None = None
    if not user_id:
        # Guest OAuth: create a lightweight account from TikTok open_id after exchange
        user_id, created_session = await _provision_user_from_tiktok(
            code=code,
            redirect_uri=TIKTOK_MOBILE_REDIRECT_URI if mobile else TIKTOK_REDIRECT_URI,
            mobile=mobile,
        )
        result = {
            "ok": True,
            "provider": PROVIDER_TIKTOK,
            "user_id": user_id,
            "provisioned": True,
            "profile": created_session.get("profile") if created_session else {},
        }
    else:
        uri = TIKTOK_MOBILE_REDIRECT_URI if mobile else TIKTOK_REDIRECT_URI
        try:
            result = await tt_auth.exchange_and_store(
                code=code,
                redirect_uri=uri,
                user_id=int(user_id),
            )
        except TikTokAPIError as exc:
            return _callback_response(
                request,
                ok=False,
                message=str(exc),
                mobile=mobile,
            )

    tokens = None
    if created_session and created_session.get("session"):
        tokens = created_session["session"]

    return _callback_response(
        request,
        ok=True,
        message="TikTok connected",
        mobile=mobile,
        extra={
            "profile": result.get("profile"),
            "user_id": result.get("user_id"),
            "session": tokens,
        },
    )


async def _provision_user_from_tiktok(
    *,
    code: str,
    redirect_uri: str,
    mobile: bool,
) -> tuple[int, dict[str, Any]]:
    """Create Crashout user when TikTok login starts without an existing session."""
    from app.services.tiktok_service import TikTokService
    from app.social_auth import expires_at_from_expires_in, upsert_social_auth

    service = TikTokService()
    try:
        token_payload = await service.exchange_code(code, redirect_uri=redirect_uri)
        profile: dict[str, Any] = {}
        try:
            profile = await service.get_user_info()
        except TikTokAPIError:
            profile = {}
        open_id = str(profile.get("open_id") or token_payload.get("open_id") or "")
        if not open_id:
            raise TikTokAPIError("TikTok did not return open_id")

        # Reuse existing social link if present
        with get_conn() as conn:
            existing = conn.execute(
                """
                SELECT user_id FROM user_social_auth
                WHERE provider = ? AND tiktok_user_id = ?
                """,
                (PROVIDER_TIKTOK, open_id),
            ).fetchone()
            if existing:
                user_id = int(existing["user_id"])
                user = load_user(user_id) or {}
            else:
                display = str(profile.get("display_name") or profile.get("username") or "tiktok")
                base = "".join(c for c in display.lower() if c.isalnum() or c == "_")[:20] or "tiktok"
                username = f"{base}_{open_id[-6:]}"
                email = f"tiktok_{open_id}@users.crashout.local"
                created = utc_now_iso()
                # Random unusable password hash placeholder — TikTok-only login
                from app.auth_security import hash_password
                import secrets as _secrets

                password_hash = hash_password(_secrets.token_urlsafe(32))
                cur = conn.execute(
                    """
                    INSERT INTO users (
                        username, email, password_hash, tier, role, created_at, last_login
                    ) VALUES (?, ?, ?, 'basic', 'user', ?, ?)
                    """,
                    (username, email, password_hash, created, created),
                )
                user_id = int(cur.lastrowid)
                conn.execute(
                    """
                    INSERT INTO recovery (user_id, streak_days, spike_history, tones, wins)
                    VALUES (?, 0, '[]', '[]', 0)
                    """,
                    (user_id,),
                )
                user = row_to_dict(
                    conn.execute(
                        """
                        SELECT id, username, email, tier, role, created_at, last_login
                        FROM users WHERE id = ?
                        """,
                        (user_id,),
                    ).fetchone()
                ) or {}

        upsert_social_auth(
            user_id,
            PROVIDER_TIKTOK,
            tiktok_user_id=open_id,
            username=str(profile.get("username") or profile.get("display_name") or user.get("username")),
            avatar_url=profile.get("avatar_url"),
            access_token=service.access_token or None,
            refresh_token=service.refresh_token or None,
            expires_at=expires_at_from_expires_in(token_payload.get("expires_in")),
            scopes=str(token_payload.get("scope") or ""),
            raw_profile=profile,
        )
        session = issue_session(user_id=user_id, username=user.get("username") or f"user{user_id}")
        return user_id, {
            "profile": {
                "username": profile.get("username") or profile.get("display_name") or user.get("username"),
                "display_name": profile.get("display_name"),
                "avatar_url": profile.get("avatar_url"),
                "tiktok_user_id": open_id,
            },
            "session": {
                "access_token": session["access_token"],
                "refresh_token": session["refresh_token"],
                "expires_in": session["expires_in"],
                "refresh_expires_in": session["refresh_expires_in"],
                "user": {
                    "id": user_id,
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "tier": user.get("tier") or "basic",
                    "role": user.get("role") or "user",
                },
            },
        }
    finally:
        await service.aclose()


def _callback_response(
    request: Request,
    *,
    ok: bool,
    message: str,
    mobile: bool,
    extra: dict[str, Any] | None = None,
):
    payload = {"ok": ok, "message": message, "platform": "tiktok", **(extra or {})}
    accept = (request.headers.get("accept") or "").lower()
    wants_json = (
        "application/json" in accept
        or request.query_params.get("format") == "json"
        or mobile
    )

    if mobile and ok:
        # Deep link back into Capacitor / RN app with compact query
        q = urlencode(
            {
                "ok": "1",
                "provider": "tiktok",
                "user_id": str((extra or {}).get("user_id") or ""),
            }
        )
        deep = f"{TIKTOK_MOBILE_REDIRECT_URI}?{q}" if "://" in TIKTOK_MOBILE_REDIRECT_URI else None
        if deep and request.query_params.get("format") != "json":
            # Still return JSON body for fetch-based mobile OAuth; include deep_link
            payload["deep_link"] = deep

    if wants_json:
        return JSONResponse(payload, status_code=200 if ok else 400)

    # Browser: land on profile with flash query
    dest = "/profile?" + urlencode({"tiktok": "1" if ok else "0", "msg": message[:120]})
    return RedirectResponse(dest, status_code=302)


@router.get("/api/tiktok/me")
async def tiktok_me(user: dict = Depends(get_current_user)):
    """Connected TikTok profile for the signed-in Crashout user."""
    linked = get_social_auth(int(user["id"]), PROVIDER_TIKTOK)
    socials = list_social_auth_public(int(user["id"]))
    if not linked:
        return {"ok": True, "connected": False, "tiktok": None, "social": socials}
    return {
        "ok": True,
        "connected": True,
        "tiktok": {
            "tiktok_user_id": linked.get("tiktok_user_id"),
            "username": linked.get("username"),
            "display_name": linked.get("username"),
            "avatar_url": linked.get("avatar_url"),
            "scopes": linked.get("scopes"),
            "updated_at": linked.get("updated_at"),
            "badge": "connected",
        },
        "social": socials,
    }


# ---------------------------------------------------------------------------
# C) Share Kit
# ---------------------------------------------------------------------------


@router.post("/api/tiktok/share")
async def tiktok_share(body: ShareRequest, request: Request):
    """Return share intents JSON (web + Capacitor / React Native)."""
    payload = tt_share.build_share_payload(
        video_url=body.video_url,
        caption=body.caption,
        hashtags=body.hashtags,
        title=body.title,
    )
    # Optional: attach requesting user id for analytics (no PII required)
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("id"):
        payload["user_id"] = int(user["id"])
    return JSONResponse(payload)


# ---------------------------------------------------------------------------
# D) Upload / Publish
# ---------------------------------------------------------------------------


@router.post("/api/tiktok/upload")
async def tiktok_upload(
    user: dict = Depends(get_current_user),
    video: UploadFile = File(...),
    title: str = Form(default="Crashout Recovery"),
    privacy_level: str = Form(default="SELF_ONLY"),
    disable_comment: bool = Form(default=False),
    disable_duet: bool = Form(default=False),
    disable_stitch: bool = Form(default=False),
    save_media: bool = Form(default=True),
):
    """Publish a video file to TikTok via Content Posting API.

    Optionally stages the file through the existing media upload pipeline first.
    """
    from app.media import MediaUploadError, save_video_bytes

    raw = await video.read()
    if len(raw) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video exceeds 500MB limit")

    media_url = None
    if save_media:
        try:
            media_url = save_video_bytes(
                raw,
                filename=video.filename,
                content_type=video.content_type,
            )
        except MediaUploadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = await tt_upload.publish_video_bytes(
            int(user["id"]),
            content=raw,
            filename=video.filename or "video.mp4",
            content_type=video.content_type or "video/mp4",
            title=title,
            privacy_level=privacy_level,
            disable_comment=disable_comment,
            disable_duet=disable_duet,
            disable_stitch=disable_stitch,
        )
    except TikTokAPIError as exc:
        raise _http_error(exc) from exc
    if media_url:
        result["media_url"] = media_url
    return JSONResponse(result)
