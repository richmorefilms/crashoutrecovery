"""Multi-platform ingestion (Instagram, Facebook, Twitter, Pinterest).

Filename keeps the platform spelling requested by the growth brief
(`multiplaform_service`).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CURATED: dict[str, list[dict[str, Any]]] = {
    "instagram": [
        {
            "id": "ig_pause_reel",
            "title": "Pause reel — one calm next step",
            "description": "Short recovery redirect for Instagram Reels.",
            "channel": "CrashoutCalm",
            "thumbnail": None,
            "url": "https://www.instagram.com/",
            "published_at": "2026-07-01T12:00:00+00:00",
        },
        {
            "id": "ig_draft_story",
            "title": "Draft it, don't post it",
            "description": "Story-style reminder to save the draft.",
            "channel": "RecoveryNotes",
            "thumbnail": None,
            "url": "https://www.instagram.com/",
            "published_at": "2026-07-02T15:00:00+00:00",
        },
    ],
    "facebook": [
        {
            "id": "fb_group_check",
            "title": "Group check-in without the spiral",
            "description": "Community post template for safer sharing.",
            "channel": "Crashout Recovery",
            "thumbnail": None,
            "url": "https://www.facebook.com/",
            "published_at": "2026-07-03T10:00:00+00:00",
        },
    ],
    "twitter": [
        {
            "id": "tw_thread_pause",
            "title": "Thread: three breaths before reply",
            "description": "Micro-pause cue for heated timelines.",
            "channel": "@crashoutrecovery",
            "thumbnail": None,
            "url": "https://twitter.com/",
            "published_at": "2026-07-04T09:00:00+00:00",
        },
        {
            "id": "tw_momentum",
            "title": "Small win > viral crashout",
            "description": "Momentum over impulse.",
            "channel": "@crashoutrecovery",
            "thumbnail": None,
            "url": "https://twitter.com/",
            "published_at": "2026-07-05T11:00:00+00:00",
        },
    ],
    "pinterest": [
        {
            "id": "pin_calm_board",
            "title": "Calm corner mood board",
            "description": "Visual anchors for a cooler head.",
            "channel": "Crashout Boards",
            "thumbnail": None,
            "url": "https://www.pinterest.com/",
            "published_at": "2026-07-06T14:00:00+00:00",
        },
    ],
}


def _normalize(platform: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("id") or ""),
        "platform": platform,
        "title": raw.get("title") or "Recovery clip",
        "description": raw.get("description") or "",
        "channel": raw.get("channel") or platform,
        "thumbnail": raw.get("thumbnail"),
        "url": raw.get("url"),
        "published_at": raw.get("published_at")
        or datetime.now(timezone.utc).isoformat(),
    }


def _envelope(platform: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ok": True,
        "platform": platform,
        "lane": "multiplatform",
        "title": f"{platform.title()} Feed",
        "items": items,
        "count": len(items),
        "meta": {"source": "curated", "ingested_at": datetime.now(timezone.utc).isoformat()},
    }


def fetch_instagram_feed() -> dict[str, Any]:
    items = [_normalize("instagram", r) for r in CURATED["instagram"]]
    return _envelope("instagram", items)


def fetch_facebook_feed() -> dict[str, Any]:
    items = [_normalize("facebook", r) for r in CURATED["facebook"]]
    return _envelope("facebook", items)


def fetch_twitter_feed() -> dict[str, Any]:
    items = [_normalize("twitter", r) for r in CURATED["twitter"]]
    return _envelope("twitter", items)


def fetch_pinterest_feed() -> dict[str, Any]:
    items = [_normalize("pinterest", r) for r in CURATED["pinterest"]]
    return _envelope("pinterest", items)
