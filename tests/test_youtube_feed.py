"""YouTube recovery feed tests (mocked Data API — no live calls)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.youtube_service import (
    CURATED_YOUTUBE_FEED,
    fetch_youtube_feed,
    normalize_youtube_video,
)


@pytest.fixture()
def youtube_db(tmp_path, monkeypatch):
    db_path = tmp_path / "youtube.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_normalize_youtube_video():
    item = normalize_youtube_video(
        {
            "id": {"videoId": "abcdefghijk"},
            "snippet": {
                "title": "Pause first",
                "channelTitle": "CalmCreator",
                "publishedAt": "2026-01-15T12:00:00Z",
                "thumbnails": {
                    "high": {"url": "https://example.com/thumb.jpg"},
                },
            },
        }
    )
    assert item["id"] == "abcdefghijk"
    assert item["title"] == "Pause first"
    assert item["channel"] == "CalmCreator"
    assert item["thumbnail"] == "https://example.com/thumb.jpg"
    assert item["published_at"] == "2026-01-15T12:00:00Z"


def test_fetch_youtube_feed_curated_without_key(monkeypatch):
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    items = fetch_youtube_feed()
    assert isinstance(items, list)
    assert len(items) == len(CURATED_YOUTUBE_FEED)
    assert {"id", "title", "thumbnail", "channel", "published_at"} <= set(items[0].keys())


def test_fetch_youtube_feed_mocks_api(monkeypatch):
    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "items": [
                    {
                        "id": {"videoId": "AbCdEfGhIjK"},
                        "snippet": {
                            "title": "Recovery clip",
                            "channelTitle": "SafeMoves",
                            "publishedAt": "2026-07-01T00:00:00Z",
                            "thumbnails": {
                                "medium": {"url": "https://i.ytimg.com/vi/AbCdEfGhIjK/mqdefault.jpg"},
                            },
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    items = fetch_youtube_feed(query="recovery")
    assert len(items) == 1
    assert items[0]["id"] == "AbCdEfGhIjK"
    assert items[0]["channel"] == "SafeMoves"


def test_youtube_feed_endpoint_returns_200(youtube_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/feed")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert data["count"] >= 1
    assert data["meta"]["mode"] == "curated"


def test_youtube_feed_endpoint_mocked_live(youtube_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "items": [
                    {
                        "id": {"videoId": "LmNoPqRsTuV"},
                        "snippet": {
                            "title": "Live recovery search",
                            "channelTitle": "DemoChannel",
                            "publishedAt": "2026-07-20T08:00:00Z",
                            "thumbnails": {
                                "high": {"url": "https://example.com/h.jpg"},
                            },
                        },
                    },
                    {
                        "id": {"videoId": "VwXyZaBcDeF"},
                        "snippet": {
                            "title": "Second clip",
                            "channelTitle": "DemoChannel",
                            "publishedAt": "2026-07-21T08:00:00Z",
                            "thumbnails": {},
                        },
                    },
                ]
            }

    monkeypatch.setattr("app.config.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/feed?q=recovery")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "Live recovery search"
    assert data["meta"]["mode"] == "live"
    assert data["meta"]["api_configured"] is True
