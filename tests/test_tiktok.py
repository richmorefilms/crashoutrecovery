"""TikTok feed / share / auth wiring tests (no live TikTok calls)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_user_version, init_db, open_connection
from app.integrations.tiktok_share import build_share_payload
from app.integrations.tiktok_content import normalize_tiktok_video, CURATED_RECOVERY_FEED
from app.integrations import tiktok_auth as tt_auth
from app.social_auth import upsert_social_auth, get_social_auth, PROVIDER_TIKTOK


@pytest.fixture()
def tiktok_db(tmp_path, monkeypatch):
    db_path = tmp_path / "tiktok.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_schema_includes_user_social_auth(tiktok_db):
    conn = open_connection(tiktok_db)
    try:
        assert get_user_version(conn) == 10
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_social_auth'"
        ).fetchone()
        assert row is not None
        cols = {r[1] for r in conn.execute("PRAGMA table_info(user_social_auth)")}
        assert {
            "tiktok_user_id",
            "username",
            "expires_at",
            "access_token",
            "refresh_token",
            "avatar_url",
            "provider",
            "user_id",
        }.issubset(cols)
    finally:
        conn.close()


def test_normalize_tiktok_video():
    item = normalize_tiktok_video(
        {
            "id": "1234567890",
            "title": "Pause first",
            "username": "calmcreator",
            "cover_image_url": "https://example.com/c.jpg",
        },
        hashtag="recovery",
    )
    assert item["video_id"] == "1234567890"
    assert item["author"] == "@calmcreator"
    assert item["hashtag"] == "recovery"
    assert "embed/v2/1234567890" in (item["embed_url"] or "")


def test_share_payload_has_mobile_fields():
    payload = build_share_payload(
        video_url="https://cdn.example.com/a.mp4",
        caption="Draft don't delete",
        hashtags=["recovery", "motivation"],
    )
    assert payload["ok"] is True
    assert "#recovery" in payload["hashtags"]
    assert payload["share"]["web_upload_url"]
    assert payload["mobile"]["use_share_sheet"] is True
    assert "Draft" in payload["caption"]


def test_oauth_state_roundtrip(monkeypatch):
    monkeypatch.setattr("app.config.TIKTOK_CLIENT_SECRET", "test_secret")
    monkeypatch.setattr("app.config.TIKTOK_CLIENT_KEY", "test_key")
    state = tt_auth.make_oauth_state(user_id=42, mobile=True)
    parsed = tt_auth.parse_oauth_state(state)
    assert parsed["user_id"] == 42
    assert parsed["mobile"] is True


def test_feed_endpoint_returns_curated(tiktok_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/tiktok/feed")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "tiktok"
    assert data["count"] >= 1
    assert data["meta"]["mode"] == "curated"
    assert len(CURATED_RECOVERY_FEED) >= 1


def test_share_endpoint_json(tiktok_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.post(
            "/api/tiktok/share",
            json={
                "video_url": "https://example.com/v.mp4",
                "caption": "One small move",
                "hashtags": ["recovery"],
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["share"]["clipboard_text"]


def test_tiktok_login_unconfigured(tiktok_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr(tt_auth, "TIKTOK_CLIENT_KEY", "")
    monkeypatch.setattr("app.config.TIKTOK_CLIENT_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/auth/tiktok/login?format=json")
    assert res.status_code == 503


def test_upsert_social_auth(tiktok_db):
    import app.db as dbmod

    with dbmod.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (username, email, password_hash, tier, role, created_at, last_login)
            VALUES ('ttuser', 'tt@example.com', 'x', 'basic', 'user', '2026-01-01', '2026-01-01')
            """
        )
        user_id = int(conn.execute("SELECT id FROM users").fetchone()[0])

    row = upsert_social_auth(
        user_id,
        PROVIDER_TIKTOK,
        tiktok_user_id="oid123",
        username="TT Display",
        avatar_url="https://example.com/a.png",
        access_token="access",
        refresh_token="refresh",
        expires_at=9999999999,
        scopes="user.info.basic",
    )
    assert row["username"] == "TT Display"
    assert row["tiktok_user_id"] == "oid123"
    loaded = get_social_auth(user_id)
    assert loaded is not None
    assert loaded["access_token"] == "access"
    assert loaded["expires_at"] == 9999999999
