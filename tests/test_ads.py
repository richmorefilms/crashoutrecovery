"""Phase G: premium ads, club promotions, impressions."""

from __future__ import annotations

from app.ad_system import (
    create_club_promotion,
    create_premium_ad,
    create_story,
    list_club_promotions,
    list_premium_ads,
    log_ad_impression,
    update_club_promotion,
    update_premium_ad,
)
from app.db import get_user_version, init_db, open_connection


def test_schema_v6_to_v9_tables(tmp_path):
    db = tmp_path / "g.db"
    init_db(db)
    conn = open_connection(db)
    try:
        assert get_user_version(conn) == 15
        for table in ("stories", "premium_ads", "club_promotions", "ad_impressions"):
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            assert row is not None
        story_cols = {r[1] for r in conn.execute("PRAGMA table_info(stories)")}
        assert {"image_url", "video_url", "thumbnail_url"}.issubset(story_cols)
    finally:
        conn.close()


def test_premium_ads_crud(tmp_path):
    db = tmp_path / "ads.db"
    init_db(db)
    ad = create_premium_ad(
        ad_type="banner",
        media_url="https://cdn.example.com/banner.jpg",
        target_url="https://example.com/offer",
        path=db,
    )
    assert ad["id"]
    assert ad["active"] == 1
    updated = update_premium_ad(ad["id"], active=False, path=db)
    assert updated["active"] == 0
    assert list_premium_ads(active_only=True, path=db) == []
    assert len(list_premium_ads(active_only=False, path=db)) == 1


def test_club_promotions_and_impressions(tmp_path):
    db = tmp_path / "clubs.db"
    init_db(db)
    promo = create_club_promotion(
        title="Night Club",
        description="Calm room",
        media_url="https://cdn.example.com/club.jpg",
        path=db,
    )
    updated = update_club_promotion(promo["id"], title="Quiet Club", path=db)
    assert updated["title"] == "Quiet Club"
    assert list_club_promotions(active_only=True, path=db)[0]["id"] == promo["id"]

    impression_id = log_ad_impression(
        ad_id=promo["id"],
        ad_source="club",
        surface="story_page",
        path=db,
    )
    assert impression_id >= 1


def test_story_media_fields(tmp_path):
    db = tmp_path / "stories.db"
    init_db(db)
    story = create_story(
        title="Pause first",
        body="One small move.",
        image_url="https://cdn.example.com/a.jpg",
        video_url="https://cdn.example.com/a.mp4",
        thumbnail_url="https://cdn.example.com/a-thumb.jpg",
        published=True,
        path=db,
    )
    assert story["image_url"]
    assert story["video_url"]
    assert story["thumbnail_url"]
    assert story["published"] == 1
