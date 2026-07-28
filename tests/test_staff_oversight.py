"""Phase E: staff oversight APIs and audit logging."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.auth_security import create_access_token
from app.db import (
    get_user_version,
    init_db,
    insert_compose_receipt,
    list_staff_audit_log,
    open_connection,
    utc_now_iso,
)
from app.retention import POLICY_DEFAULT, POLICY_SENSITIVE


@pytest.fixture()
def oversight_env(tmp_path, monkeypatch):
    db_path = tmp_path / "oversight.db"
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    now = utc_now_iso()
    conn = open_connection(db_path)
    try:
        staff_id = int(
            conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, tier, role, created_at
                ) VALUES ('staffer', 'staff@example.com', 'hash', 'basic', 'staff', ?)
                """,
                (now,),
            ).lastrowid
        )
        user_id = int(
            conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, tier, role, created_at
                ) VALUES ('member', 'member@example.com', 'hash', 'basic', 'user', ?)
                """,
                (now,),
            ).lastrowid
        )
        conn.commit()
    finally:
        conn.close()

    insert_compose_receipt(
        request_id="req-keep",
        input_prompt="slow down",
        output_text='{"ok":true}',
        output_hash="a" * 64,
        engine_version="1",
        user_id=user_id,
        retention_policy=POLICY_DEFAULT,
        expires_at="2027-01-01T00:00:00+00:00",
        moderation_flags=None,
        path=db_path,
    )
    insert_compose_receipt(
        request_id="req-flagged",
        input_prompt="blocked spike",
        output_text='{"ok":false}',
        output_hash="b" * 64,
        engine_version="1",
        user_id=user_id,
        retention_policy=POLICY_SENSITIVE,
        expires_at="2026-04-01T00:00:00+00:00",
        moderation_flags='{"blocked":true}',
        path=db_path,
    )

    from app import create_app

    app = create_app()
    staff_token, _, _ = create_access_token(user_id=staff_id, username="staffer")
    user_token, _, _ = create_access_token(user_id=user_id, username="member")
    return {
        "app": app,
        "db_path": db_path,
        "staff_id": staff_id,
        "user_id": user_id,
        "staff_headers": {"Authorization": f"Bearer {staff_token}"},
        "user_headers": {"Authorization": f"Bearer {user_token}"},
    }


@pytest.mark.compose_receipts
def test_migration_v4_creates_staff_audit_log(tmp_path):
    db_path = tmp_path / "v4.db"
    init_db(db_path)
    conn = open_connection(db_path)
    try:
        assert get_user_version(conn) == 10
        cols = {row[1] for row in conn.execute("PRAGMA table_info(staff_audit_log)")}
        assert {
            "id",
            "staff_id",
            "action_type",
            "target_request_id",
            "target_receipt_id",
            "metadata_json",
            "created_at",
        }.issubset(cols)
    finally:
        conn.close()


@pytest.mark.compose_receipts
def test_non_staff_cannot_list_receipts(oversight_env):
    with TestClient(oversight_env["app"]) as client:
        denied = client.get("/api/staff/receipts", headers=oversight_env["user_headers"])
        assert denied.status_code == 403
        anon = client.get("/api/staff/receipts")
        assert anon.status_code == 401


@pytest.mark.compose_receipts
def test_staff_list_detail_retention_soft_delete_and_audit(oversight_env):
    headers = oversight_env["staff_headers"]
    db_path = oversight_env["db_path"]

    with TestClient(oversight_env["app"]) as client:
        listed = client.get("/api/staff/receipts", headers=headers)
        assert listed.status_code == 200
        ids = {item["request_id"] for item in listed.json()}
        assert ids == {"req-keep", "req-flagged"}

        filtered = client.get(
            "/api/staff/receipts",
            headers=headers,
            params={"retention_policy": POLICY_SENSITIVE},
        )
        assert filtered.status_code == 200
        assert [item["request_id"] for item in filtered.json()] == ["req-flagged"]

        detail = client.get("/api/staff/receipts/req-keep", headers=headers)
        assert detail.status_code == 200
        body = detail.json()
        assert body["input_prompt"] == "slow down"
        assert body["output_hash"] == "a" * 64
        assert body["retention_policy"] == POLICY_DEFAULT

        override = client.patch(
            "/api/staff/receipts/req-keep/retention",
            headers=headers,
            json={
                "new_policy_code": POLICY_SENSITIVE,
                "new_expiry_timestamp": "2026-06-01T00:00:00+00:00",
            },
        )
        assert override.status_code == 200
        assert override.json()["retention_policy"] == POLICY_SENSITIVE
        assert override.json()["expires_at"] == "2026-06-01T00:00:00+00:00"

        deleted = client.post(
            "/api/staff/receipts/req-flagged/soft-delete",
            headers=headers,
        )
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "soft_deleted"

        active = client.get("/api/staff/receipts", headers=headers)
        assert {item["request_id"] for item in active.json()} == {"req-keep"}

        with_deleted = client.get(
            "/api/staff/receipts",
            headers=headers,
            params={"include_deleted": True},
        )
        assert {item["request_id"] for item in with_deleted.json()} == {
            "req-keep",
            "req-flagged",
        }

    events = list_staff_audit_log(path=db_path, limit=20)
    actions = [event["action_type"] for event in events]
    assert "VIEW_RECEIPT" in actions
    assert "RETENTION_UPDATE" in actions
    assert "SOFT_DELETE" in actions
    retention_event = next(e for e in events if e["action_type"] == "RETENTION_UPDATE")
    meta = json.loads(retention_event["metadata_json"])
    assert meta["new_policy_code"] == POLICY_SENSITIVE
