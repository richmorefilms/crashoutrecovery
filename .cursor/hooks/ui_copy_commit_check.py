#!/usr/bin/env python3
"""
Cursor beforeShellExecution hook: when a git commit is about to run,
scan staged/working changes for hard-coded UI_COPY dictionary phrases.
Report only — never auto-replaces. Does not block the commit by default;
asks for confirmation when findings exist.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_ui_copy.py"


def read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def is_git_commit(command: str) -> bool:
    if not command:
        return False
    # Match commit but not --help / amend-only dry runs awkwardly
    return bool(re.search(r"\bgit(\.exe)?\s+commit\b", command, re.IGNORECASE))


def run_check() -> tuple[int, str]:
    if not CHECKER.is_file():
        return 0, ""
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--working"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    text = out if out else err
    return result.returncode, text


def main() -> int:
    payload = read_stdin()
    command = payload.get("command") or ""

    if not is_git_commit(command):
        print(json.dumps({"permission": "allow"}))
        return 0

    code, report = run_check()
    if not report:
        print(json.dumps({"permission": "allow"}))
        return 0

    has_findings = "hard-coded user-facing strings found" in report
    if not has_findings:
        print(
            json.dumps(
                {
                    "permission": "allow",
                    "agent_message": report,
                }
            )
        )
        return 0

    # Ask so the developer sees the report before committing; still no auto-fix.
    print(
        json.dumps(
            {
                "permission": "ask",
                "user_message": (
                    "UI_COPY check found hard-coded user-facing strings "
                    "in the commit changes. Review the report, wire them through "
                    "UI_COPY.json, then re-run the commit. (Nothing was auto-replaced.)"
                ),
                "agent_message": report,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
