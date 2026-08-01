"""PWA shell — manifest, service worker, offline page."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db


@pytest.fixture()
def fe_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fe_pwa.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_pwa_manifest_and_sw(fe_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    from app import create_app

    with TestClient(create_app()) as client:
        manifest = client.get("/manifest.webmanifest")
        sw = client.get("/sw.js")
        offline = client.get("/offline")
        home = client.get("/creator/home")
    assert manifest.status_code == 200
    assert "application/manifest+json" in manifest.headers.get("content-type", "")
    data = manifest.json()
    assert data["name"] == "Crashout Recovery"
    assert data["short_name"] == "Crashout"
    assert data["start_url"] == "/creator/home"
    assert data["display"] == "standalone"
    assert data["theme_color"] == "#00eaff"
    assert sw.status_code == 200
    assert b"crashout-neon-v1" in sw.content
    assert sw.headers.get("service-worker-allowed") == "/"
    assert offline.status_code == 200
    assert b"offline-root" in offline.content
    assert home.status_code == 200
    assert b'manifest.webmanifest' in home.content or b"manifest" in home.content
    assert b"pwa-install.js" in home.content
