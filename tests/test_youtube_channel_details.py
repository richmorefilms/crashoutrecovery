"""YouTube channel detail tests (mocked Data API — no live calls)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.youtube_service import get_channel_details, normalize_channel_details


@pytest.fixture()
def youtube_db(tmp_path, monkeypatch):
    db_path = tmp_path / "youtube_channel.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


CHANNEL_ID = "UCxxxxxxxxxxxxxxxxxxxxxx"


def _channel_api_payload():
    return {
        "items": [
            {
                "id": CHANNEL_ID,
                "snippet": {
                    "title": "Crashout Recovery",
                    "description": "Adults 18+ recovery redirects.",
                    "thumbnails": {
                        "default": {"url": "https://example.com/c-d.jpg"},
                        "medium": {"url": "https://example.com/c-m.jpg"},
                        "high": {"url": "https://example.com/c-h.jpg"},
                    },
                },
                "statistics": {
                    "subscriberCount": "9001",
                    "videoCount": "42",
                    "viewCount": "100000",
                },
            }
        ]
    }


def test_normalize_channel_details():
    detail = normalize_channel_details(_channel_api_payload()["items"][0])
    assert detail["id"] == CHANNEL_ID
    assert detail["title"] == "Crashout Recovery"
    assert "Adults 18+" in detail["description"]
    assert detail["thumbnails"]["medium"] == "https://example.com/c-m.jpg"
    assert detail["statistics"]["subscriber_count"] == 9001
    assert detail["statistics"]["video_count"] == 42
    assert detail["statistics"]["view_count"] == 100000


def test_get_channel_details_mocks_api(monkeypatch):
    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return _channel_api_payload()

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    detail = get_channel_details(CHANNEL_ID)
    assert detail["id"] == CHANNEL_ID
    assert detail["title"] == "Crashout Recovery"


def test_youtube_channel_endpoint_returns_200(youtube_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return _channel_api_payload()

    monkeypatch.setattr("app.config.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/youtube/channel/{CHANNEL_ID}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "youtube"
    assert data["count"] == 1
    assert isinstance(data["items"], list)
    item = data["items"][0]
    assert {"id", "title", "description", "thumbnails", "statistics"} <= set(item.keys())
    assert data["meta"]["api_configured"] is True
    assert data["meta"]["channel_id"] == CHANNEL_ID
