"""YouTube Data API v3 feed client — recovery-themed search + normalize."""
from __future__ import annotations

import logging
import re
from typing import Any

import requests

from app.config import YOUTUBE_API_KEY

logger = logging.getLogger("crashout.youtube")

YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YT_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YT_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
DEFAULT_QUERY = "recovery motivation mental health"
DEFAULT_MAX_RESULTS = 12

VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
CHANNEL_ID_RE = re.compile(r"^UC[a-zA-Z0-9_-]{22}$")

# Curated cards when YOUTUBE_API_KEY is missing or search fails (matches TikTok pattern).
CURATED_YOUTUBE_FEED: list[dict[str, Any]] = [
    {
        "id": "yt_curated_recovery_1",
        "title": "One small recovery move",
        "thumbnail": None,
        "channel": "Crashout Recovery",
        "published_at": None,
    },
    {
        "id": "yt_curated_motivation_1",
        "title": "Momentum over meltdown",
        "thumbnail": None,
        "channel": "Crashout Recovery",
        "published_at": None,
    },
    {
        "id": "yt_curated_mentalhealth_1",
        "title": "Check the spike, keep the account",
        "thumbnail": None,
        "channel": "Crashout Recovery",
        "published_at": None,
    },
]


class YouTubeAPIError(Exception):
    """Raised when YouTube Data API returns a non-success response."""

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


def _resolve_key(api_key: str | None = None) -> str:
    return (api_key if api_key is not None else YOUTUBE_API_KEY) or ""


def _require_key(api_key: str | None = None) -> str:
    key = _resolve_key(api_key)
    if not key:
        raise YouTubeAPIError(
            "YouTube API key not configured. Set YOUTUBE_API_KEY.",
            status_code=503,
        )
    return key


def _api_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        resp = requests.get(url, params=params, timeout=20)
    except requests.RequestException as exc:
        raise YouTubeAPIError(f"YouTube API unreachable: {exc}") from exc

    try:
        payload = resp.json()
    except ValueError as exc:
        raise YouTubeAPIError(
            "YouTube API returned non-JSON",
            status_code=resp.status_code,
        ) from exc

    if resp.status_code >= 400:
        message = (
            (payload.get("error") or {}).get("message")
            if isinstance(payload, dict)
            else None
        ) or resp.text[:400]
        raise YouTubeAPIError(
            f"YouTube API error ({resp.status_code}): {message}",
            status_code=resp.status_code,
            payload=payload if isinstance(payload, dict) else {},
        )

    if not isinstance(payload, dict):
        raise YouTubeAPIError("YouTube API returned unexpected payload")
    return payload


def _pick_thumbnail(snippet: dict[str, Any]) -> str | None:
    thumbs = snippet.get("thumbnails") or {}
    for key in ("high", "medium", "default"):
        url = (thumbs.get(key) or {}).get("url")
        if url:
            return str(url)
    return None


