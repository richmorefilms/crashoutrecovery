"""Topic extraction + clusters API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_user_version, init_db, open_connection
from app.recommendation_service import cluster_items_by_topic, extract_topics


@pytest.fixture()
def rec_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rec_topics.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_extract_topics_keywords():
    topics = extract_topics(
        {"title": "One small recovery move", "description": "Pause before the post #motivation"}
    )
    assert "recovery" in topics
    assert "motivation" in topics


def test_cluster_items_by_topic():
    items = [
        {"id": "1", "title": "Recovery calm draft"},
        {"id": "2", "title": "Motivation momentum"},
        {"id": "3", "title": "Recovery again"},
    ]
    clusters = cluster_items_by_topic(items)
    assert "recovery" in clusters
    assert len(clusters["recovery"]) >= 2


def test_topics_endpoint(rec_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/recommendations/topics")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "topics"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])


def test_schema_v14(rec_db):
    conn = open_connection(rec_db)
    try:
        assert get_user_version(conn) == 15
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "topic_cache" in tables
        assert "user_similarity" in tables
    finally:
        conn.close()
