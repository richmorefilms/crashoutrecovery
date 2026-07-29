"""Frontend integration: YouTube search page + API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_yt_search.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_youtube_search_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/youtube/search?q=recovery")
    assert res.status_code == 200
    assert b"youtube-search-root" in res.content
    assert b"youtube-search.js" in res.content
    assert b'value="recovery"' in res.content or b"recovery" in res.content


def test_youtube_search_api_envelope(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "items": [
                    {
                        "id": {"videoId": "LmNoPqRsTuV"},
                        "snippet": {
                            "title": "Recovery hit",
                            "channelTitle": "Demo",
                            "publishedAt": "2026-07-01T00:00:00Z",
                            "thumbnails": {"high": {"url": "https://example.com/h.jpg"}},
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/search?q=recovery")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "youtube" or data.get("title")
    assert isinstance(data["items"], list)
    assert data["count"] >= 1
