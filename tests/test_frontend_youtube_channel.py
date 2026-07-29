"""Frontend integration: YouTube channel page + API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db

CHANNEL_ID = "UCxxxxxxxxxxxxxxxxxxxxxx"


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_yt_channel.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_youtube_channel_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/youtube/channel/{CHANNEL_ID}")
    assert res.status_code == 200
    assert b"youtube-channel-root" in res.content
    assert b"youtube-channel.js" in res.content
    assert CHANNEL_ID.encode() in res.content


def test_youtube_channel_api_envelope(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "items": [
                    {
                        "id": CHANNEL_ID,
                        "snippet": {
                            "title": "Crashout Recovery",
                            "description": "Adults 18+",
                            "thumbnails": {"high": {"url": "https://example.com/c.jpg"}},
                        },
                        "statistics": {
                            "subscriberCount": "1",
                            "videoCount": "2",
                            "viewCount": "3",
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr("app.youtube_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/youtube/channel/{CHANNEL_ID}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["items"][0]["id"] == CHANNEL_ID
