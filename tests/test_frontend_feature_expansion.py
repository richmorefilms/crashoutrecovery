"""Crashout Recovery 2.2 — Feature Expansion Pack pages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_expand.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_feature_expansion_pages(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        score = client.get("/growth/score?id=1")
        studio = client.get("/creator/studio")
        radar = client.get("/topics/radar")
        recovery = client.get("/recovery/mode")
        badges = client.get("/creator/badges")
        notes = client.get("/notifications")
        nav = client.get("/")

    assert score.status_code == 200
    assert b"growth-timeline-root" in score.content
    assert b"growth-score.js" in score.content

    assert studio.status_code == 200
    assert b"clip-studio-root" in studio.content
    assert b"clip-studio.js" in studio.content

    assert radar.status_code == 200
    assert b"opportunity-radar-root" in radar.content
    assert b"opportunity-radar.js" in radar.content

    assert recovery.status_code == 200
    assert b"recovery-mode-root" in recovery.content
    assert b"recovery-mode.js" in recovery.content

    assert badges.status_code == 200
    assert b"creator-badges-root" in badges.content
    assert b"creator-badges.js" in badges.content

    assert notes.status_code == 200
    assert b"notifications-root" in notes.content
    assert b"notifications.js" in notes.content

    assert nav.status_code == 200
    assert b"/creator/studio" in nav.content
    assert b"/topics/radar" in nav.content
    assert b"/recovery/mode" in nav.content
    assert b"/creator/badges" in nav.content
    assert b"/notifications" in nav.content
    assert b"nav-pulse" in nav.content
