"""Unified Crashout feed — merge TikTok + YouTube into one envelope."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import TIKTOK_API_KEY, YOUTUBE_API_KEY
from app.integrations.tiktok_content import CURATED_RECOVERY_FEED, normalize_tiktok_video
from app.youtube_service import (
    CURATED_YOUTUBE_FEED,
    YT_VIDEOS_URL,
    _api_get,
    _resolve_key,
    fetch_youtube_feed,
)

logger = logging.getLogger("crashout.feed")


def _parse_ts(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def normalize_unified(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize mixed-platform cards into a shared Crashout feed shape."""
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        platform = str(raw.get("platform") or raw.get("source_platform") or "unknown")
        title = str(raw.get("title") or "Recovery clip")[:200]
        channel = str(raw.get("channel") or raw.get("author") or "Crashout")[:200]
        thumb = raw.get("thumbnail") or raw.get("cover_url") or raw.get("thumbnails")
        if isinstance(thumb, dict):
            thumb = thumb.get("high") or thumb.get("medium") or thumb.get("default")
        view_count = raw.get("view_count")
        try:
            view_count = int(view_count) if view_count is not None else None
        except (TypeError, ValueError):
            view_count = None
        engagement = raw.get("engagement_score")
        if engagement is None and view_count is not None:
            likes = raw.get("like_count") or 0
            try:
                engagement = float(view_count) + float(likes) * 10
            except (TypeError, ValueError):
                engagement = float(view_count)
        published_at = raw.get("published_at")
        out.append(
            {
                "id": str(raw.get("id") or f"uni_{hash(title) & 0xFFFFFFFF:x}"),
                "platform": platform,
                "title": title,
                "thumbnail": thumb,
                "channel": channel,
                "published_at": str(published_at) if published_at else None,
                "view_count": view_count,
                "engagement_score": float(engagement) if engagement is not None else None,
                "source": raw.get("source") or platform,
            }
        )
    return out


