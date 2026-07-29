"""Creator dashboard helpers — channels + analytics (OAuth-gated)."""
from __future__ import annotations

import logging
from typing import Any

import requests

from app.oauth_service import get_tokens
from app.youtube_service import YT_CHANNELS_URL, normalize_channel_details

logger = logging.getLogger("crashout.creator")

YT_ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"


def _parse_creator_id(creator_id: str) -> int | None:
    text = (creator_id or "").strip()
    if text.isdigit():
        return int(text)
    return None


def get_creator_channels(creator_id: str) -> dict[str, Any]:
    """
    Return linked YouTube channels for a creator (user_id).

    If no OAuth tokens: { ok: false, reason: "not_linked", ...envelope }.
    """
    user_id = _parse_creator_id(creator_id)
    if user_id is None:
        return {
            "ok": False,
            "reason": "not_linked",
            "platform": "youtube",
            "lane": "creator",
            "title": "Creator Channels",
            "items": [],
            "count": 0,
            "meta": {"reason": "invalid_creator_id", "creator_id": str(creator_id)},
        }

    tokens = get_tokens(user_id)
    if not tokens or not tokens.get("access_token"):
        return {
            "ok": False,
            "reason": "not_linked",
            "platform": "youtube",
            "lane": "creator",
            "title": "Creator Channels",
            "items": [],
            "count": 0,
            "meta": {"reason": "not_linked", "creator_id": str(creator_id)},
        }

    try:
        resp = requests.get(
            YT_CHANNELS_URL,
            params={
                "part": "snippet,statistics",
                "mine": "true",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=20,
        )
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.info("Creator channels fetch failed: %s", exc)
        return {
            "ok": False,
            "reason": "fetch_failed",
            "platform": "youtube",
            "lane": "creator",
            "title": "Creator Channels",
            "items": [],
            "count": 0,
            "meta": {
                "reason": "fetch_failed",
                "creator_id": str(creator_id),
                "error": str(exc),
            },
        }

    if resp.status_code >= 400:
        return {
            "ok": False,
            "reason": "fetch_failed",
            "platform": "youtube",
            "lane": "creator",
            "title": "Creator Channels",
            "items": [],
            "count": 0,
            "meta": {
                "reason": "fetch_failed",
                "creator_id": str(creator_id),
                "status_code": resp.status_code,
            },
        }

    items = [
        normalize_channel_details(raw)
        for raw in (payload.get("items") or [])
        if isinstance(raw, dict)
    ]
    return {
        "ok": True,
        "platform": "youtube",
        "lane": "creator",
        "title": "Creator Channels",
        "items": items,
        "count": len(items),
        "meta": {"creator_id": str(creator_id), "linked": True},
    }


def get_creator_analytics(creator_id: str) -> dict[str, Any]:
    """Return placeholder analytics when linked; not_linked otherwise."""
    user_id = _parse_creator_id(creator_id)
    if user_id is None:
        return {
            "ok": False,
            "reason": "not_linked",
            "platform": "youtube",
            "lane": "analytics",
            "title": "Creator Analytics",
            "items": [],
            "count": 0,
            "meta": {"reason": "invalid_creator_id", "creator_id": str(creator_id)},
        }

    tokens = get_tokens(user_id)
    if not tokens or not tokens.get("access_token"):
        return {
            "ok": False,
            "reason": "not_linked",
            "platform": "youtube",
            "lane": "analytics",
            "title": "Creator Analytics",
            "items": [],
            "count": 0,
            "meta": {"reason": "not_linked", "creator_id": str(creator_id)},
        }

    # Foundation: mock analytics (YouTube Analytics API wired later).
    _ = YT_ANALYTICS_URL
    placeholder = {
        "id": f"analytics_{creator_id}",
        "views": 0,
        "watch_time_minutes": 0,
        "subscribers_gained": 0,
        "estimated_revenue": 0,
        "mode": "placeholder",
    }
    return {
        "ok": True,
        "platform": "youtube",
        "lane": "analytics",
        "title": "Creator Analytics",
        "items": [placeholder],
        "count": 1,
        "meta": {
            "creator_id": str(creator_id),
            "linked": True,
            "mode": "placeholder",
        },
    }
