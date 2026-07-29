"""Engagement score unit + API tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.ranking_service import score_feed, score_item


@pytest.fixture()
def rank_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rank_score.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_score_item_range_and_ordering():
    fresh = {
        "views": 10000,
        "likes": 800,
        "comments": 100,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "platform": "tiktok",
    }
    stale = {
        "views": 10000,
        "likes": 800,
        "comments": 100,
        "published_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        "platform": "tiktok",
    }
    s_fresh = score_item(fresh)
    s_stale = score_item(stale)
    assert 0 <= s_fresh <= 100
    assert 0 <= s_stale <= 100
    assert s_fresh > s_stale


def test_score_feed_sorted_desc():
    items = [
        {"id": "a", "views": 100, "likes": 1, "comments": 0, "platform": "youtube"},
        {
            "id": "b",
            "views": 50000,
            "likes": 4000,
            "comments": 500,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "platform": "tiktok",
        },
    ]
    scored = score_feed(items)
    assert scored[0]["id"] == "b"
    assert scored[0]["engagement_score"] >= scored[1]["engagement_score"]


def test_ranking_score_endpoint(rank_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/ranking/score")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "ranking"
    assert data["count"] == 1
    assert 0 <= data["items"][0]["engagement_score"] <= 100
