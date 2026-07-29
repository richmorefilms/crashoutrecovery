"""Unified feed ad injection tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.feed_service import merge_items_with_ads


@pytest.fixture()
def mon_db(tmp_path, monkeypatch):
    db_path = tmp_path / "feed_ads.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def test_merge_items_with_ads_every_n():
    items = [{"id": f"c{i}", "platform": "youtube", "title": f"C{i}"} for i in range(6)]
    ads = [{"id": 1, "title": "Ad A", "image": None, "cta": "/", "payout_per_click": 0.05}]
    merged = merge_items_with_ads(items, ads, every_n=3)
    ad_slots = [x for x in merged if x.get("platform") == "ad"]
    assert len(ad_slots) == 2
    assert merged[3]["platform"] == "ad"
    assert merged[7]["platform"] == "ad"


def test_feed_all_with_ads_flag(mon_db, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.youtube_service.YOUTUBE_API_KEY", "")
    monkeypatch.setattr("app.feed_service.YOUTUBE_API_KEY", "")
    from app import create_app

    with TestClient(create_app()) as client:
        plain = client.get("/api/feed/all")
        with_ads = client.get("/api/feed/all?with_ads=true")
    assert plain.status_code == 200
    assert with_ads.status_code == 200
    p = plain.json()
    a = with_ads.json()
    assert p["meta"].get("ads_injected") is False
    assert a["ok"] is True
    assert a["meta"]["ads_injected"] is True
    assert a["count"] >= p["count"]
    assert any(i.get("platform") == "ad" for i in a["items"])
