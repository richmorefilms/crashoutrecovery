"""User preferences API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso
from app.ranking_service import upsert_preferences


@pytest.fixture()
def rank_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rank_prefs.db"
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
            ("prefuser", "pref@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_get_preferences_envelope(rank_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(rank_db)
    upsert_preferences(
        user_id,
        preferred_platforms=["youtube", "tiktok"],
        preferred_channels=["CalmCreator"],
    )
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/ranking/preferences/{user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "preferences"
    assert data["count"] == 1
    prefs = data["items"][0]
    assert "youtube" in prefs["preferred_platforms"]
    assert "CalmCreator" in prefs["preferred_channels"]
