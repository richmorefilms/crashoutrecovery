"""YouTube OAuth foundation tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_user_version, init_db, open_connection, utc_now_iso
from app.oauth_service import (
    build_google_oauth_url,
    build_oauth_linked_response,
    exchange_code_for_tokens,
    store_tokens,
)


@pytest.fixture()
def oauth_db(tmp_path, monkeypatch):
    db_path = tmp_path / "oauth.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _seed_user(db_path) -> int:
    conn = open_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, tier, role, created_at)
            VALUES (?, ?, ?, 'basic', 'user', ?)
            """,
            ("oauth_user", "oauth@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_schema_has_youtube_tokens(oauth_db):
    conn = open_connection(oauth_db)
    try:
        assert get_user_version(conn) == 15
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='youtube_tokens'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_build_google_oauth_url(monkeypatch):
    monkeypatch.setattr("app.oauth_service.OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr("app.oauth_service.OAUTH_REDIRECT_URI", "http://localhost/cb")
    url = build_google_oauth_url(state="7")
    assert "accounts.google.com" in url
    assert "client_id=cid" in url
    assert "state=7" in url


def test_exchange_and_store_tokens(oauth_db, monkeypatch):
    user_id = _seed_user(oauth_db)

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "access_token": "ya29.access",
                "refresh_token": "1//refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            }

    monkeypatch.setattr("app.oauth_service.OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr("app.oauth_service.OAUTH_CLIENT_SECRET", "sec")
    monkeypatch.setattr("app.oauth_service.OAUTH_REDIRECT_URI", "http://localhost/cb")
    monkeypatch.setattr("app.oauth_service.requests.post", lambda *a, **k: _FakeResp())

    tokens = exchange_code_for_tokens("auth-code")
    row = store_tokens(user_id, tokens)
    assert row["access_token"] == "ya29.access"
    assert row["user_id"] == user_id


def test_oauth_callback_endpoint(oauth_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(oauth_db)

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "access_token": "ya29.access",
                "refresh_token": "1//refresh",
                "expires_in": 3600,
            }

    monkeypatch.setattr("app.oauth_service.OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr("app.oauth_service.OAUTH_CLIENT_SECRET", "sec")
    monkeypatch.setattr("app.oauth_service.OAUTH_REDIRECT_URI", "http://localhost/cb")
    monkeypatch.setattr("app.config.OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr("app.config.OAUTH_CLIENT_SECRET", "sec")
    monkeypatch.setattr("app.oauth_service.requests.post", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/oauth/youtube/callback?code=abc&state={user_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "oauth"
    assert data["meta"]["linked"] is True
    assert data["meta"]["user_id"] == user_id


def test_oauth_login_redirect(oauth_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.oauth_service.OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr("app.oauth_service.OAUTH_REDIRECT_URI", "http://localhost/cb")
    monkeypatch.setattr("app.config.OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr("app.config.OAUTH_REDIRECT_URI", "http://localhost/cb")
    from app import create_app

    with TestClient(create_app(), follow_redirects=False) as client:
        res = client.get("/api/oauth/youtube/login?state=1")
    assert res.status_code in (302, 307)
    assert "accounts.google.com" in (res.headers.get("location") or "")


def test_oauth_linked_envelope_shape():
    data = build_oauth_linked_response(user_id=9)
    assert {"ok", "platform", "lane", "title", "items", "count", "meta"} <= set(data.keys())
