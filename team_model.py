"""
Team-Guided Micro-Model helper module.

Loads all team opinions, values, tone, and topic rules from team_model.json.
Never hardcode subjective team content in Python — edit the JSON file.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import EXAMPLE_PACK_PATH, FINETUNE_EXPORT_PATH, PATTERN_LOG_PATH, TEAM_MODEL_PATH, TRAINING_LOG_PATH

_model_cache: dict[str, Any] | None = None
_example_pack_cache: list[dict[str, Any]] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_example_pack() -> list[dict[str, Any]]:
    """Load modular example pack from data/language_pack_examples.json."""
    global _example_pack_cache
    if _example_pack_cache is not None:
        return _example_pack_cache
    pack_path = Path(EXAMPLE_PACK_PATH)
    if not pack_path.exists():
        _example_pack_cache = []
        return _example_pack_cache
    with pack_path.open(encoding="utf-8") as f:
        data = json.load(f)
    _example_pack_cache = data.get("example_responses", [])
    return _example_pack_cache


def get_all_example_responses(model: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Core + language-pack examples, deduped by id."""
    model = model or load_model()
    base = list(model.get("example_responses", []))
    seen = {e.get("id") for e in base if isinstance(e, dict)}
    for item in _load_example_pack():
        if isinstance(item, dict) and item.get("id") not in seen:
            base.append(item)
            seen.add(item.get("id"))
    return base


