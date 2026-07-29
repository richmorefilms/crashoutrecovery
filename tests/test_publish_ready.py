"""Publish readiness page — CrashoutRecovery v16."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_publish.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_publish_ready_page(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/publish")
        home = client.get("/")
        js = client.get("/static/publish.js")
    assert res.status_code == 200
    assert b"publish-ready-root" in res.content
    assert b"CrashoutRecovery v16" in res.content
    assert b"publish-checklist" in res.content
    assert b"Routing stable" in res.content
    assert b"Growth engine stable" in res.content
    assert home.status_code == 200
    assert b"/publish" in home.content
    assert js.status_code == 200
    assert b"v16" in js.content
