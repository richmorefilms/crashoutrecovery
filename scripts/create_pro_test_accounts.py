"""Create 5 local Pro preview accounts for manual testing.

Usage:
  python scripts/create_pro_test_accounts.py

Accounts are written to the local SQLite DB (data/crashout.db).
There is no live billing — tier is a server-side preview entitlement.
"""
from __future__ import annotations

from app.auth_security import hash_password
from app.config import DATA_DIR, DATABASE_PATH
from app.db import get_conn, init_db, utc_now_iso

PASSWORD = "TestPro123!"
ACCOUNT_COUNT = 5


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    pw_hash = hash_password(PASSWORD)
    created = utc_now_iso()
    accounts: list[dict[str, object]] = []

    with get_conn() as conn:
        for i in range(1, ACCOUNT_COUNT + 1):
            username = f"pro_test{i}"
            email = f"pro_test{i}@crashout.test"
            existing = conn.execute(
                "SELECT id, username, email, tier FROM users WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET tier = ? WHERE id = ?",
                    ("pro", int(existing["id"])),
                )
                accounts.append(
                    {
                        "id": int(existing["id"]),
                        "username": existing["username"],
                        "email": existing["email"],
                        "tier": "pro",
                        "status": "updated_existing",
                    }
                )
                continue

            cur = conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, tier, role, created_at, last_login
                )
                VALUES (?, ?, ?, 'pro', 'user', ?, ?)
                """,
                (username, email, pw_hash, created, created),
            )
            user_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO recovery (user_id, streak_days, spike_history, tones, wins)
                VALUES (?, 0, '[]', '[]', 0)
                """,
                (user_id,),
            )
            accounts.append(
                {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "tier": "pro",
                    "status": "created",
                }
            )

    print(f"DATABASE: {DATABASE_PATH}")
    print(f"PASSWORD: {PASSWORD}")
    print("")
    for account in accounts:
        print(
            f"{account['status']}\tid={account['id']}\t"
            f"{account['username']}\t{account['email']}\ttier={account['tier']}"
        )


if __name__ == "__main__":
    main()
