"""Phase G: stories, premium ads, club promotions, AdSense/AdMob helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import (
    ADMOB_AD_UNIT_ID,
    ADMOB_APP_ID,
    ADMOB_BANNER_UNIT_ID,
    ADMOB_INTERSTITIAL_UNIT_ID,
    ADSENSE_CLIENT_ID,
    ADSENSE_SLOT_FOOTER,
    ADSENSE_SLOT_MID,
    ADSENSE_SLOT_TOP,
)
from app.db import get_conn, row_to_dict, utc_now_iso

PREMIUM_AD_TYPES = frozenset({"banner", "poster", "video", "club_promo"})
AD_SOURCES = frozenset({"premium", "club"})


def adsense_context() -> dict[str, Any]:
    """Template context for AdSense script + slot ids (empty when unset)."""
    enabled = bool(ADSENSE_CLIENT_ID)
    return {
        "adsense_enabled": enabled,
        "adsense_client_id": ADSENSE_CLIENT_ID,
        "adsense_slot_top": ADSENSE_SLOT_TOP,
        "adsense_slot_mid": ADSENSE_SLOT_MID,
        "adsense_slot_footer": ADSENSE_SLOT_FOOTER,
    }


def admob_mobile_config() -> dict[str, Any]:
    return {
        "app_id": ADMOB_APP_ID or None,
        "ad_unit_id": ADMOB_AD_UNIT_ID or None,
        "banner_unit_id": ADMOB_BANNER_UNIT_ID or ADMOB_AD_UNIT_ID or None,
        "interstitial_unit_id": ADMOB_INTERSTITIAL_UNIT_ID or None,
        "configured": bool(ADMOB_APP_ID and (ADMOB_AD_UNIT_ID or ADMOB_BANNER_UNIT_ID)),
    }


def create_story(
    *,
    title: str,
    body: str = "",
    crashout_id: int | None = None,
    image_url: str | None = None,
    video_url: str | None = None,
    thumbnail_url: str | None = None,
    published: bool = False,
    path: Path | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO stories (
                title, body, crashout_id, image_url, video_url, thumbnail_url,
                published, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                body,
                crashout_id,
                image_url,
                video_url,
                thumbnail_url,
                int(published),
                now,
                now,
            ),
        )
        story_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    return row_to_dict(row) or {}


def list_stories(
    *,
    published_only: bool = True,
    limit: int = 50,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    clauses = ["published = 1"] if published_only else []
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_conn(path) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM stories
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def get_story(story_id: int, *, path: Path | None = None) -> dict[str, Any] | None:
    with get_conn(path) as conn:
        row = conn.execute(
            "SELECT * FROM stories WHERE id = ?",
            (int(story_id),),
        ).fetchone()
    return row_to_dict(row)


def create_premium_ad(
    *,
    ad_type: str,
    media_url: str,
    target_url: str,
    active: bool = True,
    path: Path | None = None,
) -> dict[str, Any]:
    if ad_type not in PREMIUM_AD_TYPES:
        raise ValueError(f"Invalid ad_type; expected one of {sorted(PREMIUM_AD_TYPES)}")
    now = utc_now_iso()
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO premium_ads (ad_type, media_url, target_url, active, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ad_type, media_url, target_url, int(active), now),
        )
        ad_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM premium_ads WHERE id = ?", (ad_id,)).fetchone()
    return row_to_dict(row) or {}


def update_premium_ad(
    ad_id: int,
    *,
    ad_type: str | None = None,
    media_url: str | None = None,
    target_url: str | None = None,
    active: bool | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    sets: list[str] = []
    params: list[Any] = []
    if ad_type is not None:
        if ad_type not in PREMIUM_AD_TYPES:
            raise ValueError(f"Invalid ad_type; expected one of {sorted(PREMIUM_AD_TYPES)}")
        sets.append("ad_type = ?")
        params.append(ad_type)
    if media_url is not None:
        sets.append("media_url = ?")
        params.append(media_url)
    if target_url is not None:
        sets.append("target_url = ?")
        params.append(target_url)
    if active is not None:
        sets.append("active = ?")
        params.append(int(active))
    if not sets:
        raise ValueError("No premium ad fields to update")
    params.append(int(ad_id))
    with get_conn(path) as conn:
        cur = conn.execute(
            f"UPDATE premium_ads SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        if cur.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM premium_ads WHERE id = ?", (int(ad_id),)
        ).fetchone()
    return row_to_dict(row)


def list_premium_ads(
    *,
    active_only: bool = False,
    limit: int = 100,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    where = "WHERE active = 1" if active_only else ""
    with get_conn(path) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM premium_ads
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def create_club_promotion(
    *,
    title: str,
    description: str = "",
    media_url: str | None = None,
    video_url: str | None = None,
    active: bool = True,
    path: Path | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO club_promotions (
                title, media_url, video_url, description, active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title.strip(), media_url, video_url, description, int(active), now),
        )
        promo_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT * FROM club_promotions WHERE id = ?", (promo_id,)
        ).fetchone()
    return row_to_dict(row) or {}


def update_club_promotion(
    promo_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    media_url: str | None = None,
    video_url: str | None = None,
    active: bool | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    sets: list[str] = []
    params: list[Any] = []
    if title is not None:
        sets.append("title = ?")
        params.append(title.strip())
    if description is not None:
        sets.append("description = ?")
        params.append(description)
    if media_url is not None:
        sets.append("media_url = ?")
        params.append(media_url)
    if video_url is not None:
        sets.append("video_url = ?")
        params.append(video_url)
    if active is not None:
        sets.append("active = ?")
        params.append(int(active))
    if not sets:
        raise ValueError("No club promotion fields to update")
    params.append(int(promo_id))
    with get_conn(path) as conn:
        cur = conn.execute(
            f"UPDATE club_promotions SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        if cur.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM club_promotions WHERE id = ?", (int(promo_id),)
        ).fetchone()
    return row_to_dict(row)


def list_club_promotions(
    *,
    active_only: bool = False,
    limit: int = 100,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    where = "WHERE active = 1" if active_only else ""
    with get_conn(path) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM club_promotions
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def log_ad_impression(
    *,
    ad_id: int,
    ad_source: str,
    user_id: int | None = None,
    surface: str = "web",
    path: Path | None = None,
) -> int:
    if ad_source not in AD_SOURCES:
        raise ValueError(f"Invalid ad_source; expected one of {sorted(AD_SOURCES)}")
    now = utc_now_iso()
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO ad_impressions (ad_id, ad_source, user_id, surface, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(ad_id), ad_source, user_id, surface, now),
        )
        return int(cur.lastrowid)


def active_story_inventory(*, path: Path | None = None) -> dict[str, Any]:
    """Premium + club creatives for story page slots."""
    banners = [
        a for a in list_premium_ads(active_only=True, path=path) if a["ad_type"] == "banner"
    ]
    posters = [
        a for a in list_premium_ads(active_only=True, path=path) if a["ad_type"] == "poster"
    ]
    videos = [
        a for a in list_premium_ads(active_only=True, path=path) if a["ad_type"] == "video"
    ]
    clubs = list_club_promotions(active_only=True, limit=5, path=path)
    return {
        "top_banner": banners[0] if banners else None,
        "mid_story": posters[0] if posters else (videos[0] if videos else None),
        "footer": banners[1] if len(banners) > 1 else (banners[0] if banners else None),
        "sidebar": clubs[0] if clubs else None,
        "club_promotions": clubs,
    }
