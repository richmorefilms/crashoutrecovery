"""Phase G: AdSense template injection."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ad_system import create_story
from app.db import init_db


def test_story_page_includes_adsense_when_configured(tmp_path, monkeypatch):
    db = tmp_path / "adsense.db"
    monkeypatch.setattr("app.db.DATABASE_PATH", db)
    monkeypatch.setattr("app.ad_system.ADSENSE_CLIENT_ID", "ca-pub-testclient")
    monkeypatch.setattr("app.ad_system.ADSENSE_SLOT_TOP", "111")
    monkeypatch.setattr("app.config.ADSENSE_CLIENT_ID", "ca-pub-testclient")
    monkeypatch.setattr("app.config.ADSENSE_SLOT_TOP", "111")
    init_db(db)
    create_story(
        title="AdSense story",
        body="Body",
        published=True,
        path=db,
    )

    from app import create_app
    from app.ad_system import adsense_context

    ctx = adsense_context()
    assert ctx["adsense_enabled"] is True
    assert ctx["adsense_client_id"] == "ca-pub-testclient"

    with TestClient(create_app()) as client:
        page = client.get("/stories/1")
        assert page.status_code == 200
        assert "pagead2.googlesyndication.com" in page.text
        assert "ca-pub-testclient" in page.text
