"""Monetization lanes API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    db_path = tmp_path / "mon_lanes.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_monetization_lanes_envelope(mon_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/monetization/lanes")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "monetization"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    ids = {i["id"] for i in data["items"]}
    assert {"ads", "creator_payouts", "sponsorships", "premium_feed"} <= ids
