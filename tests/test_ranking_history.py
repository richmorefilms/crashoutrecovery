"""User history tracking tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_user_version, init_db, open_connection, utc_now_iso


@pytest.fixture()
def rank_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rank_history.db"
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
            ("histuser", "hist@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_schema_v13_ranking(rank_db):
    conn = open_connection(rank_db)
    try:
        assert get_user_version(conn) == 15
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "user_history" in tables
        assert "user_preferences" in tables
    finally:
        conn.close()


def test_post_ranking_history(rank_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    user_id = _seed_user(rank_db)
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.post(
            "/api/ranking/history",
            json={"user_id": user_id, "item_id": "vid_1", "platform": "youtube"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "history"
    assert data["meta"]["item_id"] == "vid_1"

    conn = open_connection(rank_db)
    try:
        row = conn.execute(
            "SELECT item_id, platform FROM user_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        assert row is not None
        assert row["item_id"] == "vid_1"
    finally:
        conn.close()
