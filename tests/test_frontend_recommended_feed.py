"""Frontend integration: /feed/recommended page."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_rec_feed.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_recommended_feed_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/feed/recommended?id=1")
        home = client.get("/")
        js = client.get("/static/recommended-feed.js")

    assert res.status_code == 200
    assert b"recommended-feed-root" in res.content
    assert b"recommended-feed.js" in res.content
    assert b"feed-page--recommended" in res.content
    assert home.status_code == 200
    assert b"/feed/recommended" in home.content
    assert js.status_code == 200
    assert b"/api/feed/all?recommended=" in js.content
