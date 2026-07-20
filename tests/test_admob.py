"""Phase G: AdMob mobile config endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import init_db


def test_mobile_config_endpoint(tmp_path, monkeypatch):
    db = tmp_path / "admob.db"
    monkeypatch.setattr("app.db.DATABASE_PATH", db)
    monkeypatch.setattr("app.ad_system.ADMOB_APP_ID", "ca-app-pub-app")
    monkeypatch.setattr("app.ad_system.ADMOB_AD_UNIT_ID", "ca-app-pub-unit")
    monkeypatch.setattr("app.config.ADMOB_APP_ID", "ca-app-pub-app")
    monkeypatch.setattr("app.config.ADMOB_AD_UNIT_ID", "ca-app-pub-unit")
    init_db(db)

    from app import create_app

    with TestClient(create_app()) as client:
        resp = client.get("/ads/mobile-config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["app_id"] == "ca-app-pub-app"
        assert body["ad_unit_id"] == "ca-app-pub-unit"
        assert body["configured"] is True