def _normalize_thumbnails(raw: dict[str, Any] | None) -> dict[str, str | None]:
    thumbs = raw if isinstance(raw, dict) else {}
    out: dict[str, str | None] = {}
    for key in ("default", "medium", "high", "standard", "maxres"):
        url = (thumbs.get(key) or {}).get("url") if isinstance(thumbs.get(key), dict) else None
        if url:
            out[key] = str(url)
    return out


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_youtube_video(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a YouTube search item into the Crashout feed card shape."""
    snippet = raw.get("snippet") if isinstance(raw.get("snippet"), dict) else {}
    video_id = (raw.get("id") or {})
    if isinstance(video_id, dict):
        video_id = video_id.get("videoId") or video_id.get("id")
    video_id = video_id or raw.get("video_id") or raw.get("id")
    title = snippet.get("title") or raw.get("title") or "YouTube video"
    channel = (
        snippet.get("channelTitle")
        or raw.get("channel")
        or raw.get("channelTitle")
        or "YouTube"
    )
    published = snippet.get("publishedAt") or raw.get("published_at")
    thumbnail = _pick_thumbnail(snippet) if snippet else raw.get("thumbnail")
    if not thumbnail and video_id and isinstance(video_id, str) and len(video_id) == 11:
        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    return {
        "id": str(video_id) if video_id else f"yt_{hash(title) & 0xFFFFFFFF:x}",
        "title": str(title)[:200],
        "thumbnail": thumbnail,
        "channel": str(channel)[:200],
        "published_at": str(published) if published else None,
    }


def normalize_video_details(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a videos.list item into detail shape."""
    snippet = raw.get("snippet") if isinstance(raw.get("snippet"), dict) else {}
    stats = raw.get("statistics") if isinstance(raw.get("statistics"), dict) else {}
    video_id = raw.get("id") or raw.get("video_id")
    return {
        "id": str(video_id) if video_id else None,
        "title": str(snippet.get("title") or raw.get("title") or "YouTube video")[:200],
        "description": str(snippet.get("description") or raw.get("description") or "")[:4000],
        "channel": str(
            snippet.get("channelTitle") or raw.get("channel") or "YouTube"
        )[:200],
        "published_at": (
            str(snippet.get("publishedAt")) if snippet.get("publishedAt") else None
        ),
        "thumbnails": _normalize_thumbnails(snippet.get("thumbnails")),
        "statistics": {
            "view_count": _int_or_none(stats.get("viewCount")),
            "like_count": _int_or_none(stats.get("likeCount")),
            "comment_count": _int_or_none(stats.get("commentCount")),
        },
    }


def normalize_channel_details(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a channels.list item into detail shape."""
    snippet = raw.get("snippet") if isinstance(raw.get("snippet"), dict) else {}
    stats = raw.get("statistics") if isinstance(raw.get("statistics"), dict) else {}
    channel_id = raw.get("id") or raw.get("channel_id")
    return {
        "id": str(channel_id) if channel_id else None,
        "title": str(snippet.get("title") or raw.get("title") or "YouTube channel")[:200],
        "description": str(snippet.get("description") or raw.get("description") or "")[:4000],
        "thumbnails": _normalize_thumbnails(snippet.get("thumbnails")),
        "statistics": {
            "subscriber_count": _int_or_none(stats.get("subscriberCount")),
            "video_count": _int_or_none(stats.get("videoCount")),
            "view_count": _int_or_none(stats.get("viewCount")),
        },
    }


def _search_videos(
    query: str,
    *,
    max_results: int,
    api_key: str,
) -> list[dict[str, Any]]:
    payload = _api_get(
        YT_SEARCH_URL,
        {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": max(1, min(int(max_results), 50)),
            "key": api_key,
            "safeSearch": "moderate",
        },
    )
    items_raw = payload.get("items")
    if not isinstance(items_raw, list):
        return []
    return [
        normalize_youtube_video(item)
        for item in items_raw
        if isinstance(item, dict)
    ]


def search_youtube(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Search YouTube and return normalized feed cards. Requires API key."""
    key = _require_key(api_key)
    q = (query or "").strip()
    if not q:
        raise YouTubeAPIError("query is required", status_code=400)
    return _search_videos(q, max_results=max_results, api_key=key)


def get_video_details(
    video_id: str,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch one video via videos.list and return normalized detail."""
    key = _require_key(api_key)
    vid = (video_id or "").strip()
    if not VIDEO_ID_RE.fullmatch(vid):
        raise YouTubeAPIError("video_id must be an 11-character YouTube id", status_code=400)

    payload = _api_get(
        YT_VIDEOS_URL,
        {
            "part": "snippet,statistics",
            "id": vid,
            "key": key,
        },
    )
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise YouTubeAPIError("Video not found", status_code=404)
    raw = items[0]
    if not isinstance(raw, dict):
        raise YouTubeAPIError("Video not found", status_code=404)
    return normalize_video_details(raw)


def get_channel_details(
    channel_id: str,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch one channel via channels.list and return normalized detail."""
    key = _require_key(api_key)
    cid = (channel_id or "").strip()
    if not cid:
        raise YouTubeAPIError("channel_id is required", status_code=400)

    payload = _api_get(
        YT_CHANNELS_URL,
        {
            "part": "snippet,statistics",
            "id": cid,
            "key": key,
        },
    )
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise YouTubeAPIError("Channel not found", status_code=404)
    raw = items[0]
    if not isinstance(raw, dict):
        raise YouTubeAPIError("Channel not found", status_code=404)
    return normalize_channel_details(raw)


def fetch_youtube_feed(
    query: str | None = None,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search YouTube Data API v3 and return normalized video cards.

    Uses YOUTUBE_API_KEY (or CRASHOUT_YOUTUBE_API_KEY). Falls back to a curated
    recovery list when the key is missing or the API call fails.
    """
    key = _resolve_key(api_key)
    q = (query or DEFAULT_QUERY).strip() or DEFAULT_QUERY

    if not key:
        logger.info("YouTube API key not set — returning curated feed")
        return [dict(item) for item in CURATED_YOUTUBE_FEED]

    try:
        items = search_youtube(q, max_results=max_results, api_key=key)
        if items:
            return items
    except YouTubeAPIError as exc:
        logger.info("YouTube search unavailable: %s", exc)

    return [dict(item) for item in CURATED_YOUTUBE_FEED]


def _envelope(
    *,
    title: str,
    items: list[dict[str, Any]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "platform": "youtube",
        "lane": "youtube",
        "title": title,
        "items": items,
        "count": len(items),
        "meta": meta,
    }


def build_youtube_feed_response(
    query: str | None = None,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    api_key: str | None = None,
) -> dict[str, Any]:
    """TikTok-style feed envelope for GET /api/youtube/feed."""
    key = _resolve_key(api_key)
    q = (query or DEFAULT_QUERY).strip() or DEFAULT_QUERY
    items = fetch_youtube_feed(q, max_results=max_results, api_key=key or None)
    curated_ids = {c["id"] for c in CURATED_YOUTUBE_FEED}
    mode = "curated" if not items or all(i.get("id") in curated_ids for i in items) else "live"
    if not key:
        mode = "curated"

    return _envelope(
        title="YouTube Recovery Feed",
        items=items,
        meta={
            "mode": mode,
            "query": q,
            "errors": [],
            "api_configured": bool(key),
            "has_token": bool(key),
        },
    )


def build_youtube_search_response(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    api_key: str | None = None,
) -> dict[str, Any]:
    """TikTok-style envelope for GET /api/youtube/search."""
    key = _resolve_key(api_key)
    items = search_youtube(query, max_results=max_results, api_key=api_key)
    return _envelope(
        title="YouTube Search",
        items=items,
        meta={
            "mode": "live",
            "query": (query or "").strip(),
            "errors": [],
            "api_configured": bool(key),
            "has_token": bool(key),
        },
    )


def build_youtube_video_response(
    video_id: str,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """TikTok-style envelope for GET /api/youtube/video/{video_id}."""
    key = _resolve_key(api_key)
    detail = get_video_details(video_id, api_key=api_key)
    return _envelope(
        title=detail.get("title") or "YouTube Video",
        items=[detail],
        meta={
            "mode": "live",
            "video_id": video_id,
            "errors": [],
            "api_configured": bool(key),
            "has_token": bool(key),
        },
    )


def build_youtube_channel_response(
    channel_id: str,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """TikTok-style envelope for GET /api/youtube/channel/{channel_id}."""
    key = _resolve_key(api_key)
    detail = get_channel_details(channel_id, api_key=api_key)
    return _envelope(
        title=detail.get("title") or "YouTube Channel",
        items=[detail],
        meta={
            "mode": "live",
            "channel_id": channel_id,
            "errors": [],
            "api_configured": bool(key),
            "has_token": bool(key),
        },
    )
