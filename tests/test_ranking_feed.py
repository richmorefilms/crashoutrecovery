"""Ranked unified feed tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def rank_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rank_feed.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_feed_all_ranked(rank_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    monkeypatch.setattr("app.feed_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/feed/all?ranked=true")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "ranked"
    assert data["meta"]["ranked"] is True
    assert isinstance(data["items"], list)
    scores = [i.get("engagement_score") or 0 for i in data["items"]]
    assert scores == sorted(scores, reverse=True)
