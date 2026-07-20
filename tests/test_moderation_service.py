import json
import sqlite3

import pytest

from app.compose_engine import _issue_receipt
from app.compose_schemas import ApproveSeedRequest, SaveSeedRequest
from app.db import init_db, open_connection, utc_now_iso
from app.moderation_service import (
    ModerationConflictError,
    ModerationNotFoundError,
    ModerationValidationError,
    promote_moderation_item,
    queue_seed,
    reject_moderation_item,
)


@pytest.fixture()
def moderation_db(tmp_path):
    path = tmp_path / "moderation.db"
    init_db(path)
    conn = open_connection(path)
    try:
        now = utc_now_iso()
        user_id = conn.execute(
            """
            INSERT INTO users (
                username, email, password_hash, tier, role, created_at
            )
            VALUES ('submitter', 'submitter@example.com', 'hash', 'basic', 'user', ?)
            """,
            (now,),
        ).lastrowid
        staff_id = conn.execute(
            """
            INSERT INTO users (
                username, email, password_hash, tier, role, created_at
            )
            VALUES ('reviewer', 'reviewer@example.com', 'hash', 'basic', 'staff', ?)
            """,
            (now,),
        ).lastrowid
        conn.commit()
    finally:
        conn.close()
    return path, int(user_id), int(staff_id)


def _queue(path, user_id, spike_text="I am deleting everything forever"):
    return queue_seed(
        SaveSeedRequest(
            spike_text=spike_text,
            suggested_rewrite="I am pausing before I decide.",
            safe_move="Save this draft.",
            tone="direct",
            compose_receipt=_issue_receipt(spike_text, True),
        ),
        submitted_by=user_id,
        db_path=path,
    )


def _approval(commentary="A public irreversible move became a private pause."):
    return ApproveSeedRequest(
        episode_title="Pause before deletion",
        commentary=commentary,
        recovery_moves=[" Save the draft ", "Save the draft", "Wait ten minutes"],
        tone_variations=["I am pausing before I decide."],
        tags=[" Delete ", "recovery", "delete"],
    )


def test_schema_is_idempotent_and_audit_is_immutable(moderation_db):
    path, _, _ = moderation_db
    init_db(path)
    conn = open_connection(path)
    try:
        role = {
            row["name"]: row for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }["role"]
        assert role["notnull"] == 1
        indexes = {
            row["name"]
            for row in conn.execute("PRAGMA index_list(moderation_events)").fetchall()
        }
        assert "idx_moderation_events_queue_id" in indexes
        triggers = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            ).fetchall()
        }
        assert {"moderation_events_no_update", "moderation_events_no_delete"} <= triggers
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_approval_validates_original_then_redacts_and_audits(moderation_db):
    path, user_id, staff_id = moderation_db
    queue_id = _queue(path, user_id)

    with pytest.raises(ModerationValidationError):
        promote_moderation_item(
            queue_id,
            _approval("I am deleting everything forever"),
            curated_by=staff_id,
            db_path=path,
        )

    crashout_id = promote_moderation_item(
        queue_id,
        _approval(),
        curated_by=staff_id,
        db_path=path,
    )
    conn = open_connection(path)
    try:
        queue_row = conn.execute(
            "SELECT * FROM moderation_queue WHERE id = ?", (queue_id,)
        ).fetchone()
        assert queue_row["status"] == "approved"
        assert queue_row["spike_text"] is None
        assert queue_row["suggested_rewrite"] is None
        assert queue_row["safe_move"] is None

        crashout = conn.execute(
            "SELECT * FROM crashout_database WHERE id = ?", (crashout_id,)
        ).fetchone()
        assert crashout["source_queue_id"] == queue_id
        assert crashout["ai_generated"] == 1
        assert json.loads(crashout["recovery_moves"]) == [
            "Save the draft",
            "Wait ten minutes",
        ]
        tags = [
            row["tag"]
            for row in conn.execute(
                "SELECT tag FROM crashout_tags WHERE crashout_id = ? ORDER BY tag",
                (crashout_id,),
            )
        ]
        assert tags == ["delete", "recovery"]

        event = conn.execute(
            "SELECT * FROM moderation_events WHERE queue_id = ? AND event_type = 'approved'",
            (queue_id,),
        ).fetchone()
        assert "deleting everything" not in event["details"]
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "UPDATE moderation_events SET details = '{}' WHERE id = ?",
                (event["id"],),
            )
    finally:
        conn.rollback()
        conn.close()


def test_approval_distinguishes_not_found_from_conflict(moderation_db):
    path, user_id, staff_id = moderation_db
    queue_id = _queue(path, user_id)
    promote_moderation_item(
        queue_id,
        _approval(),
        curated_by=staff_id,
        db_path=path,
    )

    with pytest.raises(ModerationConflictError):
        promote_moderation_item(
            queue_id,
            _approval(),
            curated_by=staff_id,
            db_path=path,
        )
    with pytest.raises(ModerationNotFoundError):
        promote_moderation_item(
            999_999,
            _approval(),
            curated_by=staff_id,
            db_path=path,
        )


def test_rejection_is_atomic_redacted_and_audited(moderation_db):
    path, user_id, staff_id = moderation_db
    queue_id = _queue(path, user_id)
    reject_moderation_item(
        queue_id,
        reviewed_by=staff_id,
        reason="Duplicate lesson",
        db_path=path,
    )

    conn = open_connection(path)
    try:
        row = conn.execute(
            "SELECT * FROM moderation_queue WHERE id = ?", (queue_id,)
        ).fetchone()
        assert row["status"] == "rejected"
        assert row["spike_text"] is None
        assert row["suggested_rewrite"] is None
        assert row["safe_move"] is None
        event = conn.execute(
            "SELECT details FROM moderation_events WHERE queue_id = ? AND event_type = 'rejected'",
            (queue_id,),
        ).fetchone()
        details = json.loads(event["details"])
        assert details["reason_recorded"] is True
        assert len(details["reason_sha256"]) == 64
        assert "Duplicate lesson" not in event["details"]
    finally:
        conn.close()
