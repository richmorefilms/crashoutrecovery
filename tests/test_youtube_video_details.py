"""YouTube video detail tests (mocked Data API — no live calls)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.youtube_service import get_video_details, normalize_video_details


@pytest.fixture()
def youtube_db(tmp_path, monkeypatch):
    db_path = tmp_path / "youtube_video.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _video_api_payload():
    return {
        "items": [
            {
                "id": "AbCdEfGhIjK",
                "snippet": {
                    "title": "Pause before the post",
                    "description": "One small recovery move.",
                    "channelTitle": "CalmCreator",
                    "publishedAt": "2026-01-15T12:00:00Z",
                    "thumbnails": {
                        "default": {"url": "https://example.com/d.jpg"},
                        "medium": {"url": "https://example.com/m.jpg"},
                        "high": {"url": "https://example.com/h.jpg"},
                    },
                },
                "statistics": {
                    "viewCount": "1200",
                    "likeCount": "45",
                    "commentCount": "8",
                },
            }
        ]
    }


def test_normalize_video_details():
    detail = normalize_video_details(_video_api_payload()["items"][0])
    assert detail["id"] == "AbCdEfGhIjK"
    assert detail["title"] == "Pause before the post"
    assert detail["description"].startswith("One small")
    assert detail["channel"] == "CalmCreator"
    assert detail["published_at"] == "2026-01-15T12:00:00Z"
    assert detail["thumbnails"]["high"] == "https://example.com/h.jpg"
    assert detail["statistics"]["view_count"] == 1200
    assert detail["statistics"]["like_count"] == 45


def test_get_video_details_mocks_api(monkeypatch):
    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return _video_api_payload()

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    detail = get_video_details("AbCdEfGhIjK")
    assert detail["id"] == "AbCdEfGhIjK"
    assert detail["statistics"]["comment_count"] == 8


def test_youtube_video_endpoint_returns_200(youtube_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return _video_api_payload()

    monkeypatch.setattr("app.config.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/video/AbCdEfGhIjK")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "youtube"
    assert data["count"] == 1
    assert isinstance(data["items"], list)
    item = data["items"][0]
    assert {
        "id",
        "title",
        "description",
        "channel",
        "published_at",
        "thumbnails",
        "statistics",
    } <= set(item.keys())
    assert data["meta"]["api_configured"] is True
    assert data["meta"]["video_id"] == "AbCdEfGhIjK"
