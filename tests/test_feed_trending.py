"""Unified GET /api/feed/trending tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def feed_db(tmp_path, monkeypatch):
    db_path = tmp_path / "feed_trending.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_feed_trending_returns_200(feed_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    monkeypatch.setattr("app.feed_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/trending")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "unified"
    assert data["lane"] == "trending"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert data["count"] >= 1
    assert data["meta"]["sources"] == ["youtube", "tiktok"]
    assert data["meta"]["sort"] == "engagement_score"
    scores = [i.get("engagement_score") or 0 for i in data["items"]]
    assert scores == sorted(scores, reverse=True)


def test_feed_trending_mocks_youtube_api(feed_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "items": [
                    {
                        "id": "trendVideo01",
                        "snippet": {
                            "title": "Trending recovery",
                            "channelTitle": "TrendChan",
                            "publishedAt": "2026-07-01T00:00:00Z",
                            "thumbnails": {"high": {"url": "https://example.com/t.jpg"}},
                        },
                        "statistics": {"viewCount": "99999", "likeCount": "100"},
                    }
                ]
            }

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.feed_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/trending")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "trending"
    assert any(i.get("id") == "trendVideo01" for i in data["items"])
