"""Creator analytics API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso
from app.oauth_service import store_tokens


@pytest.fixture()
def creator_db(tmp_path, monkeypatch):
    db_path = tmp_path / "creator_analytics.db"
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
            ("creator2", "c2@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_creator_analytics_not_linked(creator_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/creator/99/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["reason"] == "not_linked"
    assert data["platform"] == "youtube"
    assert data["lane"] == "analytics"
    assert {"ok", "platform", "lane", "title", "items", "count", "meta"} <= set(data.keys())


def test_creator_analytics_placeholder_when_linked(creator_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(creator_db)
    store_tokens(user_id, {"access_token": "ya29.x", "expires_in": 3600})
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/creator/{user_id}/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "analytics"
    assert data["count"] == 1
    assert data["items"][0]["mode"] == "placeholder"
    assert data["meta"]["linked"] is True
    assert data["meta"]["mode"] == "placeholder"
