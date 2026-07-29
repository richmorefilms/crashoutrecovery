"""GET /api/feed/all?recommended= must hit the feed API (not HTML pages)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso


@pytest.fixture()
def rec_feed_db(tmp_path, monkeypatch):
    db_path = tmp_path / "api_rec_feed.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _seed_user(db_path) -> int:
    conn = open_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, tier, role, created_at)
            VALUES (?, ?, ?, 'basic', 'user', ?)
            """,
            ("recfeed", "recfeed@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_api_feed_all_recommended_resolves_json(rec_feed_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    user_id = _seed_user(rec_feed_db)
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/feed/all?recommended={user_id}")
        page = client.get("/feed/all")
        rec_page = client.get(f"/feed/recommended?id={user_id}")

    assert res.status_code == 200
    assert "application/json" in (res.headers.get("content-type") or "")
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "unified"
    assert data["lane"] == "recommended"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert "meta" in data
    assert data["meta"].get("recommended") is True

    # Exact HTML pages must not shadow /api/feed/all
    assert page.status_code == 200
    assert "text/html" in (page.headers.get("content-type") or "")
    assert rec_page.status_code == 200
    assert "text/html" in (rec_page.headers.get("content-type") or "")


def test_api_feed_all_recommended_one_resolves(rec_feed_db, monkeypatch):
    """Regression: GET /api/feed/all?recommended=1 returns envelope, not HTML."""
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    _seed_user(rec_feed_db)
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/all?recommended=1")

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "recommended"
    assert b"<html" not in res.content.lower()
