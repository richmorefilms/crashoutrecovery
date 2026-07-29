"""Frontend redesigned growth console."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_new_growth.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_frontend_new_growth_console(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        score = client.get("/growth/score?id=1")
        trends = client.get("/growth/trends?id=1")
        opp = client.get("/growth/opportunities?id=1")
        score_js = client.get("/static/growth-score.js")
    assert score.status_code == 200
    assert b"growth-score-root" in score.content
    assert b"growth-console" in score.content
    assert trends.status_code == 200
    assert b"growth-trends-chart" in trends.content
    assert opp.status_code == 200
    assert b"v16-showcase" in opp.content
    assert score_js.status_code == 200
    assert b"v16-dial" in score_js.content
