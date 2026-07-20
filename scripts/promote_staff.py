#!/usr/bin/env python3
"""One-time / ops CLI: promote an existing user to staff.

Usage (from repo root):
  python scripts/promote_staff.py --username alice
  python scripts/promote_staff.py --email founder@example.com

Bootstrap the first staff account with this script. Later promotions can use
POST /auth/staff/promote (staff-gated). Registration never grants staff.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import init_db, promote_user_to_staff  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a user to staff role")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--username", help="Username to promote")
    group.add_argument("--email", help="Email to promote")
    args = parser.parse_args()

    init_db()
    identity = args.username or args.email
    user = promote_user_to_staff(identity)
    if not user:
        print(f"No user found for {identity!r}", file=sys.stderr)
        return 1
    print(f"Promoted {user['username']} <{user['email']}> to role={user['role']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
