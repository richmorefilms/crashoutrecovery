"""
Suggestion engine — integrates Crashout Recovery tone detection
with the Team-Guided Micro-Model pipeline.
"""

from __future__ import annotations

import random
import re
from typing import Any

import team_model
from app.decision_flow import explain_match
from app.tones import TONE_TEMPLATES

# Maps detected tone → team decision_pattern action suffix
TONE_TO_ACTION = {
    "universal": "suggest_tone_universal",
    "calm": "suggest_tone_calm",
    "humorous": "suggest_tone_humorous",
    "direct": "suggest_tone_direct",
    "strategic": "suggest_tone_strategic",
}

# Fallback redirects when no example matches (loaded from team model at runtime)
TONE_OPENERS = {
    "universal": "That spike is real — and temporary.",
    "calm": "Take a breath. The moment feels sharp, but it will soften.",
    "humorous": "Whoa there — let's holster the dynamite.",
    "direct": "This moment feels intense. Don't make an irreversible move.",
    "strategic": "This spike is data. Use it, don't let it use you.",
}


def detect_tone(text: str, *, log_pattern: bool = True) -> dict[str, Any]:
    """
    Detect Crashout Recovery tone from user text.

    Priority (first match wins):
      humorous → direct → strategic → calm → universal

    Uses regex rules in app/decision_flow.py (same as client-side JS).
    """
    result = explain_match(text)
    if log_pattern:
        team_model.log_pattern(
            {
                "type": "tone_detection",
                "tone": result["tone"],
                "matched": result["matched"],
                "reason": result["reason"],
                "input_preview": (text or "")[:120],
            }
        )
    return result


def _word_overlap(a: str, b: str) -> float:
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a), len(words_b))


def _find_best_example(
    text: str,
    tone: str,
    model: dict[str, Any],
) -> dict[str, Any] | None:
    pools: list[dict[str, Any]] = []
    pools.extend(team_model.get_all_example_responses(model))
    pools.extend([ex for ex in model.get("training_examples", []) if ex.get("approved")])

    tone_examples = [ex for ex in pools if ex.get("tone") == tone]
    if not tone_examples:
        tone_examples = pools

    best = None
    best_score = 0.0
    for ex in tone_examples:
        for candidate in (ex.get("input", ""), ex.get("trigger", "")):
            if not candidate:
                continue
            score = _word_overlap(text, candidate)
            if score > best_score:
                best_score = score
                best = ex

    if best and best_score >= 0.15:
        return {**best, "match_score": round(best_score, 2)}
    return None


def _get_pattern_redirect(tone: str, model: dict[str, Any]) -> str | None:
    action = TONE_TO_ACTION.get(tone, "suggest_tone_universal")
    for pattern in model.get("decision_patterns", []):
        if pattern.get("action") == action:
            return pattern.get("redirect")
    return None


