"""Frontend integration: Creator dashboard page + APIs."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_creator.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_creator_dashboard_page_renders(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        res = client.get("/creator/dashboard?id=1")
    assert res.status_code == 200
    assert b"creator-channels-root" in res.content
    assert b"creator-analytics-root" in res.content
    assert b"creator-hub.js" in res.content
    assert b'data-creator-id="1"' in res.content


def test_creator_apis_envelope(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        ch = client.get("/api/creator/99/channels")
        an = client.get("/api/creator/99/analytics")
    assert ch.status_code == 200
    assert an.status_code == 200
    ch_data = ch.json()
    an_data = an.json()
    for data in (ch_data, an_data):
        assert "ok" in data
        assert "platform" in data
        assert "lane" in data
        assert "items" in data
        assert "count" in data
        assert "meta" in data
    assert ch_data["reason"] == "not_linked"
    assert an_data["reason"] == "not_linked"
