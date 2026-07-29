"""Frontend redesigned staff console."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_new_staff.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_new_staff_console(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        overview = client.get("/staff/overview")
        flags = client.get("/staff/flags")
        overview_js = client.get("/static/staff-overview.js")
        flags_js = client.get("/static/staff-flags.js")
    assert overview.status_code == 200
    assert b"staff-health-chart" in overview.content
    assert b"staff-fraud-panel" in overview.content
    assert b"staff-rate-panel" in overview.content
    assert flags.status_code == 200
    assert b"staff-flags-root" in flags.content
    assert overview_js.status_code == 200
    assert flags_js.status_code == 200
    assert b"staff-table" in flags_js.content
