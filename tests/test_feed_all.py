"""Unified GET /api/feed/all tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.feed_service import merge_items, normalize_unified, sort_items


@pytest.fixture()
def feed_db(tmp_path, monkeypatch):
    db_path = tmp_path / "feed_all.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_merge_and_sort_helpers():
    a = [{"id": "a", "platform": "youtube", "title": "A", "published_at": "2026-01-01T00:00:00Z"}]
    b = [{"id": "b", "platform": "tiktok", "title": "B", "published_at": "2026-07-01T00:00:00Z"}]
    merged = merge_items(a, b)
    assert len(merged) == 2
    sorted_items = sort_items(normalize_unified(merged), key="published_at")
    assert sorted_items[0]["id"] == "b"


def test_feed_all_returns_200_and_merges(feed_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    monkeypatch.setattr("app.feed_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/all")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "unified"
    assert data["lane"] == "all"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert data["count"] >= 2
    assert data["meta"]["sources"] == ["youtube", "tiktok"]
    assert data["meta"]["total_items"] == data["count"]
    platforms = {i.get("platform") for i in data["items"]}
    assert "youtube" in platforms
    assert "tiktok" in platforms
