"""Staff platform overview + content flagging."""
from __future__ import annotations

from typing import Any

from app.db import get_conn, row_to_dict, utc_now_iso


def get_platform_overview() -> dict[str, Any]:
    """Platform health snapshot for staff oversight."""
    with get_conn() as conn:
        creators = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE role = 'user' OR role = 'staff'"
        ).fetchone()
        # Feed-ish item proxies: history rows + topic cache
        history_items = conn.execute(
            "SELECT COUNT(DISTINCT item_id) AS c FROM user_history"
        ).fetchone()
        topic_items = conn.execute(
            "SELECT COUNT(*) AS c FROM topic_cache"
        ).fetchone()
        ads_served = conn.execute(
            "SELECT COUNT(*) AS c FROM ad_clicks"
        ).fetchone()
        ads_inventory = conn.execute(
            "SELECT COUNT(*) AS c FROM ad_inventory"
        ).fetchone()
        rec_volume = conn.execute(
            "SELECT COUNT(*) AS c FROM user_similarity"
        ).fetchone()
        flags = conn.execute(
            "SELECT COUNT(*) AS c FROM flagged_items WHERE active = 1"
        ).fetchone()

    total_items = int(history_items["c"] if history_items else 0) + int(
        topic_items["c"] if topic_items else 0
    )
    ranking_latency_ms = 12.0  # placeholder local ranking cost
    summary = {
        "id": "platform_overview",
        "total_creators": int(creators["c"] if creators else 0),
        "total_items": total_items,
        "total_ads_served": int(ads_served["c"] if ads_served else 0),
        "ad_inventory": int(ads_inventory["c"] if ads_inventory else 0),
        "recommendation_volume": int(rec_volume["c"] if rec_volume else 0),
        "ranking_latency_ms": ranking_latency_ms,
        "active_flags": int(flags["c"] if flags else 0),
    }
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "staff",
        "title": "Staff Overview",
        "items": [summary],
        "count": 1,
        "meta": summary,
    }


def get_flagged_items() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, item_id, reason, flagged_by, flagged_at, active
            FROM flagged_items
            WHERE active = 1
            ORDER BY flagged_at DESC
            """
        ).fetchall()
    items = [row_to_dict(r) for r in rows]
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "staff",
        "title": "Flagged Items",
        "items": items,
        "count": len(items),
        "meta": {"active_flags": len(items)},
    }


def flag_item(
    item_id: str,
    *,
    reason: str | None = None,
    flagged_by: int | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    iid = str(item_id).strip()
    if not iid:
        return {
            "ok": False,
            "platform": "crashout",
            "lane": "staff",
            "title": "Flag Item",
            "items": [],
            "count": 0,
            "meta": {"reason": "item_id_required"},
        }
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM flagged_items WHERE item_id = ?",
            (iid,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE flagged_items
                SET active = 1, reason = ?, flagged_by = ?, flagged_at = ?
                WHERE item_id = ?
                """,
                (reason, flagged_by, now, iid),
            )
        else:
            conn.execute(
                """
                INSERT INTO flagged_items (item_id, reason, flagged_by, flagged_at, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (iid, reason, flagged_by, now),
            )
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "staff",
        "title": "Flag Item",
        "items": [{"item_id": iid, "reason": reason, "flagged_at": now}],
        "count": 1,
        "meta": {"item_id": iid, "flagged": True},
    }


def unflag_item(item_id: str) -> dict[str, Any]:
    iid = str(item_id).strip()
    with get_conn() as conn:
        conn.execute(
            "UPDATE flagged_items SET active = 0 WHERE item_id = ?",
            (iid,),
        )
    return {
        "ok": True,
        "platform": "crashout",
        "lane": "staff",
        "title": "Unflag Item",
        "items": [{"item_id": iid, "flagged": False}],
        "count": 1,
        "meta": {"item_id": iid, "flagged": False},
    }
