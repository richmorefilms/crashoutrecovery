"""Staff flag / unflag envelope tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth_security import create_access_token
from app.db import init_db, open_connection, utc_now_iso


@pytest.fixture()
def staff_env(tmp_path, monkeypatch):
    db_path = tmp_path / "staff_flags.db"
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
                VALUES ('flagger', 'flagger@example.com', 'hash', 'basic', 'staff', ?)
                """,
                (now,),
            ).lastrowid
        )
        conn.commit()
    finally:
        conn.close()
    from app import create_app

    token, _, _ = create_access_token(user_id=staff_id, username="flagger")
    return TestClient(create_app()), token


def test_staff_flag_and_list(staff_env, monkeypatch):
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    client, token = staff_env
    headers = {"Authorization": f"Bearer {token}"}

    flag = client.post("/api/staff/flag/item_abc?reason=spam", headers=headers)
    assert flag.status_code == 200
    fdata = flag.json()
    assert fdata["ok"] is True
    assert fdata["lane"] == "staff"
    assert fdata["meta"].get("flagged") is True

    listed = client.get("/api/staff/flags", headers=headers)
    assert listed.status_code == 200
    ldata = listed.json()
    assert ldata["ok"] is True
    assert ldata["count"] >= 1
    assert any(i.get("item_id") == "item_abc" for i in ldata["items"])

    unflag = client.post("/api/staff/unflag/item_abc", headers=headers)
    assert unflag.status_code == 200
    assert unflag.json()["meta"].get("flagged") is False

    listed2 = client.get("/api/staff/flags", headers=headers)
    assert listed2.status_code == 200
    assert all(i.get("item_id") != "item_abc" for i in listed2.json()["items"])
