"""Creator growth engine — score, trends, opportunities."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import get_conn, row_to_dict
from app.monetization_service import get_creator_earnings
from app.recommendation_service import build_topics_response, recommend_all


def _cid(creator_id: int | str) -> int:
    return int(creator_id)


def _history_count(creator_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM user_history WHERE user_id = ?",
            (creator_id,),
        ).fetchone()
    return int(row["c"] if row else 0)


def _engagement_proxy(creator_id: int) -> dict[str, float]:
    """Derive engagement from history + ad clicks when live analytics are absent."""
    with get_conn() as conn:
        hist = conn.execute(
            "SELECT COUNT(*) AS c FROM user_history WHERE user_id = ?",
            (creator_id,),
        ).fetchone()
        clicks = conn.execute(
            "SELECT COUNT(*) AS c FROM ad_clicks WHERE creator_id = ?",
            (creator_id,),
        ).fetchone()
        prefs = conn.execute(
            "SELECT preferred_platforms FROM user_preferences WHERE user_id = ?",
            (creator_id,),
        ).fetchone()
    views = float(hist["c"] if hist else 0) * 12.0
    likes = float(hist["c"] if hist else 0) * 3.0
    comments = float(hist["c"] if hist else 0) * 0.8
    ad_clicks = float(clicks["c"] if clicks else 0)
    platform_boost = 5.0 if prefs else 0.0
    return {
        "views": views + platform_boost,
        "likes": likes,
        "comments": comments,
        "ad_clicks": ad_clicks,
    }


def _recommendations_served(creator_id: int) -> int:
    try:
        payload = recommend_all(creator_id, max_results=12)
        return int(payload.get("count") or 0)
    except Exception:
        return 0


def compute_creator_growth(creator_id: int | str) -> dict[str, Any]:
    """
    Growth score 0–100 from history, earnings, engagement, recommendations.
    """
    cid = _cid(creator_id)
    history_n = _history_count(cid)
    earnings = get_creator_earnings(cid)
    earn_total = 0.0
    if earnings.get("ok") and earnings.get("items"):
        earn_total = float((earnings["items"][0] or {}).get("total_earnings") or 0)
    eng = _engagement_proxy(cid)
    rec_n = _recommendations_served(cid)

    # Weighted blend (capped components)
    hist_score = min(30.0, history_n * 2.5)
    earn_score = min(25.0, earn_total * 40.0)
    eng_score = min(
        30.0,
        (eng["views"] / 50.0)
        + (eng["likes"] / 20.0)
        + (eng["comments"] / 5.0)
        + (eng["ad_clicks"] * 2.0),
    )
    rec_score = min(15.0, rec_n * 1.2)
    growth_score = round(min(100.0, hist_score + earn_score + eng_score + rec_score), 1)

    return {
        "ok": True,
        "platform": "unified",
        "lane": "growth",
        "title": "Creator Growth Score",
        "items": [
            {
                "id": f"growth_{cid}",
                "creator_id": cid,
                "growth_score": growth_score,
                "components": {
                    "history": round(hist_score, 1),
                    "earnings": round(earn_score, 1),
                    "engagement": round(eng_score, 1),
                    "recommendations": round(rec_score, 1),
                },
            }
        ],
        "count": 1,
        "meta": {
            "creator_id": cid,
            "growth_score": growth_score,
            "history_events": history_n,
            "earnings": earn_total,
            "recommendations_served": rec_n,
        },
    }


def get_creator_growth_trends(creator_id: int | str) -> dict[str, Any]:
    """30-day trend of views, likes, comments, earnings, recommendations served."""
    cid = _cid(creator_id)
    eng = _engagement_proxy(cid)
    earnings = get_creator_earnings(cid)
    earn_total = 0.0
    if earnings.get("ok") and earnings.get("items"):
        earn_total = float((earnings["items"][0] or {}).get("total_earnings") or 0)
    rec_n = _recommendations_served(cid)

    # Deterministic synthetic 30-day series seeded by creator_id
    seed = int(hashlib.md5(str(cid).encode(), usedforsecurity=False).hexdigest()[:8], 16)
    today = datetime.now(timezone.utc).date()
    days: list[dict[str, Any]] = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        wave = ((seed + i * 17) % 10) / 10.0
        ramp = (30 - i) / 30.0
        days.append(
            {
                "id": f"trend_{cid}_{day.isoformat()}",
                "date": day.isoformat(),
                "views": round(max(0, eng["views"] * ramp * (0.6 + wave) / 30), 1),
                "likes": round(max(0, eng["likes"] * ramp * (0.6 + wave) / 30), 1),
                "comments": round(max(0, eng["comments"] * ramp * (0.5 + wave) / 30), 1),
                "earnings": round(max(0, earn_total * ramp * (0.5 + wave) / 30), 4),
                "recommendations_served": max(
                    0, int(rec_n * ramp * (0.4 + wave) / 5)
                ),
            }
        )

    return {
        "ok": True,
        "platform": "unified",
        "lane": "growth",
        "title": "Creator Growth Trends",
        "items": days,
        "count": len(days),
        "meta": {"creator_id": cid, "days": 30},
    }


def get_creator_opportunities(creator_id: int | str) -> dict[str, Any]:
    """Suggest topics, clusters, posting times, and platform boosts."""
    cid = _cid(creator_id)
    topics_payload = build_topics_response(max_results=24)
    clusters = topics_payload.get("items") or []
    top_topics = [c.get("topic") for c in clusters[:5] if c.get("topic")]
    high_engagement = [
        {
            "topic": c.get("topic"),
            "count": c.get("count"),
            "sample_ids": [i.get("id") for i in (c.get("items") or [])[:3]],
        }
        for c in clusters[:3]
    ]
    posting_times = ["07:00", "12:30", "18:00", "21:15"]
    platform_boosts = [
        {"platform": "youtube", "boost": "Shorts + recovery checklist CTA"},
        {"platform": "tiktok", "boost": "15s calm-redirect hooks"},
        {"platform": "instagram", "boost": "Carousel pause prompts"},
    ]
    items = [
        {
            "id": f"opp_topics_{cid}",
            "kind": "trending_topics",
            "title": "Trending topics",
            "values": top_topics or ["recovery", "calm", "draft"],
        },
        {
            "id": f"opp_clusters_{cid}",
            "kind": "high_engagement_clusters",
            "title": "High-engagement clusters",
            "values": high_engagement,
        },
        {
            "id": f"opp_times_{cid}",
            "kind": "posting_times",
            "title": "Recommended posting times",
            "values": posting_times,
        },
        {
            "id": f"opp_platforms_{cid}",
            "kind": "platform_boosts",
            "title": "Platform-specific boosts",
            "values": platform_boosts,
        },
    ]
    return {
        "ok": True,
        "platform": "unified",
        "lane": "growth",
        "title": "Creator Opportunities",
        "items": items,
        "count": len(items),
        "meta": {"creator_id": cid, "topic_count": len(top_topics)},
    }
