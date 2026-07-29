"""Monetization ads inventory API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_user_version, init_db, open_connection


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    db_path = tmp_path / "mon_ads.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_schema_v12_monetization(mon_db):
    conn = open_connection(mon_db)
    try:
        assert get_user_version(conn) == 15
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"ad_inventory", "ad_clicks", "creator_earnings"} <= tables
    finally:
        conn.close()


def test_monetization_ads_envelope(mon_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/monetization/ads")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "ads"
    assert isinstance(data["items"], list)
    assert data["count"] >= 1
    item = data["items"][0]
    assert {"id", "title", "image", "cta", "payout_per_click"} <= set(item.keys())
