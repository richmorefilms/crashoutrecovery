"""Register / login / logout / refresh / me endpoints."""
from __future__ import annotations

from typing import Any

from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth_deps import get_current_user, load_user, require_staff
from app.auth_schemas import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    StaffPromoteRequest,
    TokenResponse,
    UserPublic,
)
from app.auth_security import (
    decode_access_token,
    hash_password,
    issue_session,
    purge_expired_revocations,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    revoke_token,
    rotate_refresh_token,
    validate_refresh_token,
    verify_password,
)
from app.db import get_conn, promote_user_to_staff, row_to_dict, utc_now_iso

router = APIRouter(tags=["auth"])


def _public_user(row: dict[str, Any]) -> UserPublic:
    return UserPublic(
        id=int(row["id"]),
        username=row["username"],
        email=row["email"],
        tier=row.get("tier") or "basic",
        role=row.get("role") or "user",
        created_at=row.get("created_at"),
        last_login=row.get("last_login"),
    )


def _token_response(user: dict[str, Any], session: dict[str, Any]) -> TokenResponse:
    return TokenResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session["expires_in"],
        refresh_expires_in=session["refresh_expires_in"],
        user=_public_user(user),
    )


async def _register(body: RegisterRequest) -> TokenResponse:
    password_hash = hash_password(body.password)
    created = utc_now_iso()
    # Staff is never granted on register — use CLI or staff-gated promote.
    try:
        with get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, tier, role, created_at, last_login
                )
                VALUES (?, ?, ?, 'basic', 'user', ?, ?)
                """,
                (body.username, body.email, password_hash, created, created),
            )
            user_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO recovery (user_id, streak_days, spike_history, tones, wins)
                VALUES (?, 0, '[]', '[]', 0)
                """,
                (user_id,),
            )
            row = conn.execute(
                """
                SELECT id, username, email, tier, role, created_at, last_login
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        ) from exc

    user = row_to_dict(row) or {}
    session = issue_session(user_id=user_id, username=user["username"])
    return _token_response(user, session)


async def _login(body: LoginRequest) -> TokenResponse:
    identity = body.username_or_email.strip()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, username, email, password_hash, tier, role, created_at, last_login
            FROM users
            WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE
            """,
            (identity, identity.lower()),
        ).fetchone()

    user = row_to_dict(row)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, int(user["id"])))
    user["last_login"] = now

    session = issue_session(user_id=int(user["id"]), username=user["username"])
    return _token_response(user, session)


async def _logout(
    request: Request,
    body: LogoutRequest | None,
    user: dict[str, Any],
) -> MessageResponse:
    payload = getattr(request.state, "token_payload", None)
    if not payload:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            payload = decode_access_token(auth[7:].strip())

    if payload and payload.get("jti"):
        revoke_token(str(payload["jti"]), float(payload.get("exp") or 0))

    refresh = (body.refresh_token if body else None) or None
    if refresh:
        revoke_refresh_token(refresh)
    else:
        revoke_all_refresh_tokens(int(user["id"]))

    purge_expired_revocations()
    return MessageResponse(message="Logged out")


async def _refresh(body: RefreshRequest) -> TokenResponse:
    import time

    from app.auth_security import create_access_token

    payload = validate_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    user = load_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access, _, access_exp = create_access_token(user_id=user_id, username=user["username"])
    new_refresh, _, refresh_exp = rotate_refresh_token(body.refresh_token, user_id=user_id)
    session = {
        "access_token": access,
        "refresh_token": new_refresh,
        "expires_in": max(1, int(access_exp - time.time())),
        "refresh_expires_in": max(1, int(refresh_exp - time.time())),
    }
    return _token_response(user, session)


async def _me(user: dict[str, Any]) -> UserPublic:
    return _public_user(user)


# Canonical /auth/* routes
@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> TokenResponse:
    return await _register(body)


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    return await _login(body)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    return await _refresh(body)


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    body: LogoutRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    return await _logout(request, body, user)


@router.get("/auth/me", response_model=UserPublic)
async def me(user: dict[str, Any] = Depends(get_current_user)) -> UserPublic:
    return await _me(user)


@router.post("/auth/staff/promote", response_model=UserPublic)
async def promote_staff(
    body: StaffPromoteRequest,
    _staff: dict[str, Any] = Depends(require_staff),
) -> UserPublic:
    """Promote an existing user to staff (staff only). First staff: scripts/promote_staff.py."""
    user = promote_user_to_staff(body.username_or_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return _public_user(user)


# Short aliases requested by API design
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def register_alias(body: RegisterRequest) -> TokenResponse:
    return await _register(body)


@router.post("/login", response_model=TokenResponse, include_in_schema=False)
async def login_alias(body: LoginRequest) -> TokenResponse:
    return await _login(body)


@router.post("/logout", response_model=MessageResponse, include_in_schema=False)
async def logout_alias(
    request: Request,
    body: LogoutRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    return await _logout(request, body, user)


@router.get("/me", response_model=UserPublic, include_in_schema=False)
async def me_alias(user: dict[str, Any] = Depends(get_current_user)) -> UserPublic:
    return await _me(user)
