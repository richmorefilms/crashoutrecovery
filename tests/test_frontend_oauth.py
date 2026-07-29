"""Frontend integration: OAuth YouTube pages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_oauth.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_oauth_login_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/oauth/youtube")
    assert res.status_code == 200
    assert b"/api/oauth/youtube/login" in res.content
    assert b"oauth-youtube.js" in res.content


def test_oauth_callback_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/oauth/youtube/callback")
    assert res.status_code == 200
    assert b"oauth-youtube-status" in res.content
    assert b"oauth-youtube.js" in res.content


def test_base_nav_includes_oauth_link(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/")
    assert res.status_code == 200
    assert b"/oauth/youtube" in res.content
    assert b"/feed/all" in res.content
    assert b"/feed/trending" in res.content
    assert b"/creator/dashboard" in res.content
