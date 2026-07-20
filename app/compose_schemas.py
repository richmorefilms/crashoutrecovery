"""Validated contracts for Composer and curated-content moderation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


SuggestionSource = Literal["staff-curated", "AI-assisted"]


class ComposeRequest(BaseModel):
    spike_text: str = Field(min_length=1, max_length=4000)

    @field_validator("spike_text")
    @classmethod
    def normalize_spike_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("spike_text must not be blank")
        return cleaned


class ComposeSuggestion(BaseModel):
    label: str
    text: str
    source: SuggestionSource
    crashout_id: int | None = None


class PredictorResponse(BaseModel):
    risk_level: Literal["low", "steady", "rising", "high"]
    safe_move: str
    reason: str


class ComposeResponse(BaseModel):
    tone: str
    tone_reason: str
    tone_suggestions: list[ComposeSuggestion]
    cta_suggestions: list[ComposeSuggestion]
    predictor: PredictorResponse
    compose_receipt: str
    curated_matches: int


class SaveSeedRequest(BaseModel):
    spike_text: str = Field(min_length=1, max_length=4000)
    suggested_rewrite: str | None = Field(default=None, max_length=2000)
    safe_move: str | None = Field(default=None, max_length=500)
    tone: str | None = Field(default=None, max_length=32)
    compose_receipt: str = Field(min_length=20, max_length=2000)

    @field_validator("spike_text")
    @classmethod
    def normalize_saved_spike(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("spike_text must not be blank")
        return cleaned


class SaveSeedResponse(BaseModel):
    status: Literal["queued"] = "queued"
    id: int


class ApproveSeedRequest(BaseModel):
    episode_title: str = Field(min_length=3, max_length=200)
    commentary: str = Field(min_length=3, max_length=4000)
    recovery_moves: list[str] = Field(default_factory=list, max_length=20)
    tone_variations: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("episode_title", "commentary")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("recovery_moves", "tone_variations")
    @classmethod
    def validate_content_items(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            if not isinstance(raw, str):
                raise ValueError("Content items must be strings")
            item = raw.strip()
            if not item or len(item) > 500:
                raise ValueError("Content items must contain 1 to 500 characters")
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                cleaned.append(item)
        return cleaned

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        cleaned = sorted({tag.strip().lower() for tag in values if tag.strip()})
        if any(len(tag) > 64 for tag in cleaned):
            raise ValueError("Tags must not exceed 64 characters")
        return cleaned


class RejectSeedRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class ModerationResult(BaseModel):
    status: Literal["approved", "rejected"]
    id: int
    crashout_id: int | None = None


class ModerationQueueItem(BaseModel):
    id: int
    spike_text: str
    suggested_rewrite: str | None
    safe_move: str | None
    tone: str | None
    submitted_by: int
    submitter_username: str
    ai_generated: bool
    status: Literal["pending", "approved", "rejected"]
    created_at: str
