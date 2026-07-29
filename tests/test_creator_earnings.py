"""Creator earnings + monetization + payout tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso
from app.monetization_service import record_ad_click


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    db_path = tmp_path / "creator_earn.db"
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
            ("earner2", "earn2@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_creator_earnings_envelope(mon_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(mon_db)
    from app import create_app

    with TestClient(create_app()) as client:
        ads = client.get("/api/monetization/ads").json()["items"]
        record_ad_click(ads[0]["id"], user_id)
        res = client.get(f"/api/creator/{user_id}/earnings")
        mon = client.get(f"/api/creator/{user_id}/monetization")
        pay = client.post(f"/api/creator/{user_id}/payout")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "earnings"
    assert {"total_earnings", "clicks", "rpm", "last_payout"} <= set(data["items"][0].keys())

    assert mon.status_code == 200
    m = mon.json()
    assert m["ok"] is True
    assert {"earnings", "clicks", "rpm", "ads_served"} <= set(m["items"][0].keys())

    assert pay.status_code == 200
    p = pay.json()
    assert p["ok"] is True
    assert p["payout_processed"] is True
