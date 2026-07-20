#!/usr/bin/env python3
"""Optional local git pre-commit entrypoint (report-only unless --strict)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_ui_copy.py"


def main() -> int:
    strict = "--strict" in sys.argv
    cmd = [sys.executable, str(CHECKER), "--working"]
    if strict:
        cmd.append("--strict")
    result = subprocess.run(cmd, cwd=ROOT)
    # Always print guidance; never auto-replace.
    if result.returncode != 0:
        print(
            "\nUI_COPY check failed (--strict). "
            "Wire strings through UI_COPY.json, then retry.\n",
            file=sys.stderr,
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
