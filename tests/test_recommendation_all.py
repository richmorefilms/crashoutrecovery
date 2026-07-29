"""Combined recommendations + feed ?recommended= tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso


@pytest.fixture()
def rec_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rec_all.db"
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
            ("recall", "recall@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_recommendations_all_envelope(rec_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    user_id = _seed_user(rec_db)
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/recommendations/all/{user_id}")
        feed = client.get(f"/api/feed/all?recommended={user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "recommendations"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert "top_topics" in data["meta"]

    assert feed.status_code == 200
    f = feed.json()
    assert f["ok"] is True
    assert f["lane"] == "recommended"
    assert f["meta"].get("recommended") is True