def merge_items(
    list1: list[dict[str, Any]],
    list2: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Concatenate two item lists (no dedupe — callers may sort afterward)."""
    return list(list1 or []) + list(list2 or [])


def sort_items(
    items: list[dict[str, Any]],
    key: str = "published_at",
) -> list[dict[str, Any]]:
    """Sort descending by published_at, view_count, or engagement_score."""
    if key in ("view_count", "engagement_score"):

        def _score(item: dict[str, Any]) -> float:
            val = item.get(key)
            try:
                return float(val) if val is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        return sorted(items, key=_score, reverse=True)

    return sorted(items, key=lambda i: _parse_ts(i.get(key)), reverse=True)


def _youtube_to_unified(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged = []
    for item in items:
        row = dict(item)
        row["platform"] = "youtube"
        row.setdefault("source", "youtube")
        tagged.append(row)
    return normalize_unified(tagged)


def _tiktok_to_unified(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged = []
    for item in items:
        row = dict(item)
        row["platform"] = "tiktok"
        row["channel"] = row.get("author") or row.get("channel")
        row["thumbnail"] = row.get("cover_url") or row.get("thumbnail")
        row.setdefault("source", row.get("source") or "tiktok")
        tagged.append(row)
    return normalize_unified(tagged)


def _curated_youtube_trending() -> list[dict[str, Any]]:
    items = []
    for i, card in enumerate(CURATED_YOUTUBE_FEED):
        row = dict(card)
        row["platform"] = "youtube"
        row["view_count"] = 5000 * (len(CURATED_YOUTUBE_FEED) - i)
        row["engagement_score"] = float(row["view_count"])
        row["published_at"] = datetime.now(timezone.utc).isoformat()
        row["source"] = "youtube_trending_curated"
        items.append(row)
    return normalize_unified(items)


def fetch_youtube_items(*, max_results: int = 12) -> list[dict[str, Any]]:
    items = fetch_youtube_feed(max_results=max_results)
    return _youtube_to_unified(items)


def fetch_tiktok_items() -> list[dict[str, Any]]:
    """Curated TikTok recovery cards (live Research optional later)."""
    _ = TIKTOK_API_KEY  # reserved for live Research/Display wiring
    items = [
        normalize_tiktok_video(dict(x), hashtag=x.get("hashtag"))
        for x in CURATED_RECOVERY_FEED
    ]
    for i, curated in enumerate(CURATED_RECOVERY_FEED):
        if i < len(items):
            items[i]["share_url"] = curated.get("share_url")
            items[i]["source"] = "curated"
            items[i]["view_count"] = 1000 * (len(CURATED_RECOVERY_FEED) - i)
            items[i]["like_count"] = 50 * (len(CURATED_RECOVERY_FEED) - i)
            items[i]["published_at"] = None
    return _tiktok_to_unified(items)


def fetch_youtube_trending(max_results: int = 12) -> list[dict[str, Any]]:
    key = _resolve_key()
    if not key:
        return _curated_youtube_trending()

    try:
        payload = _api_get(
            YT_VIDEOS_URL,
            {
                "part": "snippet,statistics",
                "chart": "mostPopular",
                "maxResults": max(1, min(int(max_results), 50)),
                "key": key,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("YouTube trending unavailable: %s", exc)
        return _curated_youtube_trending()

    items_raw = payload.get("items") if isinstance(payload, dict) else None
    if not items_raw:
        return _curated_youtube_trending()

    out: list[dict[str, Any]] = []
    for raw in items_raw:
        if not isinstance(raw, dict):
            continue
        snippet = raw.get("snippet") or {}
        stats = raw.get("statistics") or {}
        try:
            views = int(stats.get("viewCount") or 0)
        except (TypeError, ValueError):
            views = 0
        try:
            likes = int(stats.get("likeCount") or 0)
        except (TypeError, ValueError):
            likes = 0
        thumbs = snippet.get("thumbnails") or {}
        high = (thumbs.get("high") or thumbs.get("medium") or {}).get("url")
        out.append(
            {
                "id": raw.get("id"),
                "platform": "youtube",
                "title": snippet.get("title"),
                "thumbnail": high,
                "channel": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "view_count": views,
                "engagement_score": float(views + likes * 10),
                "source": "youtube_trending",
            }
        )
    return normalize_unified(out)


def fetch_tiktok_trending() -> list[dict[str, Any]]:
    """TikTok trending placeholder — curated cards with engagement scores."""
    items = fetch_tiktok_items()
    for i, item in enumerate(items):
        base = item.get("view_count") or (2000 * (len(items) - i))
        item["view_count"] = base
        item["engagement_score"] = float(base) + float(item.get("like_count") or 0) * 10
        item["source"] = "tiktok_trending"
    return items


def build_unified_all_response(
    *,
    max_results: int = 12,
    with_ads: bool = False,
    ads_every_n: int | None = None,
    ranked: bool = False,
    personalized_user_id: int | str | None = None,
    recommended_user_id: int | str | None = None,
) -> dict[str, Any]:
    if recommended_user_id is not None and str(recommended_user_id).strip() != "":
        from app.recommendation_service import recommend_all

        payload = recommend_all(recommended_user_id, max_results=max_results)
        # Feed route uses lane="recommended" when ?recommended= is set
        payload = dict(payload)
        payload["lane"] = "recommended"
        payload["title"] = "Recommended Feed"
        meta = dict(payload.get("meta") or {})
        meta["recommended"] = True
        payload["meta"] = meta
        return payload

    yt = fetch_youtube_items(max_results=max_results)
    tt = fetch_tiktok_items()
    merged = sort_items(merge_items(yt, tt), key="published_at")
    meta: dict[str, Any] = {
        "sources": ["youtube", "tiktok"],
        "total_items": len(merged),
        "api_configured": {
            "youtube": bool(YOUTUBE_API_KEY),
            "tiktok": bool(TIKTOK_API_KEY),
        },
        "ads_injected": False,
        "ranked": False,
        "personalized": False,
        "recommended": False,
    }
    if with_ads:
        from app.config import ADS_INJECT_EVERY_N
        from app.monetization_service import get_ads

        ads_payload = get_ads()
        ads = list(ads_payload.get("items") or [])
        n = ads_every_n if ads_every_n is not None else ADS_INJECT_EVERY_N
        merged = merge_items_with_ads(merged, ads, every_n=n)
        meta["ads_injected"] = True
        meta["ads_every_n"] = max(1, int(n or 3))
        meta["total_items"] = len(merged)

    lane = "all"
    title = "Unified Recovery Feed"
    if personalized_user_id is not None and str(personalized_user_id).strip() != "":
        from app.ranking_service import personalize_feed

        merged = personalize_feed(personalized_user_id, merged)
        meta["ranked"] = True
        meta["personalized"] = True
        meta["user_id"] = (
            int(personalized_user_id)
            if str(personalized_user_id).isdigit()
            else personalized_user_id
        )
        lane = "personalized"
        title = "Personalized Recovery Feed"
    elif ranked:
        from app.ranking_service import score_feed

        merged = score_feed(merged)
        meta["ranked"] = True
        lane = "ranked"
        title = "Ranked Recovery Feed"

    meta["total_items"] = len(merged)
    return {
        "ok": True,
        "platform": "unified",
        "lane": lane,
        "title": title,
        "items": merged,
        "count": len(merged),
        "meta": meta,
    }


def merge_items_with_ads(
    items: list[dict[str, Any]],
    ads: list[dict[str, Any]],
    *,
    every_n: int = 3,
) -> list[dict[str, Any]]:
    """Insert ad cards every N content items."""
    if not ads:
        return list(items or [])
    n = max(1, int(every_n or 3))
    out: list[dict[str, Any]] = []
    ad_i = 0
    for idx, item in enumerate(items or [], start=1):
        out.append(item)
        if idx % n == 0:
            ad = dict(ads[ad_i % len(ads)])
            out.append(
                {
                    "id": f"ad_{ad.get('id')}",
                    "platform": "ad",
                    "title": ad.get("title") or "Sponsored",
                    "thumbnail": ad.get("image"),
                    "channel": "Sponsored",
                    "published_at": None,
                    "view_count": None,
                    "engagement_score": None,
                    "source": "ad_inventory",
                    "cta": ad.get("cta"),
                    "payout_per_click": ad.get("payout_per_click"),
                    "ad_id": ad.get("id"),
                }
            )
            ad_i += 1
    return out


def build_trending_response(*, max_results: int = 12) -> dict[str, Any]:
    yt = fetch_youtube_trending(max_results=max_results)
    tt = fetch_tiktok_trending()
    merged = sort_items(merge_items(yt, tt), key="engagement_score")
    return {
        "ok": True,
        "platform": "unified",
        "lane": "trending",
        "title": "Trending Recovery Feed",
        "items": merged,
        "count": len(merged),
        "meta": {
            "sources": ["youtube", "tiktok"],
            "total_items": len(merged),
            "sort": "engagement_score",
        },
    }


CURATED_CREATOR_FEED: list[dict[str, Any]] = [
    {
        "id": "creator_placeholder_1",
        "platform": "youtube",
        "title": "Creator draft — one safe move",
        "thumbnail": None,
        "channel": "Creator",
        "published_at": None,
        "view_count": 0,
        "engagement_score": 0,
        "source": "creator_placeholder",
    },
    {
        "id": "creator_placeholder_2",
        "platform": "tiktok",
        "title": "Creator draft — pause before post",
        "thumbnail": None,
        "channel": "Creator",
        "published_at": None,
        "view_count": 0,
        "engagement_score": 0,
        "source": "creator_placeholder",
    },
]


def build_creator_feed_response(creator_id: str) -> dict[str, Any]:
    """Placeholder creator lane — OAuth-linked channels come later."""
    items = normalize_unified(
        [{**row, "channel": f"Creator {creator_id}"} for row in CURATED_CREATOR_FEED]
    )
    return {
        "ok": True,
        "platform": "unified",
        "lane": "creator",
        "title": f"Creator Feed ({creator_id})",
        "items": items,
        "count": len(items),
        "meta": {
            "creator_id": str(creator_id),
            "mode": "placeholder",
            "sources": ["youtube", "tiktok"],
            "total_items": len(items),
        },
    }
