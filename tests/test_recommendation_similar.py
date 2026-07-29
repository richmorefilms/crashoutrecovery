"""Collaborative filtering / similar users tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, open_connection, utc_now_iso
from app.ranking_service import record_history
from app.recommendation_service import compute_similarity, recommend_from_similar_users


@pytest.fixture()
def rec_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rec_similar.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _seed_user(db_path, username: str) -> int:
    conn = open_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, tier, role, created_at)
            VALUES (?, ?, ?, 'basic', 'user', ?)
            """,
            (username, f"{username}@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_jaccard_similarity():
    assert compute_similarity({"a", "b"}, {"b", "c"}) == 0.3333
    assert compute_similarity({"a"}, {"a"}) == 1.0
    assert compute_similarity(set(), {"a"}) == 0.0


def test_recommend_from_similar_users(rec_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    u1 = _seed_user(rec_db, "u1")
    u2 = _seed_user(rec_db, "u2")
    record_history(u1, "shared_1", "youtube")
    record_history(u1, "only_u1", "youtube")
    record_history(u2, "shared_1", "youtube")
    record_history(u2, "rec_for_u1", "tiktok")
    items = recommend_from_similar_users(u1, limit=10)
    ids = {i["id"] for i in items}
    assert "rec_for_u1" in ids
    assert "only_u1" not in ids


def test_similar_endpoint(rec_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    u1 = _seed_user(rec_db, "su1")
    u2 = _seed_user(rec_db, "su2")
    record_history(u1, "x1", "youtube")
    record_history(u2, "x1", "youtube")
    record_history(u2, "y2", "tiktok")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get(f"/api/recommendations/similar/{u1}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "similar"
    assert isinstance(data["items"], list)
