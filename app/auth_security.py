"""Password hashing (bcrypt), access/refresh JWT helpers, revocation."""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from typing import Any

import bcrypt
import jwt

from app.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_SECONDS,
    JWT_REFRESH_EXPIRE_SECONDS,
    JWT_SECRET,
)
from app.db import get_conn, utc_now_iso


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(*, user_id: int, username: str) -> tuple[str, str, float]:
    """Short-lived access JWT. Returns (token, jti, expires_at_epoch)."""
    now = time.time()
    expires = now + JWT_EXPIRE_SECONDS
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "jti": jti,
        "iat": int(now),
        "exp": int(expires),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti, expires


def create_refresh_token(*, user_id: int) -> tuple[str, str, float]:
    """Longer-lived refresh token stored hashed in SQLite."""
    now = time.time()
    expires = now + JWT_REFRESH_EXPIRE_SECONDS
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": int(now),
        "exp": int(expires),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, jti, expires_at, revoked, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (user_id, _hash_refresh(token), jti, expires, utc_now_iso()),
        )
    return token, jti, expires


def decode_token(token: str, *, expect_type: str | None = None) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if expect_type and payload.get("type") != expect_type:
        return None
    return payload


def decode_access_token(token: str) -> dict[str, Any] | None:
    return decode_token(token, expect_type="access")


def revoke_token(jti: str, expires_at: float) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
            (jti, expires_at),
        )


def is_token_revoked(jti: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT jti FROM revoked_tokens WHERE jti = ?",
            (jti,),
        ).fetchone()
        return row is not None


def revoke_refresh_token(token: str) -> None:
    token_hash = _hash_refresh(token)
    with get_conn() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?",
            (token_hash,),
        )


def revoke_all_refresh_tokens(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?",
            (user_id,),
        )


def validate_refresh_token(token: str) -> dict[str, Any] | None:
    payload = decode_token(token, expect_type="refresh")
    if not payload:
        return None
    jti = payload.get("jti")
    if not jti or is_token_revoked(str(jti)):
        return None
    token_hash = _hash_refresh(token)
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, revoked, expires_at
            FROM refresh_tokens
            WHERE token_hash = ? AND jti = ?
            """,
            (token_hash, str(jti)),
        ).fetchone()
    if not row or row["revoked"] or float(row["expires_at"]) < time.time():
        return None
    return payload


def rotate_refresh_token(old_token: str, *, user_id: int) -> tuple[str, str, float]:
    revoke_refresh_token(old_token)
    payload = decode_token(old_token, expect_type="refresh")
    if payload and payload.get("jti"):
        revoke_token(str(payload["jti"]), float(payload.get("exp") or 0))
    return create_refresh_token(user_id=user_id)


def purge_expired_revocations() -> None:
    now = time.time()
    with get_conn() as conn:
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (now,))
        conn.execute(
            "DELETE FROM refresh_tokens WHERE expires_at < ? OR revoked = 1",
            (now,),
        )


def issue_session(*, user_id: int, username: str) -> dict[str, Any]:
    access, access_jti, access_exp = create_access_token(user_id=user_id, username=username)
    refresh, _, refresh_exp = create_refresh_token(user_id=user_id)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": int(access_exp - time.time()),
        "refresh_expires_in": int(refresh_exp - time.time()),
        "access_jti": access_jti,
    }


def fingerprint_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def new_secret() -> str:
    return secrets.token_urlsafe(48)
