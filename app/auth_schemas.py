"""Pydantic models for auth + user data sync."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Client sync may not write tier — server owns entitlement preview updates.
ALLOWED_DATA_KEYS = frozenset(
    {
        "crashout_recovery",
        "crashout_seeds",
        "crashout_market_packs",
        "crashout_world_signals",
    }
)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_chars(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.replace("_", "").isalnum():
            raise ValueError("Username may only use letters, numbers, and underscores")
        return cleaned

    @field_validator("email")
    @classmethod
    def email_format(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_RE.match(cleaned):
            raise ValueError("Invalid email address")
        return cleaned


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    tier: str
    role: str
    created_at: str | None = None
    last_login: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: UserPublic


class MessageResponse(BaseModel):
    message: str


class StaffPromoteRequest(BaseModel):
    username_or_email: str = Field(min_length=1, max_length=254)


class UserDataBundle(BaseModel):
    crashout_recovery: Any | None = None
    crashout_seeds: Any | None = None
    crashout_market_packs: Any | None = None
    crashout_world_signals: Any | None = None
    tier: str | None = None


class UserDataPut(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def only_allowed_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        unknown = set(value) - ALLOWED_DATA_KEYS
        if unknown:
            raise ValueError(f"Unsupported keys: {sorted(unknown)}")
        return value
