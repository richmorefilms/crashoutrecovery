"""TikTok Content Posting (Upload) API helpers."""
from __future__ import annotations

import logging
from typing import Any

from app.services.tiktok_service import TikTokAPIError, TikTokService
from app.social_auth import (
    PROVIDER_TIKTOK,
    get_social_auth,
    update_tokens,
)

logger = logging.getLogger("crashout.tiktok.upload")

# TikTok direct-post privacy options
PRIVACY_OPTIONS = frozenset(
    {
        "PUBLIC_TO_EVERYONE",
        "MUTUAL_FOLLOW_FRIENDS",
        "FOLLOWER_OF_CREATOR",
        "SELF_ONLY",
    }
)


def service_for_user(user_id: int) -> TikTokService:
    row = get_social_auth(user_id, PROVIDER_TIKTOK)
    if not row or not row.get("access_token"):
        raise TikTokAPIError(
            "TikTok not connected. Sign in with TikTok first.",
            status_code=401,
        )
    return TikTokService(
        access_token=row.get("access_token") or "",
        refresh_token=row.get("refresh_token") or "",
        token_expires_at=(
            float(row["expires_at"])
            if row.get("expires_at") is not None
            else row.get("token_expires_at")
        ),
    )


async def publish_video_bytes(
    user_id: int,
    *,
    content: bytes,
    filename: str,
    content_type: str,
    title: str,
    privacy_level: str = "SELF_ONLY",
    disable_comment: bool = False,
    disable_duet: bool = False,
    disable_stitch: bool = False,
) -> dict[str, Any]:
    """
    Init → PUT bytes → return publish_id / status.

    Uses FILE_UPLOAD source. Caller must have video.upload + video.publish scopes.
    """
    if not content:
        raise TikTokAPIError("Empty video file", status_code=400)
    privacy = privacy_level if privacy_level in PRIVACY_OPTIONS else "SELF_ONLY"
    title_clean = (title or "Crashout Recovery").strip()[:150]

    service = service_for_user(user_id)
    try:
        if service.token_needs_refresh():
            try:
                await service.refresh_access_token()
                snap = service.token_snapshot()
                update_tokens(
                    user_id,
                    PROVIDER_TIKTOK,
                    access_token=snap["access_token"],
                    refresh_token=snap.get("refresh_token"),
                    expires_at=snap.get("token_expires_at"),
                )
            except TikTokAPIError:
                logger.warning("TikTok refresh failed before upload for user %s", user_id)

        post_info = {
            "title": title_clean,
            "privacy_level": privacy,
            "disable_comment": disable_comment,
            "disable_duet": disable_duet,
            "disable_stitch": disable_stitch,
        }
        source_info = {
            "source": "FILE_UPLOAD",
            "video_size": len(content),
            "chunk_size": len(content),
            "total_chunk_count": 1,
        }
        init_payload = await service.init_video_upload(
            post_info=post_info,
            source_info=source_info,
        )
        data = init_payload.get("data") or {}
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")
        if not upload_url or not publish_id:
            raise TikTokAPIError(
                "TikTok init did not return upload_url/publish_id",
                payload=init_payload,
            )

        ctype = content_type or "video/mp4"
        await service.upload_video_bytes(str(upload_url), content, ctype)

        status_payload: dict[str, Any] = {}
        try:
            status_payload = await service.fetch_publish_status(str(publish_id))
        except TikTokAPIError as exc:
            logger.info("Publish status fetch deferred: %s", exc)
            status_payload = {"error": str(exc)}

        status_data = status_payload.get("data") or status_payload
        video_id: Any = status_data.get("video_id")
        posts = status_data.get("publicaly_available_post_id") or status_data.get(
            "publicly_available_post_id"
        )
        if isinstance(posts, list) and posts:
            video_id = posts[0]
        elif isinstance(posts, (str, int)):
            video_id = posts

        return {
            "ok": True,
            "platform": "tiktok",
            "publish_id": publish_id,
            "video_id": video_id,
            "status": status_data.get("status") or "PROCESSING_UPLOAD",
            "filename": filename,
            "bytes": len(content),
            "privacy_level": privacy,
            "title": title_clean,
            "raw_status": status_data if isinstance(status_data, dict) else {},
        }
    finally:
        # Persist refreshed tokens if any
        snap = service.token_snapshot()
        if snap.get("access_token"):
            update_tokens(
                user_id,
                PROVIDER_TIKTOK,
                access_token=snap["access_token"],
                refresh_token=snap.get("refresh_token"),
                expires_at=snap.get("token_expires_at"),
            )
        await service.aclose()
