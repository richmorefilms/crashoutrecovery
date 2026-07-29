"""GET /api/staff/overview envelope tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth_security import create_access_token
from app.db import init_db, open_connection, utc_now_iso


@pytest.fixture()
def staff_env(tmp_path, monkeypatch):
    db_path = tmp_path / "staff_ov.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    now = utc_now_iso()
    conn = open_connection(db_path)
    try:
        staff_id = int(
            conn.execute(
                """
                INSERT INTO users (username, email, password_hash, tier, role, created_at)
                VALUES ('staffov', 'staffov@example.com', 'hash', 'basic', 'staff', ?)
                """,
                (now,),
            ).lastrowid
        )
        conn.commit()
    finally:
        conn.close()
    from app import create_app

    token, _, _ = create_access_token(user_id=staff_id, username="staffov")
    return TestClient(create_app()), token


def test_staff_overview_envelope(staff_env, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    client, token = staff_env
    res = client.get(
        "/api/staff/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lane"] == "staff"
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    meta = data["meta"]
    for key in (
        "total_creators",
        "total_items",
        "total_ads_served",
        "recommendation_volume",
        "ranking_latency_ms",
    ):
        assert key in meta
