"""Engagement scoring + personalization for unified feeds."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from app.db import get_conn, row_to_dict, utc_now_iso

PLATFORM_WEIGHTS = {
    "youtube": 1.0,
    "tiktok": 1.05,
    "ad": 0.4,
    "unknown": 0.8,
}

# Sample item for GET /api/ranking/score demo
SAMPLE_SCORE_ITEM: dict[str, Any] = {
    "id": "sample_score_1",
    "views": 12000,
    "likes": 840,
    "comments": 95,
    "published_at": datetime.now(timezone.utc).isoformat(),
    "platform": "youtube",
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_ts(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _clamp(score: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, score))


def score_item(item: dict[str, Any]) -> float:
    """
    Engagement score 0–100 from views/likes/comments/recency/platform.

    Weights:
    - recency
    - platform weight (YouTube / TikTok)
    - interaction density (likes/views)
    - comment velocity
    """
    views = max(_num(item.get("views", item.get("view_count"))), 0.0)
    likes = max(_num(item.get("likes", item.get("like_count"))), 0.0)
    comments = max(_num(item.get("comments", item.get("comment_count"))), 0.0)
    platform = str(item.get("platform") or "unknown").lower()
    platform_w = PLATFORM_WEIGHTS.get(platform, PLATFORM_WEIGHTS["unknown"])

    # Recency: fresher content scores higher (7-day half-life style)
    ts = _parse_ts(item.get("published_at"))
    if ts is None:
        recency = 35.0
    else:
        age_hours = max(0.0, (datetime.now(timezone.utc).timestamp() - ts) / 3600.0)
        recency = 40.0 * math.exp(-age_hours / (24.0 * 7.0))

    # Interaction density: likes / views
    density = 0.0 if views <= 0 else min(1.0, likes / views)
    density_score = 30.0 * density

    # Comment velocity relative to views
    comment_rate = 0.0 if views <= 0 else min(1.0, (comments * 20.0) / views)
    comment_score = 20.0 * comment_rate

    # Soft volume signal so high-view items aren't ignored when ratios are low
    volume = 10.0 * min(1.0, math.log10(views + 1.0) / 5.0)

    raw = (recency + density_score + comment_score + volume) * platform_w
    return round(_clamp(raw), 2)


def score_feed(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply score_item and return sorted by engagement_score desc."""
    scored: list[dict[str, Any]] = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        item["engagement_score"] = score_item(item)
        scored.append(item)
    return sorted(
        scored,
        key=lambda i: _num(i.get("engagement_score")),
        reverse=True,
    )


