"""Database-first Composer suggestions with bounded assisted gap filling."""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

import jwt

import team_model
from app.compose_schemas import (
    ComposeResponse,
    ComposeSuggestion,
    PredictorResponse,
)
from app.config import JWT_ALGORITHM, JWT_SECRET
from app.db import get_conn, insert_compose_receipt
from app.retention import resolve_compose_retention
from app.suggest_engine import build_suggestion, detect_tone

_RECEIPT_TTL_SECONDS = 15 * 60
COMPOSE_ENGINE_VERSION = "1"
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,63}", re.IGNORECASE)
_IRREVERSIBLE_RE = re.compile(
    r"\b(delete|deleting|deleted|nuke|quit|burn|destroy|wipe)\w*\b",
    re.IGNORECASE,
)
_HIGH_RISK_RE = re.compile(
    r"\b(delete|nuke|quit|burn|destroy|reply[- ]?all|forever|"
    r"tell them off|post it raw|everyone|everything)\b",
    re.IGNORECASE,
)
_URGENCY_RE = re.compile(
    r"\b(right now|immediately|this second|furious|rage|meltdown|spiraling)\b",
    re.IGNORECASE,
)


class InvalidComposeReceipt(ValueError):
    """Raised when a save request cannot prove server-side provenance."""


def _text_hash(text: str) -> str:
    """Deterministic SHA-256 fingerprint of normalized text."""
    normalized = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _build_receipt_token(spike_text: str, ai_generated: bool) -> tuple[str, str]:
    """Return (JWT compose_receipt, request_id/jti)."""
    now = int(time.time())
    request_id = uuid.uuid4().hex
    token = jwt.encode(
        {
            "type": "compose_receipt",
            "text_hash": _text_hash(spike_text),
            "ai_generated": bool(ai_generated),
            "iat": now,
            "exp": now + _RECEIPT_TTL_SECONDS,
            "jti": request_id,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return token, request_id


def _issue_receipt(spike_text: str, ai_generated: bool) -> str:
    token, _request_id = _build_receipt_token(spike_text, ai_generated)
    return token


def record_compose_receipt(
    *,
    request_id: str,
    input_prompt: str,
    output_text: str,
    output_hash: str,
    tone: str | None = None,
    model_name: str | None = None,
    parameters_json: str | None = None,
    moderation_flags: str | None = None,
    user_id: int | None = None,
    staff_id: int | None = None,
    engine_version: str = COMPOSE_ENGINE_VERSION,
    created_at: str | None = None,
    path: Path | None = None,
) -> int:
    """Persist compose provenance with retention fields. Monkeypatchable for unit tests."""
    decision = resolve_compose_retention(
        created_at=created_at,
        moderation_flags=moderation_flags,
        staff_id=staff_id,
    )
    return insert_compose_receipt(
        request_id=request_id,
        input_prompt=input_prompt,
        output_text=output_text,
        output_hash=output_hash,
        engine_version=engine_version,
        tone=tone,
        model_name=model_name,
        parameters_json=parameters_json,
        moderation_flags=moderation_flags,
        user_id=user_id,
        staff_id=staff_id,
        created_at=created_at,
        expires_at=decision.expires_at,
        retention_policy=decision.policy,
        path=path,
    )


def verify_compose_receipt(receipt: str, spike_text: str) -> bool:
    try:
        payload = jwt.decode(receipt, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidComposeReceipt("Invalid or expired compose receipt") from exc
    if payload.get("type") != "compose_receipt":
        raise InvalidComposeReceipt("Invalid compose receipt")
    if payload.get("text_hash") != _text_hash(spike_text):
        raise InvalidComposeReceipt("Compose receipt does not match spike_text")
    return bool(payload.get("ai_generated"))


def _tokens(text: str) -> list[str]:
    ignored = {
        "and",
        "are",
        "but",
        "for",
        "from",
        "have",
        "just",
        "that",
        "the",
        "this",
        "with",
        "you",
        "your",
    }
    return list(dict.fromkeys(
        token.lower()
        for token in _WORD_RE.findall(text)
        if token.lower() not in ignored
    ))[:12]


def _load_json_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _find_curated_matches(spike_text: str) -> list[dict[str, Any]]:
    tokens = _tokens(spike_text)
    if not tokens:
        return []

    placeholders = ",".join("?" for _ in tokens)
    like_clauses = " OR ".join(
        "(lower(c.episode_title) LIKE ? ESCAPE '\\' "
        "OR lower(c.commentary) LIKE ? ESCAPE '\\')"
        for _ in tokens[:5]
    )
    params: list[Any] = [*tokens]
    for token in tokens[:5]:
        escaped = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.extend((f"%{escaped}%", f"%{escaped}%"))

    query = f"""
        SELECT DISTINCT c.*
        FROM crashout_database c
        LEFT JOIN crashout_tags t ON t.crashout_id = c.id
        WHERE t.tag IN ({placeholders}) OR {like_clauses}
        ORDER BY c.ai_generated ASC, c.created_at DESC
        LIMIT 5
    """
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def _soften_text(text: str) -> str:
    softened = _IRREVERSIBLE_RE.sub("pause", text)
    softened = re.sub(r"\bforever\b", "for now", softened, flags=re.IGNORECASE)
    softened = re.sub(r"!{2,}", "!", softened)
    return re.sub(r"\s+", " ", softened).strip()


def _assisted_rewrites(
    spike_text: str,
    model: dict[str, Any],
) -> list[ComposeSuggestion]:
    templates = (model.get("composer_pipeline") or {}).get("rewrite_templates") or []
    softened = _soften_text(spike_text)
    suggestions: list[ComposeSuggestion] = []
    for item in templates[:3]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        template = str(item.get("template") or "").strip()
        if not label or "{softened_text}" not in template:
            continue
        suggestions.append(
            ComposeSuggestion(
                label=label,
                text=template.replace("{softened_text}", softened),
                source="AI-assisted",
            )
        )
    return suggestions


def _curated_suggestions(
    matches: list[dict[str, Any]],
    field: str,
    labels: list[str],
) -> list[ComposeSuggestion]:
    suggestions: list[ComposeSuggestion] = []
    seen: set[str] = set()
    for row in matches:
        for text in _load_json_list(row.get(field)):
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                ComposeSuggestion(
                    label=labels[len(suggestions) % len(labels)],
                    text=text,
                    source="staff-curated",
                    crashout_id=int(row["id"]),
                )
            )
            if len(suggestions) >= 3:
                return suggestions
    return suggestions


def _predict(
    spike_text: str,
    safe_move: str,
    model: dict[str, Any],
) -> PredictorResponse:
    high_signals = len(_HIGH_RISK_RE.findall(spike_text))
    urgency_signals = len(_URGENCY_RE.findall(spike_text))
    score = high_signals * 2 + urgency_signals
    if score >= 5:
        level = "high"
    elif score >= 3:
        level = "rising"
    elif score >= 1:
        level = "steady"
    else:
        level = "low"
    reasons = (model.get("composer_pipeline") or {}).get("predictor_reasons") or {}
    reason = str(reasons.get(level) or "Keep the next move small and reversible.")
    return PredictorResponse(risk_level=level, safe_move=safe_move, reason=reason)


def build_compose_response(
    spike_text: str,
    *,
    user_id: int | None = None,
    staff_id: int | None = None,
    db_path: Path | None = None,
) -> ComposeResponse:
    """Build Composer output and persist an audit-grade compose receipt."""
    model = team_model.load_model()
    tone_result = detect_tone(spike_text, log_pattern=False)
    safety = build_suggestion(spike_text, auto_log=False)
    matches = _find_curated_matches(spike_text)

    rewrites = _curated_suggestions(
        matches,
        "tone_variations",
        ["Calm version", "Clear rewrite", "Stable phrasing"],
    )
    curated_ctas = _curated_suggestions(
        matches,
        "recovery_moves",
        ["Save draft idea", "Take safe move", "Share recovery tip"],
    )

    used_assistance = False
    if len(rewrites) < 3:
        used_assistance = True
        existing = {item.text.casefold() for item in rewrites}
        for suggestion in _assisted_rewrites(spike_text, model):
            if suggestion.text.casefold() not in existing:
                rewrites.append(suggestion)
                existing.add(suggestion.text.casefold())
            if len(rewrites) >= 3:
                break

    if len(curated_ctas) < 3:
        used_assistance = True
        fallback_moves = (
            (model.get("composer_pipeline") or {}).get("fallback_recovery_moves") or []
        )
        existing = {item.text.casefold() for item in curated_ctas}
        for move in fallback_moves:
            text = str(move).strip()
            if text and text.casefold() not in existing:
                curated_ctas.append(
                    ComposeSuggestion(
                        label=["Save draft idea", "Take safe move", "Share recovery tip"][
                            len(curated_ctas) % 3
                        ],
                        text=text,
                        source="AI-assisted",
                    )
                )
                existing.add(text.casefold())
            if len(curated_ctas) >= 3:
                break

    if safety.get("blocked"):
        safe_text = str(safety.get("suggestion") or "Pause and ask for qualified help.")
        rewrites = [
            ComposeSuggestion(
                label="Safer next step",
                text=safe_text,
                source="AI-assisted",
            )
        ]
        curated_ctas = [
            ComposeSuggestion(
                label="Pause",
                text=safe_text,
                source="AI-assisted",
            )
        ]
        used_assistance = True

    if not rewrites:
        rewrites = [
            ComposeSuggestion(
                label="Safer next step",
                text=str(safety.get("suggestion") or "Save this as a draft and pause."),
                source="AI-assisted",
            )
        ]
        used_assistance = True
    if not curated_ctas:
        curated_ctas = [
            ComposeSuggestion(
                label="Save draft idea",
                text="Save this as a draft and review it later.",
                source="AI-assisted",
            )
        ]
        used_assistance = True

    predictor = _predict(spike_text, curated_ctas[0].text, model)
    receipt_token, request_id = _build_receipt_token(spike_text, used_assistance)
    response = ComposeResponse(
        tone=str(tone_result["tone"]),
        tone_reason=str(tone_result["reason"]),
        tone_suggestions=rewrites[:3],
        cta_suggestions=curated_ctas[:3],
        predictor=predictor,
        compose_receipt=receipt_token,
        curated_matches=len(matches),
    )

    output_payload = {
        "tone": response.tone,
        "tone_reason": response.tone_reason,
        "tone_suggestions": [item.model_dump() for item in response.tone_suggestions],
        "cta_suggestions": [item.model_dump() for item in response.cta_suggestions],
        "predictor": response.predictor.model_dump(),
        "curated_matches": response.curated_matches,
    }
    output_text = json.dumps(output_payload, sort_keys=True, separators=(",", ":"))
    parameters = {
        "ai_generated": used_assistance,
        "curated_match_ids": [int(row["id"]) for row in matches if row.get("id") is not None],
    }
    flags = {"blocked": True} if safety.get("blocked") else None
    record_compose_receipt(
        request_id=request_id,
        input_prompt=spike_text,
        output_text=output_text,
        output_hash=_text_hash(output_text),
        tone=response.tone,
        model_name="compose_engine",
        parameters_json=json.dumps(parameters, sort_keys=True, separators=(",", ":")),
        moderation_flags=(
            json.dumps(flags, sort_keys=True, separators=(",", ":")) if flags else None
        ),
        user_id=user_id,
        staff_id=staff_id,
        path=db_path,
    )
    return response
