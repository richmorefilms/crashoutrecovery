"""Crashout Recovery 3.0 — platform evolution pages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_v3.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_platform_evolution_pages(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        economy = client.get("/economy?id=1")
        identity = client.get("/creator/profile?id=1")
        social = client.get("/social")
        challenges = client.get("/challenges")
        assistant = client.get("/assistant")
        vault = client.get("/vault")
        nav = client.get("/")

    assert economy.status_code == 200
    assert b"economy-root" in economy.content
    assert b"creator-economy.js" in economy.content

    assert identity.status_code == 200
    assert b"creator-identity-root" in identity.content
    assert b"creator-identity.js" in identity.content

    assert social.status_code == 200
    assert b"social-root" in social.content
    assert b"social-layer.js" in social.content

    assert challenges.status_code == 200
    assert b"challenges-root" in challenges.content
    assert b"creator-challenges.js" in challenges.content

    assert assistant.status_code == 200
    assert b"assistant-root" in assistant.content
    assert b"creator-assistant.js" in assistant.content

    assert vault.status_code == 200
    assert b"vault-root" in vault.content
    assert b"creator-vault.js" in vault.content

    assert nav.status_code == 200
    for path in (
        b"/economy",
        b"/creator/profile",
        b"/social",
        b"/challenges",
        b"/assistant",
        b"/vault",
    ):
        assert path in nav.content
