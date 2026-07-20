"""Phase D: compose receipt retention and soft-delete."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db import (
    init_db,
    insert_compose_receipt,
    list_active_compose_receipts,
    soft_delete_compose_receipt,
)
from app.retention import (
    POLICY_DEFAULT,
    POLICY_SENSITIVE,
    POLICY_STAFF,
    DEFAULT_RETENTION_DAYS,
    SENSITIVE_RETENTION_DAYS,
    STAFF_RETENTION_DAYS,
    resolve_compose_retention,
)


def test_retention_policy_default():
    created = "2026-01-01T00:00:00+00:00"
    decision = resolve_compose_retention(created_at=created)
    assert decision.policy == POLICY_DEFAULT
    expected = (
        datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=DEFAULT_RETENTION_DAYS)
    ).isoformat()
    assert decision.expires_at == expected


def test_retention_policy_sensitive_blocked():
    created = "2026-01-01T00:00:00+00:00"
    decision = resolve_compose_retention(
        created_at=created,
        moderation_flags='{"blocked": true}',
    )
    assert decision.policy == POLICY_SENSITIVE
    expected = (
        datetime(2026, 1, 1, tzinfo=timezone.utc)
        + timedelta(days=SENSITIVE_RETENTION_DAYS)
    ).isoformat()
    assert decision.expires_at == expected


def test_retention_policy_staff_overrides_sensitive():
    created = "2026-01-01T00:00:00+00:00"
    decision = resolve_compose_retention(
        created_at=created,
        moderation_flags={"blocked": True},
        staff_id=9,
    )
    assert decision.policy == POLICY_STAFF
    expected = (
        datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=STAFF_RETENTION_DAYS)
    ).isoformat()
    assert decision.expires_at == expected


@pytest.mark.compose_receipts
def test_soft_delete_excludes_from_active_list(tmp_path):
    db_path = tmp_path / "retention.db"
    init_db(db_path)

    insert_compose_receipt(
        request_id="req-active",
        input_prompt="keep me",
        output_text="{}",
        output_hash="a" * 64,
        engine_version="1",
        retention_policy=POLICY_DEFAULT,
        expires_at="2027-01-01T00:00:00+00:00",
        path=db_path,
    )
    insert_compose_receipt(
        request_id="req-gone",
        input_prompt="delete me",
        output_text="{}",
        output_hash="b" * 64,
        engine_version="1",
        retention_policy=POLICY_DEFAULT,
        expires_at="2027-01-01T00:00:00+00:00",
        path=db_path,
    )

    assert soft_delete_compose_receipt(request_id="req-gone", path=db_path) is True
    assert soft_delete_compose_receipt(request_id="req-gone", path=db_path) is False

    active = list_active_compose_receipts(path=db_path)
    ids = {row["request_id"] for row in active}
    assert ids == {"req-active"}
    assert all(row["deleted_at"] is None for row in active)