def _load_preferences(user_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return {
            "preferred_platforms": [],
            "preferred_channels": [],
            "last_seen_item": None,
        }
    d = row_to_dict(row)
    platforms = d.get("preferred_platforms") or "[]"
    channels = d.get("preferred_channels") or "[]"
    if isinstance(platforms, str):
        try:
            platforms = json.loads(platforms)
        except json.JSONDecodeError:
            platforms = []
    if isinstance(channels, str):
        try:
            channels = json.loads(channels)
        except json.JSONDecodeError:
            channels = []
    return {
        "preferred_platforms": list(platforms or []),
        "preferred_channels": list(channels or []),
        "last_seen_item": d.get("last_seen_item"),
    }


def _load_history_signals(user_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT item_id, platform
            FROM user_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()
    item_ids = set()
    platforms: dict[str, int] = {}
    for row in rows:
        d = row_to_dict(row)
        item_ids.add(str(d.get("item_id") or ""))
        p = str(d.get("platform") or "").lower()
        if p:
            platforms[p] = platforms.get(p, 0) + 1
    return {"item_ids": item_ids, "platforms": platforms}


def personalize_feed(user_id: int | str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Boost items matching watched channels, search/history platforms, preferences.
    Falls back to score_feed when no history/preferences.
    """
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return score_feed(items)

    prefs = _load_preferences(uid)
    history = _load_history_signals(uid)
    has_signal = bool(
        prefs["preferred_platforms"]
        or prefs["preferred_channels"]
        or history["item_ids"]
        or history["platforms"]
    )
    scored = score_feed(items)
    if not has_signal:
        return scored

    pref_platforms = {str(p).lower() for p in prefs["preferred_platforms"]}
    pref_channels = {str(c).lower() for c in prefs["preferred_channels"]}
    hist_platforms = set(history["platforms"].keys())

    boosted: list[dict[str, Any]] = []
    for raw in scored:
        item = dict(raw)
        boost = 0.0
        platform = str(item.get("platform") or "").lower()
        channel = str(item.get("channel") or item.get("author") or "").lower()
        item_id = str(item.get("id") or "")

        if platform in pref_platforms:
            boost += 12.0
        if platform in hist_platforms:
            boost += 6.0
        if channel and any(c in channel or channel in c for c in pref_channels if c):
            boost += 15.0
        if item_id and item_id in history["item_ids"]:
            boost += 4.0  # familiarity

        item["engagement_score"] = round(
            _clamp(_num(item.get("engagement_score")) + boost), 2
        )
        item["personalization_boost"] = boost
        boosted.append(item)

    return sorted(
        boosted,
        key=lambda i: _num(i.get("engagement_score")),
        reverse=True,
    )


def record_history(
    user_id: int | str,
    item_id: str,
    platform: str,
) -> dict[str, Any]:
    uid = int(user_id)
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_history (user_id, item_id, platform, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (uid, str(item_id), str(platform or "unknown"), now),
        )
        # Touch preferences last_seen + ensure row exists
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE user_id = ?",
            (uid,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE user_preferences
                SET last_seen_item = ?
                WHERE user_id = ?
                """,
                (str(item_id), uid),
            )
        else:
            conn.execute(
                """
                INSERT INTO user_preferences (
                    user_id, preferred_platforms, preferred_channels, last_seen_item
                ) VALUES (?, '[]', '[]', ?)
                """,
                (uid, str(item_id)),
            )
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "history",
        "title": "History recorded",
        "items": [],
        "count": 0,
        "meta": {
            "user_id": uid,
            "item_id": str(item_id),
            "platform": str(platform or "unknown"),
            "timestamp": now,
        },
    }


def get_preferences(user_id: int | str) -> dict[str, Any]:
    uid = int(user_id)
    prefs = _load_preferences(uid)
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "preferences",
        "title": "User Preferences",
        "items": [{**prefs, "user_id": uid}],
        "count": 1,
        "meta": {"user_id": uid},
    }


def upsert_preferences(
    user_id: int | str,
    *,
    preferred_platforms: list[str] | None = None,
    preferred_channels: list[str] | None = None,
) -> dict[str, Any]:
    """Helper for tests / future UI — not required by routes yet."""
    uid = int(user_id)
    platforms = json.dumps(list(preferred_platforms or []))
    channels = json.dumps(list(preferred_channels or []))
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE user_id = ?",
            (uid,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE user_preferences
                SET preferred_platforms = ?, preferred_channels = ?
                WHERE user_id = ?
                """,
                (platforms, channels, uid),
            )
        else:
            conn.execute(
                """
                INSERT INTO user_preferences (
                    user_id, preferred_platforms, preferred_channels, last_seen_item
                ) VALUES (?, ?, ?, NULL)
                """,
                (uid, platforms, channels),
            )
    return get_preferences(uid)


def build_score_demo_response() -> dict[str, Any]:
    score = score_item(SAMPLE_SCORE_ITEM)
    item = {**SAMPLE_SCORE_ITEM, "engagement_score": score}
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "ranking",
        "title": "Engagement Score Demo",
        "items": [item],
        "count": 1,
        "meta": {"engagement_score": score, "formula": "recency+platform+density+comments"},
    }


def build_personalized_feed_response(
    user_id: int | str,
    *,
    max_results: int = 12,
) -> dict[str, Any]:
    from app.feed_service import build_unified_all_response

    base = build_unified_all_response(max_results=max_results, with_ads=False)
    items = personalize_feed(user_id, list(base.get("items") or []))
    return {
        "ok": True,
        "platform": "unified",
        "lane": "personalized",
        "title": "Personalized Recovery Feed",
        "items": items,
        "count": len(items),
        "meta": {
            "user_id": int(user_id) if str(user_id).isdigit() else user_id,
            "ranked": True,
            "personalized": True,
            "sources": (base.get("meta") or {}).get("sources", ["youtube", "tiktok"]),
        },
    }
