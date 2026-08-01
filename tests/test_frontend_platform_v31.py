"""Crashout Recovery 3.1 — expansion map pages + public API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_v31.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_expansion_map_pages(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        signals = client.get("/feed/signals")
        rooms = client.get("/rooms")
        studio_pro = client.get("/creator/studio/pro")
        journal = client.get("/recovery/journal")
        sync = client.get("/sync")
        developer = client.get("/developer/api")
        nav = client.get("/")

    assert signals.status_code == 200
    assert b"feed-signals-root" in signals.content
    assert b"feed-signals.js" in signals.content

    assert rooms.status_code == 200
    assert b"rooms-root" in rooms.content
    assert b"creator-rooms.js" in rooms.content

    assert studio_pro.status_code == 200
    assert b"studio-pro-root" in studio_pro.content
    assert b"clip-studio-pro.js" in studio_pro.content

    assert journal.status_code == 200
    assert b"recovery-journal-root" in journal.content
    assert b"recovery-journal.js" in journal.content

    assert sync.status_code == 200
    assert b"sync-root" in sync.content
    assert b"creator-sync.js" in sync.content

    assert developer.status_code == 200
    assert b"developer-api-root" in developer.content
    assert b"developer-api.js" in developer.content

    assert nav.status_code == 200
    for path in (
        b"/feed/signals",
        b"/rooms",
        b"/creator/studio/pro",
        b"/recovery/journal",
        b"/sync",
        b"/developer/api",
    ):
        assert path in nav.content
    assert b"creator-pulse" in nav.content


def test_public_developer_api(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        signals = client.get("/api/public/feed/signals")
        topics = client.get("/api/public/topics")
        momentum = client.get("/api/public/momentum?creator_id=1")
        vault = client.get("/api/public/vault/meta")

    assert signals.status_code == 200
    body = signals.json()
    assert body.get("ok") is True
    assert body.get("lane") == "public_signals"
    assert isinstance(body.get("items"), list)
    assert len(body["items"]) >= 1

    assert topics.status_code == 200
    assert topics.json()

    assert momentum.status_code == 200
    assert momentum.json()

    assert vault.status_code == 200
    vault_body = vault.json()
    assert vault_body.get("ok") is True
    assert vault_body.get("lane") == "vault_meta"
