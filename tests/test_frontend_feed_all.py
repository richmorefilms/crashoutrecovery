"""Frontend integration: /feed/all page + /api/feed/all envelope."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_feed_all.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_feed_all_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/feed/all")
    assert res.status_code == 200
    assert b"feed-all-root" in res.content
    assert b"feed-all.js" in res.content
    assert b"Unified Feed" in res.content or b"unified_feed" in res.content


def test_feed_all_api_envelope(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/all")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "unified"
    assert data["lane"] == "all"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert "meta" in data
