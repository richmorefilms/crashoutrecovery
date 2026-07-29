"""GET /api/multi/pinterest envelope tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def multi_db(tmp_path, monkeypatch):
    db_path = tmp_path / "multi_pin.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_multiplaform_pinterest_envelope(multi_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/multi/pinterest")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "pinterest"
    assert data["lane"] == "multiplatform"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert "meta" in data