def load_model(force_reload: bool = False) -> dict[str, Any]:
    """Load team_model.json. Cached until force_reload=True."""
    global _model_cache, _example_pack_cache
    if _model_cache is not None and not force_reload:
        return _model_cache

    if force_reload:
        _example_pack_cache = None

    path = Path(TEAM_MODEL_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Team model not found: {path}")

    with path.open(encoding="utf-8") as f:
        _model_cache = json.load(f)
    return _model_cache


def save_model(model: dict[str, Any]) -> dict[str, Any]:
    """Persist team_model.json and refresh cache."""
    global _model_cache
    model["updated_at"] = _now_iso()[:10]
    path = Path(TEAM_MODEL_PATH)
    with path.open("w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)
        f.write("\n")
    _model_cache = model
    return model


def log_pattern(entry: dict[str, Any]) -> None:
    """Append a pattern observation for future model expansion."""
    path = Path(PATTERN_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"logged_at": _now_iso(), **entry}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def resolve_placeholders(text: str, model: dict[str, Any] | None = None) -> tuple[str, bool]:
    """Replace {key} placeholders using missing_context_rules before tone alignment."""
    model = model or load_model()
    rules = model.get("missing_context_rules", {})
    placeholders: dict[str, list[str]] = {}

    if isinstance(rules.get("placeholders"), dict):
        placeholders.update(rules["placeholders"])

    for key, options in rules.items():
        if key in (
            "allow_ai_phrasing",
            "invent_stances",
            "fill_order",
            "required_parts",
            "optional_parts",
            "acknowledge_signals",
            "redirect_signals",
            "placeholders",
        ):
            continue
        if isinstance(options, list) and options and all(isinstance(o, str) for o in options):
            placeholders[key] = options

    result = text
    had_unresolved = False
    for key, options in placeholders.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            had_unresolved = True
            result = result.replace(placeholder, random.choice(options))

    return result, had_unresolved


def pick_stance_template(
    key: str,
    templates: dict[str, Any] | None = None,
    model: dict[str, Any] | None = None,
    tone: str | None = None,
) -> str:
    """Return a stance template string; tone-aware when variants exist."""
    model = model or load_model()
    templates = templates or model.get("stance_templates", {})
    value = templates.get(key, "")
    if not isinstance(value, list):
        return str(value) if value else ""
    if not value:
        return ""

    if tone:
        pack = model.get("tone_vocabulary", {}).get(tone, {})
        phrases = [p.lower() for p in pack.get("phrases", [])]
        if phrases:
            scored = [(sum(1 for p in phrases if p in tmpl.lower()), tmpl) for tmpl in value]
            best = max(s[0] for s in scored)
            if best > 0:
                value = [t for s, t in scored if s == best]

    return random.choice(value)


def _build_cta_pool(tone: str, model: dict[str, Any]) -> list[str]:
    """Assemble tone-scoped CTA candidates from call_to_actions, cta_vocabulary, platform_identity."""
    pool: list[str] = []
    pool.extend(model.get("call_to_actions", {}).get(tone, []))
    pool.extend(model.get("call_to_actions", {}).get("universal", []))

    cta_vocab = model.get("cta_vocabulary", {})
    pool.extend(cta_vocab.get("micro_actions", []))
    pool.extend(cta_vocab.get("momentum_actions", []))
    pool.extend(cta_vocab.get("community_actions", []))

    platform = model.get("platform_identity", {})
    pool.extend(platform.get("brand_phrases", []))

    tone_pack = model.get("tone_vocabulary", {}).get(tone, {})
    for phrase in tone_pack.get("phrases", []):
        if phrase and phrase[0].isupper():
            pool.append(phrase)
        else:
            pool.append(phrase[0].upper() + phrase[1:] + ".")

    seen: set[str] = set()
    unique: list[str] = []
    for item in pool:
        normalized = item.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(item.strip())
    return unique


def attach_cta(text: str, tone: str, model: dict[str, Any] | None = None) -> str:
    """Append a tone-specific call-to-action from merged CTA vocabulary."""
    model = model or load_model()
    pool = _build_cta_pool(tone, model)
    if not pool:
        return text
    cta = random.choice(pool)
    if not cta.endswith((".", "!", "?")):
        cta = cta + "."
    if cta.lower().rstrip(".") in text.lower():
        return text
    return f"{text.rstrip()} {cta}".strip()


def _apply_platform_phrasing_swaps(text: str, model: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    """Apply vocabulary phrasing_swaps (includes platform-aware rewrites)."""
    vocab = model.get("vocabulary", {})
    aligned = text
    changes: list[dict[str, str]] = []

    for old, new in vocab.get("phrasing_swaps", {}).items():
        if old and old.lower() in aligned.lower():
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            aligned = pattern.sub(new, aligned)
            changes.append({"from": old, "to": new})
    return aligned, changes


def _apply_tone_vocabulary(text: str, tone: str | None, model: dict[str, Any]) -> tuple[str, list[str]]:
    """Flag or lightly enrich text with tone-scoped vocabulary markers."""
    flags: list[str] = []
    if not tone:
        return text, flags

    pack = model.get("tone_vocabulary", {}).get(tone) or model.get("tone_vocabulary", {}).get("universal", {})
    phrases = pack.get("phrases", [])
    if phrases and not any(p.lower() in text.lower() for p in phrases):
        flags.append(f"missing_tone_phrase:{tone}")
    return text, flags


def log_training(entry: dict[str, Any]) -> None:
    """Append a training example for future expansion."""
    path = Path(TRAINING_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"logged_at": _now_iso(), **entry}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _contains_any(text: str, terms: list[str]) -> str | None:
    normalized = _normalize(text)
    for term in terms:
        if _normalize(term) in normalized:
            return term
    return None


def _contains_keywords(text: str, keywords: list[str]) -> str | None:
    normalized = _normalize(text)
    for kw in keywords:
        if _normalize(kw) in normalized:
            return kw
    return None


def _match_topic_entries(text: str, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = _normalize(text)
    for entry in entries:
        topic = entry.get("topic", "")
        if topic and _normalize(topic) in normalized:
            return entry
        keywords = entry.get("keywords", [])
        hit = _contains_keywords(text, keywords)
        if hit:
            return {**entry, "matched_keyword": hit}
    return None


def detect_topic(text: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect topic classification: block, override, shaping, allowed, or unknown."""
    model = model or load_model()

    block = apply_topic_blocks(text, model)
    if block.get("blocked"):
        return {"classification": "blocked", **block}

    override = apply_topic_overrides(text, model)
    if override.get("matched"):
        return {"classification": "override", **override}

    shaping = apply_topic_shaping(text, model)
    if shaping.get("matched"):
        return {"classification": "shaping", **shaping}

    legacy = apply_topic_rules(text, model)
    if legacy.get("status") == "allowed":
        return {"classification": "allowed", **legacy}

    return {"classification": "unknown", "status": "unknown", "matched_topic": None}


def apply_topic_overrides(text: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return team-defined custom response for a matching topic override."""
    model = model or load_model()
    entry = _match_topic_entries(text, model.get("topic_overrides", []))
    if not entry:
        return {"matched": False, "topic": None, "response": None, "tone": None}

    return {
        "matched": True,
        "override_id": entry.get("id"),
        "topic": entry.get("topic"),
        "response": entry.get("response"),
        "tone": entry.get("tone", "universal"),
        "confidence": entry.get("confidence", 1.0),
        "source": entry.get("source", "team"),
    }


def apply_topic_blocks(text: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hard block with safe redirect. Checks topic_blocks then legacy topics.blocked."""
    model = model or load_model()
    templates = model.get("stance_templates", {})

    entry = _match_topic_entries(text, model.get("topic_blocks", []))
    if entry:
        return {
            "blocked": True,
            "status": "blocked",
            "matched_topic": entry.get("topic"),
            "block_id": entry.get("id"),
            "safe_redirect": entry.get("safe_redirect") or templates.get("blocked_topic"),
            "escalate": entry.get("escalate", True),
        }

    legacy_hit = _contains_any(text, model.get("topics", {}).get("blocked", []))
    if legacy_hit:
        return {
            "blocked": True,
            "status": "blocked",
            "matched_topic": legacy_hit,
            "block_id": None,
            "safe_redirect": templates.get("blocked_topic"),
            "escalate": True,
        }

    for item in model.get("topics", {}).get("conditional", []):
        if not item.get("allowed", True) and item.get("topic"):
            if _normalize(item["topic"]) in _normalize(text):
                return {
                    "blocked": True,
                    "status": "blocked",
                    "matched_topic": item["topic"],
                    "safe_redirect": item.get("constraint") or templates.get("blocked_topic"),
                    "escalate": True,
                }

    return {"blocked": False, "status": "clear", "matched_topic": None, "safe_redirect": None, "escalate": False}


def apply_topic_shaping(text: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply constraints for allowed topics that need shaping."""
    model = model or load_model()
    templates = model.get("stance_templates", {})

    entry = _match_topic_entries(text, model.get("topic_shaping", []))
    if entry:
        return {
            "matched": True,
            "shaping_id": entry.get("id"),
            "topic": entry.get("topic"),
            "constraint": entry.get("constraint"),
            "prepend": entry.get("prepend", True),
            "shaped_prefix": templates.get("conditional_topic", "Keeping it practical: {constraint_redirect}").replace(
                "{constraint_redirect}", entry.get("constraint", "")
            ),
        }

    for item in model.get("topics", {}).get("conditional", []):
        if item.get("allowed", True) and item.get("topic"):
            if _normalize(item["topic"]) in _normalize(text):
                return {
                    "matched": True,
                    "shaping_id": None,
                    "topic": item["topic"],
                    "constraint": item.get("constraint"),
                    "prepend": True,
                    "shaped_prefix": templates.get("conditional_topic", "").replace(
                        "{constraint_redirect}", item.get("constraint", "")
                    ),
                }

    return {"matched": False, "topic": None, "constraint": None, "shaped_prefix": None}


def _increment_growth(model: dict[str, Any], field: str, amount: int = 1) -> None:
    meta = model.setdefault("growth_metadata", {})
    meta[field] = meta.get(field, 0) + amount
    meta["last_trained_at"] = _now_iso()[:10]


def apply_topic_rules(text: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Evaluate text against allowed, blocked, and conditional topics.

    Returns:
        status: allowed | blocked | conditional | unknown
        matched_topic, constraint, redirect guidance
    """
    model = model or load_model()
    topics = model.get("topics", {})

    blocked_hit = _contains_any(text, topics.get("blocked", []))
    if blocked_hit:
        return {
            "status": "blocked",
            "matched_topic": blocked_hit,
            "constraint": None,
            "message": model.get("stance_templates", {}).get(
                "blocked_topic",
                "Can't go there. Pause, write privately, pick one small next step.",
            ),
            "escalate": True,
        }

    for item in topics.get("conditional", []):
        topic = item.get("topic", "")
        if topic and _normalize(topic) in _normalize(text):
            allowed = item.get("allowed", True)
            return {
                "status": "conditional" if allowed else "blocked",
                "matched_topic": topic,
                "constraint": item.get("constraint"),
                "message": item.get("constraint"),
                "escalate": not allowed,
            }

    allowed_hit = _contains_any(text, topics.get("allowed", []))
    if allowed_hit:
        return {
            "status": "allowed",
            "matched_topic": allowed_hit,
            "constraint": None,
            "message": None,
            "escalate": False,
        }

    return {
        "status": "unknown",
        "matched_topic": None,
        "constraint": None,
        "message": None,
        "escalate": False,
    }


def block_topic(text: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """Enforce blocking rules. Returns blocked flag and safe redirect."""
    result = apply_topic_blocks(text, model)
    return result


def apply_team_opinion(
    topic: str,
    context: str = "",
    model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Find the best matching team opinion for a topic or context string.
    Does not invent opinions — returns None stance if no match.
    """
    model = model or load_model()
    opinions = sorted(
        model.get("team_opinions", []),
        key=lambda o: o.get("priority", 99),
    )

    search = _normalize(f"{topic} {context}")
    best = None
    for opinion in opinions:
        opinion_topic = _normalize(opinion.get("topic", ""))
        if opinion_topic and opinion_topic in search:
            best = opinion
            break
        stance = _normalize(opinion.get("stance", ""))
        if stance and any(word in search for word in stance.split()[:4]):
            best = opinion
            break

    if best:
        return {
            "found": True,
            "opinion_id": best.get("id"),
            "topic": best.get("topic"),
            "stance": best.get("stance"),
            "source": "team_model",
        }

    escalation = next(
        (r for r in model.get("escalation_rules", []) if r.get("condition") == "no_matching_opinion"),
        None,
    )
    return {
        "found": False,
        "opinion_id": None,
        "topic": topic,
        "stance": None,
        "source": "none",
        "escalate": True,
        "escalation_message": escalation.get("message") if escalation else "Ask team for input.",
    }


def align_tone(
    text: str,
    model: dict[str, Any] | None = None,
    tone: str | None = None,
) -> dict[str, Any]:
    """
    Normalize AI output to match team tone: vocabulary swaps, avoid-list flags,
    tone_vocabulary markers, and platform identity phrasing.
    """
    model = model or load_model()
    team_tone = model.get("team_tone", {})
    vocab = model.get("vocabulary", {})
    aligned = text
    changes: list[dict[str, str]] = []
    flags: list[str] = []

    aligned, platform_changes = _apply_platform_phrasing_swaps(aligned, model)
    changes.extend(platform_changes)

    for rule in vocab.get("phrasing_rules", []):
        old = rule.get("replace", "")
        new = rule.get("with", "")
        if old and old in aligned.lower():
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            aligned = pattern.sub(new, aligned)
            changes.append({"from": old, "to": new})

    aligned, tone_flags = _apply_tone_vocabulary(aligned, tone, model)
    flags.extend(tone_flags)

    for term in vocab.get("avoid", []):
        if term.lower() in aligned.lower():
            flags.append(f"avoid_term:{term}")

    for term in vocab.get("banned_terms", []):
        if term.lower() in aligned.lower():
            flags.append(f"banned_term:{term}")

    preferred = set(vocab.get("preferred", []) + vocab.get("preferred_terms", []))
    platform_nouns = model.get("platform_identity", {}).get("nouns", [])
    preferred.update(platform_nouns)
    if tone:
        tone_pack = model.get("tone_vocabulary", {}).get(tone, {})
        preferred.update(tone_pack.get("nouns", []))

    for term in team_tone.get("avoid", []):
        if term.lower() in aligned.lower():
            flags.append(f"tone_avoid:{term}")

    sentences = re.split(r"(?<=[.!?])\s+", aligned.strip())
    max_sentences = team_tone.get("max_sentences", 6)
    truncated = len(sentences) > max_sentences
    if truncated:
        aligned = " ".join(sentences[:max_sentences])

    return {
        "original": text,
        "aligned": aligned.strip(),
        "changes": changes,
        "flags": flags,
        "truncated": truncated,
        "voice": team_tone.get("voice"),
        "tone": tone,
    }


def fill_missing_context(
    partial_response: str,
    context: str = "",
    model: dict[str, Any] | None = None,
    tone: str | None = None,
    *,
    log_patterns: bool = True,
) -> dict[str, Any]:
    """
    Fill gaps using missing_context_rules — templates and examples only.
    AI may phrase — never invent new team stances.
    """
    model = model or load_model()
    rules = model.get("missing_context_rules", {})
    templates = model.get("stance_templates", {})
    filled = partial_response.strip()
    parts_missing: list[str] = []
    matched_source = None
    matched_id = None

    ack_signals = rules.get("acknowledge_signals", ["real", "yeah", "that", "frustration"])
    redirect_signals = rules.get("redirect_signals", ["try", "before", "step", "pause", "one "])

    has_ack = any(w in filled.lower() for w in ack_signals)
    has_redirect = any(w in filled.lower() for w in redirect_signals)

    if not has_ack:
        parts_missing.append("acknowledge")
        override = apply_topic_overrides(context, model)
        if override.get("matched") and override.get("response"):
            filled = override["response"]
            matched_source = "topic_override"
            matched_id = override.get("override_id")
        else:
            filled = f"{pick_stance_template('acknowledge', templates, model, tone)} {filled}"

    if not has_redirect and matched_source != "topic_override":
        parts_missing.append("redirect")
        fill_order = rules.get("fill_order", ["example_responses", "stance_templates"])
        for source in fill_order:
            if source == "example_responses":
                for ex in get_all_example_responses(model):
                    ctx = _normalize(context)
                    ex_input = _normalize(ex.get("input", ""))
                    ex_trigger = _normalize(ex.get("trigger", ""))
                    if ctx and (
                        (ex_input and (ex_input in ctx or ctx in ex_input))
                        or (ex_trigger and ex_trigger in ctx)
                    ):
                        filled = f"{filled} {ex.get('response', '')}"
                        matched_source = "example_responses"
                        matched_id = ex.get("id")
                        break
            elif source == "training_examples" and not matched_source:
                for ex in model.get("training_examples", []):
                    if ex.get("approved") and _normalize(ex.get("input", "")) in _normalize(context):
                        filled = f"{filled} {ex.get('response', '')}"
                        matched_source = "training_examples"
                        matched_id = ex.get("id")
                        break
            elif source == "stance_templates" and not matched_source:
                filled = f"{filled} {pick_stance_template('redirect', templates, model, tone)}"
                matched_source = "stance_templates"

    if "closing" in rules.get("optional_parts", ["closing"]):
        ender_key = "momentum" if templates.get("momentum") and random.random() < 0.5 else "closing"
        ender = pick_stance_template(ender_key, templates, model, tone)
        if ender and ender.lower() not in filled.lower():
            filled = f"{filled.rstrip()}. {ender}" if not filled.rstrip().endswith(".") else f"{filled.rstrip()} {ender}"

    original_before_placeholders = filled
    filled, placeholder_filled = resolve_placeholders(filled, model)

    tone_result = align_tone(filled, model, tone=tone)

    if log_patterns and (
        placeholder_filled or "{feeling}" in original_before_placeholders
    ):
        log_pattern(
            {
                "type": "placeholder_fill",
                "placeholder_filled": True,
                "context_preview": context[:120],
            }
        )

    return {
        "partial": partial_response,
        "filled": tone_result["aligned"],
        "parts_missing": parts_missing,
        "matched_example_id": matched_id,
        "matched_source": matched_source,
        "placeholder_filled": placeholder_filled,
        "invented_stance": False,
        "note": "Phrasing filled from templates/examples only. No new opinions invented.",
        "tone_alignment": tone_result,
    }


def check_response(
    proposed_response: str,
    context: str = "",
    model: dict[str, Any] | None = None,
    *,
    log_patterns: bool = True,
) -> dict[str, Any]:
    """
    Full alignment pass: topic rules → team opinion → tone → escalation flags.
    """
    model = model or load_model()
    topic_result = apply_topic_rules(f"{context} {proposed_response}", model)
    opinion_result = apply_team_opinion(context or "general", context, model)
    tone_result = align_tone(proposed_response, model)

    escalate = topic_result.get("escalate") or opinion_result.get("escalate", False)
    escalation_messages = []
    if topic_result.get("status") == "blocked":
        escalation_messages.append(topic_result.get("message"))
    if opinion_result.get("escalate"):
        escalation_messages.append(opinion_result.get("escalation_message"))

    approved = topic_result.get("status") not in ("blocked",) and not tone_result.get("flags")

    if log_patterns:
        log_pattern(
            {
                "type": "check_response",
                "context_preview": context[:120],
                "approved": approved,
                "topic_status": topic_result.get("status"),
                "escalate": escalate,
            }
        )

    return {
        "approved": approved,
        "proposed": proposed_response,
        "aligned": tone_result["aligned"],
        "topic_check": topic_result,
        "opinion_check": opinion_result,
        "tone_check": tone_result,
        "escalate": escalate,
        "escalation_messages": escalation_messages,
        "safe_to_send": approved and not escalate,
    }


def update_model(updates: dict[str, Any]) -> dict[str, Any]:
    """
    Merge new team data into team_model.json.

    Supported keys: team_opinions, team_values, example_responses,
    topics (partial merge), decision_patterns, stance_templates, vocabulary.
    """
    model = load_model(force_reload=True)
    list_keys = (
        "team_opinions",
        "team_values",
        "example_responses",
        "decision_patterns",
        "escalation_rules",
        "training_examples",
        "topic_overrides",
        "topic_blocks",
        "topic_shaping",
    )

    for key in list_keys:
        if key in updates and isinstance(updates[key], list):
            existing = model.get(key, [])
            existing_ids = {item.get("id") for item in existing if isinstance(item, dict)}
            for item in updates[key]:
                if isinstance(item, dict) and item.get("id") in existing_ids:
                    model[key] = [
                        item if (isinstance(i, dict) and i.get("id") == item.get("id")) else i
                        for i in existing
                    ]
                else:
                    existing.append(item)
            model[key] = existing

    if "topics" in updates and isinstance(updates["topics"], dict):
        topics = model.setdefault("topics", {})
        for sub in ("allowed", "blocked", "conditional"):
            if sub in updates["topics"]:
                if sub == "conditional":
                    topics[sub] = updates["topics"][sub]
                else:
                    merged = set(topics.get(sub, []))
                    merged.update(updates["topics"][sub])
                    topics[sub] = sorted(merged)

    for key in (
        "stance_templates",
        "vocabulary",
        "team_tone",
        "missing_context_rules",
        "growth_metadata",
        "call_to_actions",
        "tone_vocabulary",
        "cta_vocabulary",
        "platform_identity",
    ):
        if key in updates and isinstance(updates[key], dict):
            model.setdefault(key, {}).update(updates[key])

    return save_model(model)


def promote_example(example: dict[str, Any]) -> dict[str, Any]:
    """Move an approved example into team_model.json example_responses and training_examples."""
    model = load_model(force_reload=True)
    ex_id = example.get("id") or f"ex-{int(datetime.now(timezone.utc).timestamp())}"
    entry = {
        "id": ex_id,
        "input": example.get("input", ""),
        "tone": example.get("tone", "universal"),
        "response": example.get("response", ""),
        "approved": True,
        "source": example.get("source", "team_promoted"),
        "confidence": example.get("confidence", 1.0),
        "promoted_at": _now_iso(),
    }

    responses = model.setdefault("example_responses", [])
    existing_ids = {e.get("id") for e in responses if isinstance(e, dict)}
    if ex_id not in existing_ids:
        responses.append({k: v for k, v in entry.items() if k != "approved"})

    training = model.setdefault("training_examples", [])
    training_ids = {e.get("id") for e in training if isinstance(e, dict)}
    if ex_id not in training_ids:
        training.append(entry)

    _increment_growth(model, "total_promoted")
    model["growth_metadata"]["last_promoted_at"] = _now_iso()[:10]
    save_model(model)

    log_pattern({"type": "promote_example", "example_id": ex_id, "tone": entry["tone"]})
    return {"promoted": True, "example_id": ex_id, "entry": entry}


def get_topic_rules() -> dict[str, Any]:
    """Return all topic control rules for viewing/editing."""
    model = load_model()
    return {
        "topic_overrides": model.get("topic_overrides", []),
        "topic_blocks": model.get("topic_blocks", []),
        "topic_shaping": model.get("topic_shaping", []),
        "topics_legacy": model.get("topics", {}),
    }


def update_topic_rules(updates: dict[str, Any]) -> dict[str, Any]:
    """Update topic_overrides, topic_blocks, or topic_shaping lists."""
    return update_model(updates)


def log_suggestion_for_training(text: str, result: dict[str, Any]) -> None:
    """Auto-log successful suggestions for future training review."""
    if not result.get("safe_to_send") or result.get("blocked"):
        return
    entry = {
        "input": text[:2000],
        "tone": result.get("tone", "universal"),
        "response": result.get("suggestion", result.get("aligned", ""))[:4000],
        "tags": ["auto_logged", "api_suggest"],
        "approved": False,
        "source": "api_suggest",
        "confidence": 0.7,
    }
    log_training(entry)
    model = load_model()
    _increment_growth(model, "total_suggestions_logged")
    save_model(model)


def prepare_for_finetune(include_unapproved: bool = False) -> dict[str, Any]:
    """
    Export training-ready JSONL for future fine-tuning.
    Format: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
    """
    model = load_model()
    path = Path(FINETUNE_EXPORT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []

    def add_pair(inp: str, out: str, meta: dict[str, Any]) -> None:
        if inp.strip() and out.strip():
            records.append(
                {
                    "messages": [
                        {"role": "user", "content": inp.strip()},
                        {"role": "assistant", "content": out.strip()},
                    ],
                    "metadata": meta,
                }
            )

    for ex in get_all_example_responses(model):
        add_pair(ex.get("input", ""), ex.get("response", ""), {"source": "example_responses", "id": ex.get("id")})

    for ex in model.get("training_examples", []):
        if ex.get("approved") or include_unapproved:
            add_pair(
                ex.get("input", ""),
                ex.get("response", ""),
                {"source": "training_examples", "id": ex.get("id"), "approved": ex.get("approved", False)},
            )

    for ov in model.get("topic_overrides", []):
        add_pair(
            f"[topic: {ov.get('topic')}]",
            ov.get("response", ""),
            {"source": "topic_overrides", "id": ov.get("id")},
        )

    training_path = Path(TRAINING_LOG_PATH)
    if training_path.exists():
        with training_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if include_unapproved or row.get("approved"):
                        add_pair(
                            row.get("input", ""),
                            row.get("response", ""),
                            {"source": "training_log", "logged_at": row.get("logged_at")},
                        )
                except json.JSONDecodeError:
                    continue

    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    model = load_model(force_reload=True)
    model["growth_metadata"]["last_trained_at"] = _now_iso()[:10]
    model["growth_metadata"]["total_training_examples"] = len(records)
    save_model(model)

    return {
        "exported": len(records),
        "path": str(path),
        "include_unapproved": include_unapproved,
        "format": "openai_messages_jsonl",
    }


def preview_alignment(text: str, proposed: str | None = None) -> dict[str, Any]:
    """Preview full alignment pipeline without saving."""
    from app.suggest_engine import preview_suggestion

    return preview_suggestion(text, proposed)


def train(examples: list[dict[str, Any]], promote: bool = False) -> dict[str, Any]:
    """
    Store new examples in training_log.jsonl and optionally training_examples.
    If promote=True, also promote to example_responses.
    """
    logged = []
    model = load_model(force_reload=True)

    for ex in examples:
        entry = {
            "input": ex.get("input", ""),
            "tone": ex.get("tone", "universal"),
            "response": ex.get("response", ""),
            "tags": ex.get("tags", []),
            "approved": ex.get("approved", False),
            "source": ex.get("source", "api_train"),
            "confidence": ex.get("confidence", 0.5),
            "logged_at": _now_iso(),
        }
        log_training(entry)
        logged.append(entry)

        ex_id = ex.get("id") or f"tr-{int(datetime.now(timezone.utc).timestamp())}-{len(logged)}"
        training = model.setdefault("training_examples", [])
        existing_ids = {e.get("id") for e in training if isinstance(e, dict)}
        if ex_id not in existing_ids:
            training.append({**entry, "id": ex_id})

    _increment_growth(model, "total_training_examples", len(logged))
    save_model(model)

    promoted = 0
    if promote:
        for ex in examples:
            result = promote_example(ex)
            if result.get("promoted"):
                promoted += 1

    return {
        "logged": len(logged),
        "promoted": promoted,
        "message": f"Stored {len(logged)} example(s). Promoted {promoted} to team_model.json.",
    }
