"""Creator channels API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso
from app.oauth_service import store_tokens


@pytest.fixture()
def creator_db(tmp_path, monkeypatch):
    db_path = tmp_path / "creator_channels.db"
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
            ("creator1", "c1@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_creator_channels_not_linked(creator_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/creator/99/channels")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["reason"] == "not_linked"
    assert data["platform"] == "youtube"
    assert data["lane"] == "creator"
    assert data["items"] == []
    assert data["count"] == 0


def test_creator_channels_linked_mocks_api(creator_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(creator_db)
    store_tokens(
        user_id,
        {"access_token": "ya29.x", "refresh_token": "r", "expires_in": 3600},
    )

    class _FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "items": [
                    {
                        "id": "UCxxxxxxxxxxxxxxxxxxxxxx",
                        "snippet": {
                            "title": "My Channel",
                            "description": "Recovery creator",
                            "thumbnails": {
                                "high": {"url": "https://example.com/c.jpg"},
                            },
                        },
                        "statistics": {
                            "subscriberCount": "10",
                            "videoCount": "3",
                            "viewCount": "100",
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.creator_service.requests.get", lambda *a, **k: _FakeResp())
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/creator/{user_id}/channels")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "youtube"
    assert data["lane"] == "creator"
    assert data["count"] == 1
    assert data["items"][0]["title"] == "My Channel"
    assert data["meta"]["linked"] is True
