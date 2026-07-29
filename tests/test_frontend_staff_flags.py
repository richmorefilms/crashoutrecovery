"""Frontend staff flags page."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_staff_flags.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_staff_flags_page(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/staff/flags")
        home = client.get("/")
    assert res.status_code == 200
    assert b"staff-flags-root" in res.content
    assert b"staff-flags.js" in res.content
    assert home.status_code == 200
    assert b"staff_overview" in home.content or b"/staff/overview" in home.content
