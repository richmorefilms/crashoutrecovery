"""Frontend redesigned recommendations explorer."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_new_recs.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_new_recommendations(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        recs = client.get("/recommendations?id=1")
        clusters = client.get("/topics")
        graph = client.get("/topic-graph")
    assert recs.status_code == 200
    assert b"recs-explorer" in recs.content
    assert b"recommendations-root" in recs.content
    assert clusters.status_code == 200
    assert b"topic-clusters-root" in clusters.content
    assert b"v16-showcase" in clusters.content
    assert graph.status_code == 200
    assert b"topic-graph-root" in graph.content
    assert b"topic-graph-list" in graph.content
