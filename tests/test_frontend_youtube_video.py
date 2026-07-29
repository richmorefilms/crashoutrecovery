"""Frontend integration: YouTube video page + API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_yt_video.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_youtube_video_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/youtube/video/AbCdEfGhIjK")
    assert res.status_code == 200
    assert b"youtube-video-root" in res.content
    assert b"youtube-video.js" in res.content
    assert b"AbCdEfGhIjK" in res.content


def test_youtube_video_api_envelope(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "items": [
                    {
                        "id": "AbCdEfGhIjK",
                        "snippet": {
                            "title": "Pause first",
                            "description": "Safe move",
                            "channelTitle": "Calm",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {"high": {"url": "https://example.com/h.jpg"}},
                        },
                        "statistics": {
                            "viewCount": "10",
                            "likeCount": "1",
                            "commentCount": "0",
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/youtube/video/AbCdEfGhIjK")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["count"] == 1
    assert data["items"][0]["title"] == "Pause first"
