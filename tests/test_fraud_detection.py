"""Fraud detection helpers on recommendation_service."""
from __future__ import annotations

import pytest

from app.db import init_db, open_connection, utc_now_iso
from app.recommendation_service import detect_fraudulent_behavior, mark_user_fraudulent


@pytest.fixture()
def fraud_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fraud.db"
    monkeypatch.setenv("CRASHOUT_ENV", "test")
    monkeypatch.setattr("app.config.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.db.DATABASE_PATH", db_path)
    init_db(db_path)
    return db_path


def _seed_user(db_path, name: str) -> int:
    conn = open_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, tier, role, created_at)
            VALUES (?, ?, ?, 'basic', 'user', ?)
            """,
            (name, f"{name}@example.com", "x", utc_now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def test_detect_and_mark_fraud(fraud_db):
    uid = _seed_user(fraud_db, "fraudster")
    other = _seed_user(fraud_db, "twin")
    now = utc_now_iso()
    conn = open_connection(fraud_db)
    try:
        # Seed ad inventory + repeated clicks
        ad_id = int(
            conn.execute(
                "INSERT INTO ad_inventory (title, payout_per_click) VALUES ('x', 0.01)"
            ).lastrowid
        )
        for _ in range(12):
            conn.execute(
                """
                INSERT INTO ad_clicks (ad_id, creator_id, timestamp, payout_amount)
                VALUES (?, ?, ?, 0.01)
                """,
                (ad_id, uid, now),
            )
        # Identical history patterns
        for item in ("a", "b", "c", "d", "e"):
            conn.execute(
                """
                INSERT INTO user_history (user_id, item_id, platform, timestamp)
                VALUES (?, ?, 'youtube', ?)
                """,
                (uid, item, now),
            )
            conn.execute(
                """
                INSERT INTO user_history (user_id, item_id, platform, timestamp)
                VALUES (?, ?, 'youtube', ?)
                """,
                (other, item, now),
            )
        conn.commit()
    finally:
        conn.close()

    detected = detect_fraudulent_behavior(uid)
    assert detected["ok"] is True
    assert detected["lane"] == "fraud"
    assert detected["meta"]["fraudulent"] is True
    assert len(detected["meta"]["signals"]) >= 1

    marked = mark_user_fraudulent(uid, reason="test_mark")
    assert marked["ok"] is True
    assert marked["meta"]["fraudulent"] is True

    conn = open_connection(fraud_db)
    try:
        row = conn.execute(
            "SELECT user_id FROM fraudulent_users WHERE user_id = ?",
            (uid,),
        ).fetchone()
        assert row is not None
        sigs = conn.execute(
            "SELECT COUNT(*) AS c FROM fraud_signals WHERE user_id = ?",
            (uid,),
        ).fetchone()
        assert int(sigs["c"]) >= 1
    finally:
        conn.close()
