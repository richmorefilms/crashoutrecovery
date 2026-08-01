"""Frontend Creator Home — Neon Welcome Console."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_creator_home.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_creator_home_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/creator/home")
        home = client.get("/")
    assert res.status_code == 200
    assert b"creator-home-root" in res.content
    assert b"creator-home.js" in res.content
    assert b"/feed/all" in res.content
    assert b"/creator/dashboard" in res.content
    assert home.status_code == 200
    assert b"/creator/home" in home.content
