"""Topic graph API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.recommendation_service import build_topic_graph


@pytest.fixture()
def rec_db(tmp_path, monkeypatch):
    db_path = tmp_path / "rec_graph.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_build_topic_graph_adjacency():
    items = [
        {"id": "1", "title": "recovery motivation pause"},
        {"id": "2", "title": "recovery calm draft"},
    ]
    graph = build_topic_graph(items)
    assert "recovery" in graph
    assert isinstance(graph["recovery"], dict)
    assert "motivation" in graph["recovery"] or "calm" in graph["recovery"]


def test_graph_endpoint(rec_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/api/recommendations/graph")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "topic_graph"
    assert "adjacency" in data["meta"]
    assert isinstance(data["items"], list)
