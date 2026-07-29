"""Phase F: rate limits, abuse detection, and staff audit integration."""

from __future__ import annotations

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
from app.rate_limits import (
    EVENT_ABUSE_BURST,
    EVENT_RATE_LIMIT_EXCEEDED,
    LIMIT_COMPOSE,
    LIMIT_STAFF_MODIFY,
    LIMIT_STAFF_VIEW,
    AUDIT_RATE_LIMIT_HIT,
    RateLimitExceeded,
    RateLimitPolicy,
    check_rate_limit,
    increment_rate_limit,
    reset_rate_limit_windows,
    subject_for_staff,
    subject_for_user,
)
from app.retention import POLICY_DEFAULT


@pytest.mark.compose_receipts
def test_migration_v5_rate_limits_and_abuse_tables(tmp_path):
    db_path = tmp_path / "v5.db"
    init_db(db_path)
    conn = open_connection(db_path)
    try:
        assert get_user_version(conn) == 15
        rate_cols = {row[1] for row in conn.execute("PRAGMA table_info(rate_limits)")}
        abuse_cols = {row[1] for row in conn.execute("PRAGMA table_info(abuse_events)")}
        assert {
            "id",
            "subject_id",
            "window_start",
            "window_end",
            "count",
            "limit_type",
        }.issubset(rate_cols)
        assert {
            "id",
            "subject_id",
            "event_type",
            "metadata_json",
            "created_at",
        }.issubset(abuse_cols)
    finally:
        conn.close()


@pytest.mark.compose_receipts
def test_user_compose_rate_limit_enforcement(tmp_path):
    db_path = tmp_path / "compose_rl.db"
    init_db(db_path)
    subject = subject_for_user(42)
    policy = RateLimitPolicy(max_count=2, window_seconds=300)

    check_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)
    increment_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)
    check_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)
    increment_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)

    with pytest.raises(RateLimitExceeded) as exc:
        check_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)
    assert exc.value.limit == 2
    assert exc.value.limit_type == LIMIT_COMPOSE

    conn = open_connection(db_path)
    try:
        hits = conn.execute(
            "SELECT COUNT(*) AS n FROM abuse_events WHERE event_type = ?",
            (EVENT_RATE_LIMIT_EXCEEDED,),
        ).fetchone()["n"]
        assert int(hits) >= 1
    finally:
        conn.close()


