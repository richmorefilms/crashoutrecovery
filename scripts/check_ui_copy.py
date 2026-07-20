#!/usr/bin/env python3
"""
Scan changed files for hard-coded user-facing copy that should use UI_COPY.json.

Report-only: never auto-replaces. Ignores developer docs and internal identifiers.

Usage:
  python scripts/check_ui_copy.py                # staged vs HEAD (falls back to working tree)
  python scripts/check_ui_copy.py --working      # unstaged + staged vs HEAD
  python scripts/check_ui_copy.py --commit HEAD  # files in a commit
  python scripts/check_ui_copy.py --files a.js b.html
  python scripts/check_ui_copy.py --strict       # exit 1 when findings exist
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_COPY_PATH = ROOT / "UI_COPY.json"

SCAN_SUFFIXES = {".html", ".js", ".md", ".py"}
IGNORE_PATH_PARTS = {
    "OPERATIONS.md",
    "ops-full.md",
    "PLAIN_OPS.md",  # static download mirror of /ops; regenerate from dictionary later
    "UI_COPY.json",
    "UI_COPY_PATCH.md",
    "PLAIN_LANGUAGE_REPLACEMENTS.md",
    "check_ui_copy.py",
    "_ui_copy_report.txt",
    "_ui_copy_report.json",
    "node_modules",
    ".git",
    "data/",
    "tests/",
}

# Insider / legacy terms → dictionary key (same keys as UI_COPY.json)
INSIDER_ALIASES: dict[str, list[str]] = {
    "pulse_strip": ["pulse strip", "pulse-strip"],
    "composer": ["compose fab", "the composer"],
    "seed": ["save seed", "seed preview", "seed templates"],
    "tone_pills": ["tone pills", "tone pill"],
    "momentum_cta": ["momentum cta", "momentum move", "momentum:"],
    "recovery_streak": ["recovery streak"],
    "momentum_score": ["momentum score", "momentum meter"],
    "bad_decision_predictor": ["bad decision predictor", "bad-decision predictor"],
    "signals_pro": ["signals pro", "world signals pro"],
    "marketplace_packs": ["marketplace packs", "marketplace pack"],
    "premium_tiers": ["premium tiers", "premium tier"],
    "global_spike_alert": ["global spike alert", "spike alert flash"],
}


@dataclass
class Finding:
    path: str
    line: int
    text: str
    key: str
    label: str
    kind: str  # "label" | "tooltip" | "insider"

    def replacement_example(self) -> str:
        rel = Path(self.path).suffix.lower()
        if rel == ".html":
            return (
                f'{{{{ uc.{self.key}.label }}}}  '
                f'<!-- or title="{{{{ uc.{self.key}.tooltip }}}}" -->'
            )
        if rel == ".js":
            return (
                f'uiLabel("{self.key}", "{self.label}")  '
                f'// or CrashoutUICopy.label("{self.key}")'
            )
        if rel == ".md":
            return f"(prefer generating from UI_COPY.json / ops template; key: {self.key})"
        return f'ui_label("{self.key}") / CrashoutUICopy.label("{self.key}")'


def load_ui_copy() -> dict[str, dict[str, str]]:
    with UI_COPY_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit("UI_COPY.json must be an object")
    return data


def should_scan(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return False
    if path.suffix.lower() not in SCAN_SUFFIXES:
        return False
    name = path.name
    if name in IGNORE_PATH_PARTS:
        return False
    if any(part in rel for part in IGNORE_PATH_PARTS if part.endswith("/")):
        return False
    if rel.endswith("OPERATIONS.md") or rel.endswith("ops-full.md"):
        return False
    if rel.endswith("ui-copy.js"):
        # Fallback dictionary — intentional hard-coded mirror of UI_COPY.json
        return False
    if rel.startswith("scripts/") and path.name.startswith("check_ui_copy"):
        return False
    return True


def line_is_dictionary_wired(line: str, key: str) -> bool:
    """True when the line already routes copy through UI_COPY."""
    patterns = [
        rf"\buc\.{re.escape(key)}\b",
        rf"\bui_copy\b",
        rf'data-ui-copy=["\']{re.escape(key)}["\']',
        rf'uiLabel\(\s*["\']{re.escape(key)}["\']',
        rf'uiLower\(\s*["\']{re.escape(key)}["\']',
        rf'CrashoutUICopy\.(?:label|labelLower|tooltip|get)\(\s*["\']{re.escape(key)}["\']',
        rf'(?:label|tooltip)\(\s*["\']{re.escape(key)}["\']',
        rf'ui_label\(\s*["\']{re.escape(key)}["\']',
        rf'ui_tooltip\(\s*["\']{re.escape(key)}["\']',
    ]
    return any(re.search(p, line) for p in patterns)


def line_is_developer_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    # Comments / module headers
    if stripped.startswith(("//", "/*", "*", "#", "<!--")):
        return True
    # localStorage keys and storage identifiers
    if "localStorage" in line or "crashout_" in line and ("KEY" in line or "getItem" in line or "setItem" in line):
        return True
    # CSS classes / HTML ids that embed insider words
    if re.search(r"""(?:class|id|className|getElementById|querySelector)\s*[=(]""", line):
        # Still scan string literals on those lines below — don't blanket-skip
        pass
    # Pure module API identifiers without user copy quotes containing UI phrases
    if re.search(r"\bCrashout[A-Z]\w*\b", line) and not re.search(r"""['"][^'"]{3,}['"]""", line):
        return True
    return False


def build_matchers(copy: dict[str, dict[str, str]]) -> list[tuple[str, str, str, re.Pattern[str]]]:
    """Return list of (key, label_or_phrase, kind, pattern)."""
    matchers: list[tuple[str, str, str, re.Pattern[str]]] = []
    for key, entry in copy.items():
        label = (entry or {}).get("label") or ""
        tip = (entry or {}).get("tooltip") or ""
        if label:
            matchers.append(
                (
                    key,
                    label,
                    "label",
                    re.compile(rf"(?<![\w/]){re.escape(label)}(?![\w-])", re.IGNORECASE),
                )
            )
        if tip and len(tip) >= 24:
            # Full tooltip pasted into UI
            matchers.append(
                (
                    key,
                    tip,
                    "tooltip",
                    re.compile(re.escape(tip), re.IGNORECASE),
                )
            )
        for alias in INSIDER_ALIASES.get(key, []):
            matchers.append(
                (
                    key,
                    alias,
                    "insider",
                    re.compile(rf"(?<![\w/]){re.escape(alias)}(?![\w-])", re.IGNORECASE),
                )
            )
    # Longer phrases first to avoid nested double-flags when possible
    matchers.sort(key=lambda m: len(m[1]), reverse=True)
    return matchers


def scan_line(
    path: str,
    line_no: int,
    line: str,
    matchers: list[tuple[str, str, str, re.Pattern[str]]],
    copy: dict[str, dict[str, str]],
) -> list[Finding]:
    if line_is_developer_noise(line):
        return []
    findings: list[Finding] = []
    hit_spans: list[tuple[int, int]] = []

    for key, phrase, kind, pattern in matchers:
        if line_is_dictionary_wired(line, key):
            continue
        for match in pattern.finditer(line):
            span = match.span()
            # Skip overlaps with earlier (longer) hits
            if any(not (span[1] <= a or span[0] >= b) for a, b in hit_spans):
                continue
            # Skip CSS/js identifiers like momentum-score, composer-modal
            before = line[max(0, span[0] - 1) : span[0]]
            after = line[span[1] : span[1] + 1]
            if before in "-_." or after in "-_.":
                continue
            label = (copy.get(key) or {}).get("label") or key
            findings.append(
                Finding(
                    path=path,
                    line=line_no,
                    text=match.group(0),
                    key=key,
                    label=label,
                    kind=kind,
                )
            )
            hit_spans.append(span)
    return findings


def git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def changed_files_staged() -> list[Path]:
    out = git_output("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    files = [ROOT / line.strip() for line in out.splitlines() if line.strip()]
    if files:
        return files
    # Nothing staged — scan working tree changes vs HEAD
    out = git_output("diff", "HEAD", "--name-only", "--diff-filter=ACMR")
    return [ROOT / line.strip() for line in out.splitlines() if line.strip()]


def changed_files_working() -> list[Path]:
    out = git_output("diff", "HEAD", "--name-only", "--diff-filter=ACMR")
    paths = {ROOT / line.strip() for line in out.splitlines() if line.strip()}
    untracked = git_output("ls-files", "--others", "--exclude-standard")
    for line in untracked.splitlines():
        if line.strip():
            paths.add(ROOT / line.strip())
    return sorted(paths)


def changed_files_commit(ref: str) -> list[Path]:
    out = git_output("diff-tree", "--no-commit-id", "--name-only", "-r", ref)
    return [ROOT / line.strip() for line in out.splitlines() if line.strip()]


def added_line_map(path: Path, mode: str, commit: str | None) -> dict[int, str] | None:
    """
    If a diff is available, return {line_number_in_new_file: line_text} for added lines only.
    None means scan the whole file.
    """
    rel = path.resolve().relative_to(ROOT).as_posix()
    if mode == "files":
        return None
    if mode == "commit" and commit:
        diff = git_output("show", "--format=", "--unified=0", commit, "--", rel)
    elif mode == "working":
        diff = git_output("diff", "HEAD", "--unified=0", "--", rel)
        if not diff and not path.exists():
            return {}
        if not diff:
            # Untracked → whole file is “new”
            return None
    else:
        diff = git_output("diff", "--cached", "--unified=0", "--", rel)
        if not diff:
            diff = git_output("diff", "HEAD", "--unified=0", "--", rel)
        if not diff:
            return None

    added: dict[int, str] = {}
    new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            # @@ -a,b +c,d @@
            m = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            if not m:
                continue
            new_line = int(m.group(1))
            continue
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("diff "):
            continue
        if raw.startswith("+"):
            added[new_line] = raw[1:]
            new_line += 1
        elif raw.startswith("-"):
            continue
        else:
            # context (rare with unified=0) or '\ No newline'
            if not raw.startswith("\\"):
                new_line += 1
    return added


def scan_file(
    path: Path,
    matchers: list[tuple[str, str, str, re.Pattern[str]]],
    mode: str,
    commit: str | None,
    copy: dict[str, dict[str, str]],
) -> list[Finding]:
    if not should_scan(path):
        return []
    if not path.is_file():
        return []

    rel = path.resolve().relative_to(ROOT).as_posix()
    line_map = added_line_map(path, mode, commit)

    findings: list[Finding] = []
    if line_map is None:
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            findings.extend(scan_line(rel, i, line, matchers, copy))
    else:
        for i, line in sorted(line_map.items()):
            findings.extend(scan_line(rel, i, line, matchers, copy))
    return findings


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return "UI_COPY check: OK - no hard-coded dictionary phrases in scanned changes.\n"

    lines = [
        "UI_COPY check: hard-coded user-facing strings found",
        "(report only - not auto-replaced; wire through UI_COPY.json)",
        "",
    ]
    for i, f in enumerate(findings, start=1):
        lines.extend(
            [
                f"### {i}. {f.path}:{f.line}",
                f"- Hard-coded: {f.text!r} ({f.kind})",
                f"- Suggested key: {f.key} -> {f.label!r}",
                f"- Example: {f.replacement_example()}",
                "",
            ]
        )
    lines.append(f"Total: {len(findings)} finding(s).")
    return "\n".join(lines) + "\n"


def safe_print(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))
        if not text.endswith("\n"):
            sys.stdout.buffer.write(b"\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report hard-coded UI copy vs UI_COPY.json")
    parser.add_argument("--working", action="store_true", help="Scan working tree vs HEAD")
    parser.add_argument("--commit", metavar="REF", help="Scan files changed in commit REF")
    parser.add_argument("--files", nargs="+", help="Scan these files fully")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if findings exist")
    parser.add_argument("--json", action="store_true", help="Emit JSON findings")
    args = parser.parse_args(argv)

    copy = load_ui_copy()
    matchers = build_matchers(copy)

    if args.files:
        mode = "files"
        files = [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.files]
        commit = None
    elif args.commit:
        mode = "commit"
        files = changed_files_commit(args.commit)
        commit = args.commit
    elif args.working:
        mode = "working"
        files = changed_files_working()
        commit = None
    else:
        mode = "staged"
        files = changed_files_staged()
        commit = None

    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path, matchers, mode, commit, copy))

    # De-dupe identical path/line/key/text
    deduped: list[Finding] = []
    seen: set[tuple[str, int, str, str]] = set()
    for f in findings:
        marker = (f.path, f.line, f.key, f.text.lower())
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(f)

    if args.json:
        payload = [
            {
                "path": f.path,
                "line": f.line,
                "hard_coded": f.text,
                "kind": f.kind,
                "suggested_key": f.key,
                "label": f.label,
                "example": f.replacement_example(),
            }
            for f in deduped
        ]
        safe_print(json.dumps({"findings": payload, "count": len(deduped)}, indent=2) + "\n")
    else:
        safe_print(format_report(deduped))

    if args.strict and deduped:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
