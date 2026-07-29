"""YouTube search endpoint tests (mocked Data API — no live calls)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.youtube_service import search_youtube


@pytest.fixture()
def youtube_db(tmp_path, monkeypatch):
    db_path = tmp_path / "youtube_search.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _search_api_payload():
    return {
        "items": [
            {
                "id": {"videoId": "LmNoPqRsTuV"},
                "snippet": {
                    "title": "Recovery search hit",
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
                    "title": "Second recovery clip",
                    "channelTitle": "DemoChannel",
                    "publishedAt": "2026-07-21T08:00:00Z",
                    "thumbnails": {
                        "medium": {"url": "https://example.com/m.jpg"},
                    },
                },
            },
        ]
    }


def test_search_youtube_mocks_api(monkeypatch):
    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return _search_api_payload()

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    items = search_youtube("recovery")
    assert len(items) == 2
    assert items[0]["id"] == "LmNoPqRsTuV"
    assert {"id", "title", "thumbnail", "channel", "published_at"} <= set(items[0].keys())


def test_youtube_search_endpoint_returns_200(youtube_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return _search_api_payload()

    monkeypatch.setattr("app.config.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/search?q=recovery")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "youtube"
    assert data["title"] == "YouTube Search"
    assert isinstance(data["items"], list)
    assert data["count"] == 2
    assert data["count"] == len(data["items"])
    assert data["items"][0]["title"] == "Recovery search hit"
    assert data["meta"]["mode"] == "live"
    assert data["meta"]["query"] == "recovery"
    assert data["meta"]["api_configured"] is True


def test_youtube_search_requires_query(youtube_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/search")
    assert res.status_code == 400