def apply_crashout_redirect(text: str, tone: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build a tone-specific redirect using team examples, decision patterns,
    and stance templates. Does not invent new team opinions.
    """
    model = model or team_model.load_model()
    templates = model.get("stance_templates", {})

    example = _find_best_example(text, tone, model)
    if example:
        return {
            "source": "example",
            "example_id": example.get("id"),
            "match_score": example.get("match_score"),
            "draft": example.get("response", ""),
        }

    pattern_redirect = _get_pattern_redirect(tone, model)
    opener = TONE_OPENERS.get(tone, TONE_OPENERS["universal"])
    redirect_line = pattern_redirect or team_model.pick_stance_template("redirect", templates, model, tone)
    closing = team_model.pick_stance_template("closing", templates, model, tone)

    draft = f"{opener} {redirect_line} {closing}"
    return {
        "source": "pattern_template",
        "example_id": None,
        "match_score": None,
        "draft": draft.strip(),
    }


def attach_cta(text: str, tone: str, model: dict[str, Any] | None = None) -> str:
    """Attach a tone-specific CTA after redirect logic, before alignment."""
    return team_model.attach_cta(text, tone, model)


def run_team_alignment(
    draft: str,
    context: str,
    tone: str,
    model: dict[str, Any] | None = None,
    *,
    log_pattern: bool = True,
) -> dict[str, Any]:
    """
    Run team_model alignment: topic rules, opinion lookup, gap-fill, tone align.
    """
    model = model or team_model.load_model()

    topic_check = team_model.apply_topic_rules(f"{context} {draft}", model)
    opinion_check = team_model.apply_team_opinion("crashout_impulse", context, model)
    filled = team_model.fill_missing_context(
        draft,
        context,
        model,
        tone=tone,
        log_patterns=log_pattern,
    )
    aligned_draft = filled["filled"]

    log_entry: dict[str, Any] = {
        "type": "team_alignment",
        "tone": tone,
        "topic_status": topic_check.get("status"),
        "opinion_found": opinion_check.get("found"),
        "example_id": filled.get("matched_example_id"),
        "parts_filled": filled.get("parts_missing"),
        "escalate": topic_check.get("escalate") or opinion_check.get("escalate"),
    }
    if filled.get("placeholder_filled"):
        log_entry["placeholder_filled"] = True
    if log_pattern:
        team_model.log_pattern(log_entry)

    return {
        "topic_check": topic_check,
        "opinion_check": opinion_check,
        "fill_result": filled,
        "tone_check": filled.get("tone_alignment"),
        "aligned_draft": aligned_draft,
    }


def finalize_suggestion(
    aligned_draft: str,
    context: str,
    model: dict[str, Any] | None = None,
    *,
    log_pattern: bool = True,
) -> dict[str, Any]:
    """Final team check, trim, and approve flag."""
    model = model or team_model.load_model()
    final = team_model.check_response(
        aligned_draft,
        context,
        model,
        log_patterns=log_pattern,
    )

    if final.get("escalate") and log_pattern:
        team_model.log_pattern(
            {
                "type": "escalation",
                "context_preview": context[:120],
                "messages": final.get("escalation_messages"),
                "safe_to_send": final.get("safe_to_send"),
            }
        )

    return final


def build_suggestion(text: str, auto_log: bool = True) -> dict[str, Any]:
    """
    Full /api/suggest pipeline:
      topic detection → blocks → overrides → shaping
      → tone → crashout redirect → alignment → finalize → training log
    """
    model = team_model.load_model()
    context = text or ""

    # 1. Topic detection
    topic_detection = team_model.detect_topic(context, model)

    # 2. Hard blocks
    block_result = team_model.apply_topic_blocks(context, model)
    if block_result["blocked"]:
        safe = block_result["safe_redirect"]
        finalized = finalize_suggestion(safe, context, model, log_pattern=auto_log)
        result = {
            "tone": "universal",
            "matched": False,
            "reason": f"Blocked topic: {block_result.get('matched_topic')}",
            "fragment": TONE_TEMPLATES["universal"],
            "suggestion": finalized["aligned"],
            "aligned": finalized["aligned"],
            "safe_to_send": True,
            "blocked": True,
            "escalate": block_result.get("escalate", True),
            "topic_status": "blocked",
            "topic_classification": topic_detection.get("classification"),
            "team_opinion_id": None,
            "example_id": None,
            "override_id": None,
            "invented_stance": False,
            "pipeline": {
                "step": "blocked",
                "topic_detection": topic_detection,
                "block_result": block_result,
                "final_check": finalized,
            },
        }
        return result

    # 3. Topic overrides — team-defined custom response
    override = team_model.apply_topic_overrides(context, model)
    if override.get("matched") and override.get("response"):
        tone = override.get("tone", "universal")
        draft = override["response"]
        alignment = run_team_alignment(
            draft, context, tone, model, log_pattern=auto_log
        )
        finalized = finalize_suggestion(
            alignment["aligned_draft"], context, model, log_pattern=auto_log
        )
        result = {
            "tone": tone,
            "matched": True,
            "reason": f"Topic override: {override.get('topic')}",
            "fragment": TONE_TEMPLATES.get(tone, TONE_TEMPLATES["universal"]),
            "suggestion": finalized["aligned"],
            "aligned": finalized["aligned"],
            "safe_to_send": finalized.get("safe_to_send", False),
            "blocked": False,
            "escalate": finalized.get("escalate", False),
            "topic_status": "override",
            "topic_classification": "override",
            "override_id": override.get("override_id"),
            "team_opinion_id": alignment["opinion_check"].get("opinion_id"),
            "example_id": None,
            "redirect_source": "topic_override",
            "invented_stance": False,
            "pipeline": {
                "topic_detection": topic_detection,
                "topic_override": override,
                "team_alignment": alignment,
                "final_check": finalized,
            },
        }
        if auto_log:
            team_model.log_suggestion_for_training(context, result)
        return result

    # 4. Topic shaping constraints
    shaping = team_model.apply_topic_shaping(context, model)
    topic_rules = team_model.apply_topic_rules(context, model)

    # 5. Tone detection
    tone_result = detect_tone(context, log_pattern=auto_log)
    tone = tone_result["tone"]

    # 6. Crashout redirect draft + CTA
    redirect = apply_crashout_redirect(context, tone, model)
    draft = attach_cta(redirect["draft"], tone, model)

    if shaping.get("matched") and shaping.get("shaped_prefix"):
        draft = f"{shaping['shaped_prefix']} {draft}"

    # 7. Team alignment
    alignment = run_team_alignment(
        draft, context, tone, model, log_pattern=auto_log
    )

    # 8. Final check
    finalized = finalize_suggestion(
        alignment["aligned_draft"], context, model, log_pattern=auto_log
    )

    result = {
        "tone": tone,
        "matched": tone_result["matched"],
        "reason": tone_result["reason"],
        "fragment": TONE_TEMPLATES[tone],
        "suggestion": finalized["aligned"],
        "aligned": finalized["aligned"],
        "safe_to_send": finalized.get("safe_to_send", False),
        "blocked": False,
        "escalate": finalized.get("escalate", False),
        "topic_status": topic_rules.get("status"),
        "topic_classification": topic_detection.get("classification"),
        "shaping_id": shaping.get("shaping_id"),
        "team_opinion_id": alignment["opinion_check"].get("opinion_id"),
        "example_id": redirect.get("example_id") or alignment["fill_result"].get("matched_example_id"),
        "override_id": None,
        "redirect_source": redirect.get("source"),
        "invented_stance": False,
        "growth": {
            "logged_for_training": True,
            "model_stage": model.get("growth_metadata", {}).get("model_stage", "micro"),
        },
        "pipeline": {
            "topic_detection": topic_detection,
            "topic_shaping": shaping,
            "tone_detection": tone_result,
            "topic_rules": topic_rules,
            "crashout_redirect": redirect,
            "cta_attached": True,
            "team_alignment": {
                "topic_check": alignment["topic_check"],
                "opinion_check": alignment["opinion_check"],
                "fill_result": {
                    "parts_missing": alignment["fill_result"].get("parts_missing"),
                    "matched_example_id": alignment["fill_result"].get("matched_example_id"),
                    "matched_source": alignment["fill_result"].get("matched_source"),
                    "invented_stance": False,
                },
                "tone_check": alignment["tone_check"],
            },
            "final_check": {
                "approved": finalized.get("approved"),
                "safe_to_send": finalized.get("safe_to_send"),
                "escalate": finalized.get("escalate"),
                "escalation_messages": finalized.get("escalation_messages"),
            },
        },
    }

    # 9. Auto-log for training review
    if auto_log:
        team_model.log_suggestion_for_training(context, result)
    return result


def preview_suggestion(text: str, proposed: str | None = None) -> dict[str, Any]:
    """Preview alignment without saving training logs."""
    if not proposed:
        return build_suggestion(text, auto_log=False)

    model = team_model.load_model()
    topic_detection = team_model.detect_topic(text, model)
    block = team_model.apply_topic_blocks(text, model)
    override = team_model.apply_topic_overrides(text, model)
    shaping = team_model.apply_topic_shaping(text, model)
    filled = team_model.fill_missing_context(proposed, text, model)
    final = team_model.check_response(filled["filled"], text, model)
    return {
        "mode": "proposed_response",
        "preview": final.get("aligned"),
        "safe_to_send": final.get("safe_to_send"),
        "topic_detection": topic_detection,
        "topic_block": block,
        "topic_override": override,
        "topic_shaping": shaping,
        "fill_result": filled,
        "final_check": final,
    }
