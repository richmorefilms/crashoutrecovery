"""Retention policies for compose receipt provenance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# Policy codes stored in compose_receipts.retention_policy
POLICY_DEFAULT = "default_365d"
POLICY_SENSITIVE = "sensitive_90d"
POLICY_STAFF = "staff_730d"
KNOWN_RETENTION_POLICIES = frozenset(
    {POLICY_DEFAULT, POLICY_SENSITIVE, POLICY_STAFF}
)

DEFAULT_RETENTION_DAYS = 365
SENSITIVE_RETENTION_DAYS = 90
STAFF_RETENTION_DAYS = 730


@dataclass(frozen=True)
class RetentionDecision:
    policy: str
    expires_at: str  # ISO-8601 UTC


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _expires_iso(created: datetime, days: int) -> str:
    return (created + timedelta(days=days)).isoformat()


def _flags_dict(moderation_flags: str | dict[str, Any] | None) -> dict[str, Any]:
    if moderation_flags is None:
        return {}
    if isinstance(moderation_flags, dict):
        return moderation_flags
    try:
        value = json.loads(moderation_flags)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def resolve_compose_retention(
    *,
    created_at: str | None = None,
    moderation_flags: str | dict[str, Any] | None = None,
    staff_id: int | None = None,
) -> RetentionDecision:
    """
    Choose retention for a new compose receipt.

    Priority:
      1. staff-assisted (staff_id set) → longer staff retention
      2. sensitive (e.g. blocked moderation flags) → shorter window
      3. default → standard retention
    """
    created = _parse_iso(created_at) or _utc_now()
    if staff_id is not None:
        return RetentionDecision(
            policy=POLICY_STAFF,
            expires_at=_expires_iso(created, STAFF_RETENTION_DAYS),
        )
    flags = _flags_dict(moderation_flags)
    if flags.get("blocked"):
        return RetentionDecision(
            policy=POLICY_SENSITIVE,
            expires_at=_expires_iso(created, SENSITIVE_RETENTION_DAYS),
        )
    return RetentionDecision(
        policy=POLICY_DEFAULT,
        expires_at=_expires_iso(created, DEFAULT_RETENTION_DAYS),
    )
