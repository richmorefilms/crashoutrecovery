"""GET /api/growth/{id}/trends envelope tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso


@pytest.fixture()
def growth_db(tmp_path, monkeypatch):
    db_path = tmp_path / "growth_trends.db"
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
            ("trender", "trender@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_growth_trends_envelope(growth_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    cid = _seed_user(growth_db)
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/growth/{cid}/trends")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "growth"
    assert isinstance(data["items"], list)
    assert data["count"] == 30
    assert data["count"] == len(data["items"])
    day = data["items"][0]
    for key in ("views", "likes", "comments", "earnings", "recommendations_served"):
        assert key in day
    assert "meta" in data
