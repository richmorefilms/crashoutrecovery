"""Monetization ad click → earnings update tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    db_path = tmp_path / "mon_click.db"
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
            ("earner1", "earn@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_ad_click_updates_earnings(mon_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(mon_db)
    from app import create_app

    with TestClient(create_app()) as client:
        ads = client.get("/api/monetization/ads").json()["items"]
        ad_id = ads[0]["id"]
        res = client.post(f"/api/monetization/ads/click/{ad_id}?creator_id={user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["earnings_updated"] is True
    assert data["meta"]["earnings_updated"] is True

    with TestClient(create_app()) as client:
        earn = client.get(f"/api/monetization/creator/{user_id}/earnings")
    assert earn.status_code == 200
    body = earn.json()
    assert body["ok"] is True
    summary = body["items"][0]
    assert summary["clicks"] >= 1
    assert summary["total_earnings"] > 0
