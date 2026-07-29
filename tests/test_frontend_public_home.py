"""Frontend public landing page."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_public.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_public_home(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/public")
        home = client.get("/")
        js = client.get("/static/home-public.js")
    assert res.status_code == 200
    assert b"public-home-root" in res.content
    assert b"home-public.js" in res.content
    assert b"v16-hero" in res.content
    assert home.status_code == 200
    assert b"/public" in home.content
    assert js.status_code == 200
