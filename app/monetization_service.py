"""Monetization lanes — ads, clicks, creator earnings."""
from __future__ import annotations

from typing import Any

from app.db import get_conn, row_to_dict, utc_now_iso

MONETIZATION_LANES: list[dict[str, Any]] = [
    {
        "id": "ads",
        "title": "Ads",
        "description": "Serve recovery-safe ad cards in the feed.",
    },
    {
        "id": "creator_payouts",
        "title": "Creator payouts",
        "description": "Cash out earnings from ad clicks.",
    },
    {
        "id": "sponsorships",
        "title": "Sponsorships",
        "description": "Brand-safe sponsorship placements (coming soon).",
    },
    {
        "id": "premium_feed",
        "title": "Premium feed",
        "description": "Subscriber feed placements (coming soon).",
    },
]

DEFAULT_ADS_EVERY_N = 3


def get_monetization_lanes() -> dict[str, Any]:
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "monetization",
        "title": "Monetization Lanes",
        "items": list(MONETIZATION_LANES),
        "count": len(MONETIZATION_LANES),
        "meta": {"lanes": [x["id"] for x in MONETIZATION_LANES]},
    }


def get_ads() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, image_url, cta_url, payout_per_click
            FROM ad_inventory
            ORDER BY id ASC
            """
        ).fetchall()
    items = []
    for row in rows:
        d = row_to_dict(row)
        items.append(
            {
                "id": d["id"],
                "title": d["title"],
                "image": d.get("image_url"),
                "cta": d.get("cta_url"),
                "payout_per_click": float(d.get("payout_per_click") or 0),
            }
        )
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "ads",
        "title": "Ad Inventory",
        "items": items,
        "count": len(items),
        "meta": {},
    }


def _parse_creator_id(creator_id: str | int | None) -> int | None:
    if creator_id is None:
        return None
    text = str(creator_id).strip()
    if text.isdigit():
        return int(text)
    return None


def record_ad_click(ad_id: int | str, creator_id: int | str | None) -> dict[str, Any]:
    """Record an ad click and increment creator earnings."""
    try:
        aid = int(ad_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("ad_id must be an integer") from exc
    cid = _parse_creator_id(creator_id)
    if cid is None:
        raise ValueError("creator_id is required")

    now = utc_now_iso()
    with get_conn() as conn:
        ad = conn.execute(
            "SELECT id, payout_per_click FROM ad_inventory WHERE id = ?",
            (aid,),
        ).fetchone()
        if not ad:
            raise LookupError("ad not found")
        payout = float(ad["payout_per_click"] or 0)

        # Ensure user row exists for FK — skip FK failure by allowing orphan creator_id
        # if users table missing that id: creator_earnings FK is to users. Soft-create earnings only.
        user = conn.execute("SELECT id FROM users WHERE id = ?", (cid,)).fetchone()
        if not user:
            raise LookupError("creator not found")

        conn.execute(
            """
            INSERT INTO ad_clicks (ad_id, creator_id, timestamp, payout_amount)
            VALUES (?, ?, ?, ?)
            """,
            (aid, cid, now, payout),
        )
        existing = conn.execute(
            "SELECT id, total_earnings FROM creator_earnings WHERE creator_id = ?",
            (cid,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE creator_earnings
                SET total_earnings = total_earnings + ?
                WHERE creator_id = ?
                """,
                (payout, cid),
            )
        else:
            conn.execute(
                """
                INSERT INTO creator_earnings (creator_id, total_earnings, last_payout)
                VALUES (?, ?, NULL)
                """,
                (cid, payout),
            )

    return {
        "ok": True,
        "platform": "crashout",
        "lane": "ads",
        "title": "Ad Click",
        "items": [],
        "count": 0,
        "earnings_updated": True,
        "meta": {
            "ad_id": aid,
            "creator_id": cid,
            "payout_amount": payout,
            "earnings_updated": True,
        },
    }


def get_creator_earnings(creator_id: str | int) -> dict[str, Any]:
    cid = _parse_creator_id(creator_id)
    if cid is None:
        return {
            "ok": False,
            "platform": "crashout",
            "lane": "earnings",
            "title": "Creator Earnings",
            "items": [],
            "count": 0,
            "meta": {"reason": "invalid_creator_id"},
        }

    with get_conn() as conn:
        earn = conn.execute(
            "SELECT * FROM creator_earnings WHERE creator_id = ?",
            (cid,),
        ).fetchone()
        click_row = conn.execute(
            """
            SELECT COUNT(*) AS clicks, COALESCE(SUM(payout_amount), 0) AS total
            FROM ad_clicks WHERE creator_id = ?
            """,
            (cid,),
        ).fetchone()

    clicks = int(click_row["clicks"] if click_row else 0)
    total = float(earn["total_earnings"]) if earn else float(click_row["total"] if click_row else 0)
    last_payout = earn["last_payout"] if earn else None
    rpm = (total / clicks * 1000.0) if clicks else 0.0
    summary = {
        "total_earnings": round(total, 4),
        "clicks": clicks,
        "rpm": round(rpm, 4),
        "last_payout": last_payout,
        "creator_id": cid,
    }
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "earnings",
        "title": "Creator Earnings",
        "items": [summary],
        "count": 1,
        "meta": summary,
    }


def get_creator_monetization(creator_id: str | int) -> dict[str, Any]:
    """Dashboard monetization summary: earnings, clicks, rpm, ads_served."""
    base = get_creator_earnings(creator_id)
    if not base.get("ok"):
        return {
            **base,
            "lane": "monetization",
            "title": "Creator Monetization",
        }
    summary = (base.get("items") or [{}])[0]
    cid = summary.get("creator_id")
    with get_conn() as conn:
        ads_served = conn.execute("SELECT COUNT(*) AS c FROM ad_inventory").fetchone()
    payload = {
        "earnings": summary.get("total_earnings", 0),
        "clicks": summary.get("clicks", 0),
        "rpm": summary.get("rpm", 0),
        "ads_served": int(ads_served["c"] if ads_served else 0),
        "last_payout": summary.get("last_payout"),
        "creator_id": cid,
    }
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "monetization",
        "title": "Creator Monetization",
        "items": [payload],
        "count": 1,
        "meta": payload,
    }


def process_creator_payout(creator_id: str | int) -> dict[str, Any]:
    cid = _parse_creator_id(creator_id)
    if cid is None:
        raise ValueError("creator_id is required")
    now = utc_now_iso()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, total_earnings FROM creator_earnings WHERE creator_id = ?",
            (cid,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE creator_earnings
                SET last_payout = ?
                WHERE creator_id = ?
                """,
                (now, cid),
            )
            total = float(existing["total_earnings"] or 0)
        else:
            conn.execute(
                """
                INSERT INTO creator_earnings (creator_id, total_earnings, last_payout)
                VALUES (?, 0, ?)
                """,
                (cid, now),
            )
            total = 0.0
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "payout",
        "title": "Creator Payout",
        "items": [],
        "count": 0,
        "payout_processed": True,
        "meta": {
            "creator_id": cid,
            "last_payout": now,
            "total_earnings": total,
            "payout_processed": True,
        },
    }
