"""Frontend monetization pages + nav."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_mon.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_monetization_pages_render(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        lanes = client.get("/monetization")
        ads = client.get("/monetization/ads")
        earn = client.get("/earnings?id=1")
        home = client.get("/")
    assert lanes.status_code == 200
    assert b"monetization-lanes.js" in lanes.content
    assert ads.status_code == 200
    assert b"monetization-ads.js" in ads.content
    assert earn.status_code == 200
    assert b"creator-earnings.js" in earn.content
    assert home.status_code == 200
    assert b"/monetization" in home.content
    assert b"/earnings" in home.content
