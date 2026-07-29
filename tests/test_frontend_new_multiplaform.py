"""Frontend multi-platform viewer pages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_new_multi.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_new_multiplaform(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        ig = client.get("/multi/instagram")
        fb = client.get("/multi/facebook")
        tw = client.get("/multi/twitter")
        pin = client.get("/multi/pinterest")
        home = client.get("/")
        js = client.get("/static/multi-instagram.js")
    assert ig.status_code == 200
    assert b"multi-instagram-root" in ig.content
    assert fb.status_code == 200
    assert b"multi-facebook-root" in fb.content
    assert tw.status_code == 200
    assert pin.status_code == 200
    assert home.status_code == 200
    assert b"/multi/instagram" in home.content
    assert js.status_code == 200
    assert b"/api/multi/instagram" in js.content
    assert b"norm-badge" in js.content
