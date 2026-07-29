"""Frontend redesigned creator dashboard."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_new_creator.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_new_creator_dashboard(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        dash = client.get("/creator/dashboard?id=1")
        earnings = client.get("/earnings?id=1")
        hub_js = client.get("/static/creator-hub.js")
    assert dash.status_code == 200
    assert b"creator-growth-dial" in dash.content
    assert b"creator-opportunities-root" in dash.content
    assert earnings.status_code == 200
    assert b"creator-earnings-chart" in earnings.content
    assert hub_js.status_code == 200
    assert b"/api/growth/" in hub_js.content
