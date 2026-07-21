"""TikTok Content / Display helpers — normalize videos into Crashout feed format."""
from __future__ import annotations

import logging
from typing import Any

from app.services.tiktok_service import TikTokAPIError, TikTokService

logger = logging.getLogger("crashout.tiktok.content")

DEFAULT_HASHTAGS = ("recovery", "motivation", "mentalhealth")

# Curated public recovery-themed embeds used when Research/Display APIs are unavailable.
# Video IDs are placeholders for embed structure; real IDs come from TikTok when API works.
CURATED_RECOVERY_FEED: list[dict[str, Any]] = [
    {
        "id": "tt_curated_recovery_1",
        "video_id": None,
        "title": "One small recovery move",
        "description": "Pause before the post. #recovery",
        "author": "@crashoutrecovery",
        "author_avatar": None,
        "hashtag": "recovery",
        "cover_url": None,
        "share_url": "https://www.tiktok.com/tag/recovery",
        "embed_url": None,
        "source": "curated",
        "tone": "calm",
    },
    {
        "id": "tt_curated_motivation_1",
        "video_id": None,
        "title": "Momentum over meltdown",
        "description": "Draft the safer take. #motivation",
        "author": "@crashoutrecovery",
        "author_avatar": None,
        "hashtag": "motivation",
        "cover_url": None,
        "share_url": "https://www.tiktok.com/tag/motivation",
        "embed_url": None,
        "source": "curated",
        "tone": "direct",
    },
    {
        "id": "tt_curated_mentalhealth_1",
        "video_id": None,
        "title": "Check the spike, keep the account",
        "description": "Adults 18+ · #mentalhealth",
        "author": "@crashoutrecovery",
        "author_avatar": None,
        "hashtag": "mentalhealth",
        "cover_url": None,
        "share_url": "https://www.tiktok.com/tag/mentalhealth",
        "embed_url": None,
        "source": "curated",
        "tone": "strategic",
    },
]


def normalize_tiktok_video(raw: dict[str, Any], *, hashtag: str | None = None) -> dict[str, Any]:
    """Map TikTok API / research video objects into our feed card shape."""
    video_id = (
        raw.get("id")
        or raw.get("video_id")
        or raw.get("item_id")
        or (raw.get("video") or {}).get("id")
    )
    title = (
        raw.get("title")
        or raw.get("video_description")
        or raw.get("desc")
        or raw.get("description")
        or "TikTok clip"
    )
    author = (
        raw.get("username")
        or raw.get("author")
        or (raw.get("author") if isinstance(raw.get("author"), str) else None)
        or (raw.get("user") or {}).get("display_name")
        or (raw.get("user") or {}).get("username")
        or "@tiktok"
    )
    if isinstance(author, dict):
        author = author.get("display_name") or author.get("username") or "@tiktok"
    if isinstance(author, str) and not author.startswith("@"):
        author = f"@{author}"

    cover = (
        raw.get("cover_image_url")
        or raw.get("cover")
        or raw.get("thumbnail_url")
        or (raw.get("video") or {}).get("cover_image_url")
    )
    share_url = (
        raw.get("share_url")
        or raw.get("embed_link")
        or (f"https://www.tiktok.com/@/video/{video_id}" if video_id else None)
    )
    embed_url = None
    if video_id:
        embed_url = f"https://www.tiktok.com/embed/v2/{video_id}"

    return {
        "id": f"tt_{video_id}" if video_id else f"tt_{hash(title) & 0xFFFFFFFF:x}",
        "video_id": str(video_id) if video_id else None,
        "title": str(title)[:200],
        "description": str(raw.get("video_description") or raw.get("desc") or title)[:500],
        "author": author,
        "author_avatar": raw.get("avatar_url") or (raw.get("user") or {}).get("avatar_url"),
        "hashtag": (hashtag or raw.get("hashtag") or "").lstrip("#") or None,
        "cover_url": cover,
        "share_url": share_url,
        "embed_url": embed_url,
        "like_count": raw.get("like_count") or raw.get("digg_count"),
        "view_count": raw.get("view_count") or raw.get("play_count"),
        "source": raw.get("source") or "tiktok_api",
        "tone": raw.get("tone") or "calm",
        "raw": None,  # keep responses mobile-light
    }


def _extract_video_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or payload
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    for key in ("videos", "video_list", "list", "items"):
        val = data.get(key) if isinstance(data, dict) else None
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
    return []


async def fetch_hashtag_feed(
    service: TikTokService,
    hashtags: list[str] | None = None,
    *,
    max_per_tag: int = 6,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch hashtag videos via Research API; fall back to curated recovery feed."""
    tags = [h.lstrip("#") for h in (hashtags or list(DEFAULT_HASHTAGS))]
    meta: dict[str, Any] = {
        "mode": "curated",
        "hashtags": tags,
        "errors": [],
        "api_configured": service.is_configured,
        "has_token": service.has_access_token,
    }
    items: list[dict[str, Any]] = []

    if service.has_access_token:
        for tag in tags:
            try:
                payload = await service.research_hashtag_videos(tag, max_count=max_per_tag)
                for raw in _extract_video_list(payload):
                    items.append(normalize_tiktok_video(raw, hashtag=tag))
                meta["mode"] = "research"
            except TikTokAPIError as exc:
                logger.info("Research hashtag #%s unavailable: %s", tag, exc)
                meta["errors"].append({"hashtag": tag, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected TikTok feed error for #%s", tag)
                meta["errors"].append({"hashtag": tag, "error": str(exc)})

        if not items and service.has_access_token:
            try:
                payload = await service.query_videos()
                for raw in _extract_video_list(payload):
                    items.append(normalize_tiktok_video(raw))
                if items:
                    meta["mode"] = "display"
            except TikTokAPIError as exc:
                meta["errors"].append({"query": "video/query", "error": str(exc)})

    if not items:
        items = [normalize_tiktok_video(dict(x), hashtag=x.get("hashtag")) for x in CURATED_RECOVERY_FEED]
        # Preserve curated share URLs
        for i, curated in enumerate(CURATED_RECOVERY_FEED):
            if i < len(items):
                items[i]["share_url"] = curated.get("share_url")
                items[i]["source"] = "curated"
        meta["mode"] = "curated"

    return items, meta


from app.ui_copy import ui_label


async def build_feed_response(
    *,
    hashtags: list[str] | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
    token_expires_at: float | None = None,
) -> dict[str, Any]:
    service = TikTokService(
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at,
    )
    try:
        items, meta = await fetch_hashtag_feed(service, hashtags)
    finally:
        await service.aclose()

    return {
        "ok": True,
        "platform": "tiktok",
        "lane": "tiktok",
        "title": ui_label("tiktok_recovery_feed", "TikTok Recovery Feed"),
        "items": items,
        "count": len(items),
        "meta": meta,
    }