@pytest.mark.compose_receipts
def test_staff_view_and_modify_limits_with_audit(tmp_path):
    db_path = tmp_path / "staff_rl.db"
    init_db(db_path)
    now = utc_now_iso()
    conn = open_connection(db_path)
    try:
        staff_id = int(
            conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, tier, role, created_at
                ) VALUES ('limiter', 'limiter@example.com', 'hash', 'basic', 'staff', ?)
                """,
                (now,),
            ).lastrowid
        )
        conn.commit()
    finally:
        conn.close()

    subject = subject_for_staff(staff_id)
    view_policy = RateLimitPolicy(max_count=1, window_seconds=3600)
    modify_policy = RateLimitPolicy(max_count=1, window_seconds=3600)

    check_rate_limit(
        subject,
        LIMIT_STAFF_VIEW,
        policy=view_policy,
        path=db_path,
        staff_id_for_audit=staff_id,
    )
    increment_rate_limit(subject, LIMIT_STAFF_VIEW, policy=view_policy, path=db_path)
    with pytest.raises(RateLimitExceeded):
        check_rate_limit(
            subject,
            LIMIT_STAFF_VIEW,
            policy=view_policy,
            path=db_path,
            staff_id_for_audit=staff_id,
        )

    check_rate_limit(
        subject,
        LIMIT_STAFF_MODIFY,
        policy=modify_policy,
        path=db_path,
        staff_id_for_audit=staff_id,
    )
    increment_rate_limit(subject, LIMIT_STAFF_MODIFY, policy=modify_policy, path=db_path)
    with pytest.raises(RateLimitExceeded):
        check_rate_limit(
            subject,
            LIMIT_STAFF_MODIFY,
            policy=modify_policy,
            path=db_path,
            staff_id_for_audit=staff_id,
        )

    audits = list_staff_audit_log(path=db_path, limit=20)
    assert any(row["action_type"] == AUDIT_RATE_LIMIT_HIT for row in audits)


@pytest.mark.compose_receipts
def test_abuse_burst_after_repeated_limit_hits(tmp_path, monkeypatch):
    db_path = tmp_path / "abuse.db"
    init_db(db_path)
    monkeypatch.setattr("app.rate_limits.ABUSE_HIT_THRESHOLD", 3)
    subject = subject_for_user(7)
    policy = RateLimitPolicy(max_count=1, window_seconds=300)

    increment_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)
    for _ in range(3):
        with pytest.raises(RateLimitExceeded):
            check_rate_limit(subject, LIMIT_COMPOSE, policy=policy, path=db_path)

    conn = open_connection(db_path)
    try:
        burst = conn.execute(
            """
            SELECT COUNT(*) AS n FROM abuse_events
            WHERE subject_id = ? AND event_type = ?
            """,
            (subject, EVENT_ABUSE_BURST),
        ).fetchone()["n"]
        assert int(burst) >= 1
    finally:
        conn.close()


@pytest.mark.compose_receipts
def test_compose_http_returns_429_when_limited(tmp_path, monkeypatch):
    db_path = tmp_path / "http_rl.db"
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.rate_limits.USER_COMPOSE_LIMIT", 2)
    monkeypatch.setattr("app.compose_engine.record_compose_receipt", lambda **_kwargs: 0)
    monkeypatch.setattr("app.compose_engine._find_curated_matches", lambda _text: [])
    init_db(db_path)
    reset_rate_limit_windows(path=db_path)

    from app import create_app

    with TestClient(create_app()) as client:
        assert (
            client.post("/api/compose", json={"spike_text": "first compose"}).status_code
            == 200
        )
        assert (
            client.post("/api/compose", json={"spike_text": "second compose"}).status_code
            == 200
        )
        blocked = client.post("/api/compose", json={"spike_text": "third compose"})
        assert blocked.status_code == 429
        assert blocked.json()["detail"]["error"] == "rate_limit_exceeded"
        assert blocked.headers.get("Retry-After")


@pytest.mark.compose_receipts
def test_staff_modify_http_rate_limit(tmp_path, monkeypatch):
    db_path = tmp_path / "staff_http_rl.db"
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.rate_limits.STAFF_MODIFY_LIMIT", 1)
    init_db(db_path)
    now = utc_now_iso()
    conn = open_connection(db_path)
    try:
        staff_id = int(
            conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, tier, role, created_at
                ) VALUES ('modstaff', 'modstaff@example.com', 'hash', 'basic', 'staff', ?)
                """,
                (now,),
            ).lastrowid
        )
        conn.commit()
    finally:
        conn.close()

    insert_compose_receipt(
        request_id="req-a",
        input_prompt="a",
        output_text="{}",
        output_hash="a" * 64,
        engine_version="1",
        retention_policy=POLICY_DEFAULT,
        expires_at="2027-01-01T00:00:00+00:00",
        path=db_path,
    )
    insert_compose_receipt(
        request_id="req-b",
        input_prompt="b",
        output_text="{}",
        output_hash="b" * 64,
        engine_version="1",
        retention_policy=POLICY_DEFAULT,
        expires_at="2027-01-01T00:00:00+00:00",
        path=db_path,
    )

    token, _, _ = create_access_token(user_id=staff_id, username="modstaff")
    headers = {"Authorization": f"Bearer {token}"}
    from app import create_app

    with TestClient(create_app()) as client:
        first = client.post("/api/staff/receipts/req-a/soft-delete", headers=headers)
        assert first.status_code == 200
        second = client.post("/api/staff/receipts/req-b/soft-delete", headers=headers)
        assert second.status_code == 429
        assert second.json()["detail"]["limit_type"] == LIMIT_STAFF_MODIFY


@pytest.mark.compose_receipts
def test_endpoint_rate_limit_user_id_api(tmp_path, monkeypatch):
    """v15: check_rate_limit(user_id, endpoint) + reset_rate_limits()."""
    db_path = tmp_path / "endpoint_rl.db"
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    from app.rate_limits import (
        check_rate_limit,
        increment_rate_limit,
        reset_rate_limits,
        enforce_endpoint_rate_limit,
    )

    assert check_rate_limit(7, "/api/growth/score", path=db_path, max_count=2) is True
    increment_rate_limit(7, "/api/growth/score", path=db_path, max_count=2)
    assert check_rate_limit(7, "/api/growth/score", path=db_path, max_count=2) is True
    increment_rate_limit(7, "/api/growth/score", path=db_path, max_count=2)
    assert check_rate_limit(7, "/api/growth/score", path=db_path, max_count=2) is False

    blocked = enforce_endpoint_rate_limit(7, "/api/growth/score", path=db_path, max_count=2)
    assert blocked is not None
    assert blocked.status_code == 429
    body = blocked.body
    import json

    payload = json.loads(body.decode("utf-8"))
    assert payload["ok"] is False
    assert payload["reason"] == "rate_limit_exceeded"

    reset_rate_limits(path=db_path)
    assert check_rate_limit(7, "/api/growth/score", path=db_path, max_count=2) is True


@pytest.mark.compose_receipts
def test_migration_v15_endpoint_rate_limits_and_fraud(tmp_path):
    db_path = tmp_path / "v15.db"
    init_db(db_path)
    conn = open_connection(db_path)
    try:
        assert get_user_version(conn) == 15
        ep_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(endpoint_rate_limits)")
        }
        fraud_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(fraud_signals)")
        }
        flag_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(flagged_items)")
        }
        assert {"id", "user_id", "endpoint", "count", "window_start"}.issubset(ep_cols)
        assert {"id", "user_id", "signal", "timestamp"}.issubset(fraud_cols)
        assert {"id", "item_id", "active"}.issubset(flag_cols)
    finally:
        conn.close()
