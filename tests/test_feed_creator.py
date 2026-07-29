"""Unified GET /api/feed/creator/{id} tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def feed_db(tmp_path, monkeypatch):
    db_path = tmp_path / "feed_creator.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_feed_creator_returns_placeholder_envelope(feed_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/creator/42")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["platform"] == "unified"
    assert data["lane"] == "creator"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    assert data["count"] >= 1
    assert data["meta"]["creator_id"] == "42"
    assert data["meta"]["mode"] == "placeholder"
    assert data["meta"]["sources"] == ["youtube", "tiktok"]
