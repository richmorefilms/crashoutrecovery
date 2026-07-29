"""Frontend redesigned feed pages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_new_feed.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_new_feed_pages(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        all_page = client.get("/feed/all")
        trending = client.get("/feed/trending")
        recommended = client.get("/feed/recommended?id=1")
        feed_js = client.get("/static/feed-all.js")
    assert all_page.status_code == 200
    assert b"feed-all-root" in all_page.content
    assert b"feed-page--v16" in all_page.content
    assert trending.status_code == 200
    assert b"feed-trending-root" in trending.content
    assert recommended.status_code == 200
    assert b"recommended-feed-root" in recommended.content
    assert feed_js.status_code == 200
    assert b"max_results" in feed_js.content
    assert b"score-badge" in feed_js.content
