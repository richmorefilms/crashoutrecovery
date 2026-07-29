"""Personalized ranking tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso
from app.ranking_service import personalize_feed, upsert_preferences


@pytest.fixture()
def rank_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rank_personal.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _seed_user(db_path) -> int:
    conn = open_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, tier, role, created_at)
            VALUES (?, ?, ?, 'basic', 'user', ?)
            """,
            ("rankuser", "rank@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_personalize_boosts_preferred_platform(rank_db):
    user_id = _seed_user(rank_db)
    upsert_preferences(user_id, preferred_platforms=["tiktok"], preferred_channels=[])
    items = [
        {
            "id": "yt1",
            "platform": "youtube",
            "channel": "A",
            "views": 1000,
            "likes": 10,
            "comments": 1,
        },
        {
            "id": "tt1",
            "platform": "tiktok",
            "channel": "B",
            "views": 1000,
            "likes": 10,
            "comments": 1,
        },
    ]
    out = personalize_feed(user_id, items)
    assert out[0]["id"] == "tt1"
    assert out[0].get("personalization_boost", 0) > 0


def test_ranking_feed_user_endpoint(rank_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    user_id = _seed_user(rank_db)
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/ranking/feed/{user_id}")
        feed = client.get(f"/api/feed/all?personalized={user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "personalized"
    assert feed.status_code == 200
    assert feed.json()["lane"] == "personalized"
