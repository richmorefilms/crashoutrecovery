"""Auth dependencies and JWT middleware."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.auth_security import decode_access_token, is_token_revoked
from app.db import get_conn, row_to_dict

bearer_scheme = HTTPBearer(auto_error=False)

PUBLIC_PREFIXES = (
    "/static",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/UI_COPY.json",
    "/ops",
    "/ops.md",
    "/ops-full.md",
    "/manual",
    "/embed",
    "/crashout",
    "/api/tones",
    "/api/crashout",
    "/api/compose",
    "/api/suggest",
    "/api/youtube",
    "/api/tiktok/feed",
    "/api/tiktok/share",
    "/api/stories",
    "/ads",
    "/stories",
    "/media",
    "/videos.json",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/auth/tiktok",
    "/register",
    "/login",
    "/login/tiktok",
    "/profile",
    "/feed",
    "/feed/tiktok",
)

PUBLIC_EXACT = {"/", "/favicon.ico"}

# /team/* is not public: mutating handlers require staff via Depends(require_staff).
# Read-only team helpers (model/topics/check/block/preview) stay open at the route layer.
PROTECTED_PREFIXES = ("/api/user", "/auth/staff")
PROTECTED_EXACT = {"/auth/me", "/auth/logout", "/me", "/logout"}


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path == p or path.startswith(f"{p}/") for p in PUBLIC_PREFIXES)


def _needs_auth(path: str) -> bool:
    if path in PROTECTED_EXACT:
        return True
    return any(path == p or path.startswith(f"{p}/") for p in PROTECTED_PREFIXES)


def load_user(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, username, email, tier, role, created_at, last_login
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return row_to_dict(row)


def resolve_token(token: str) -> dict[str, Any]:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    jti = payload.get("jti")
    if not jti or is_token_revoked(str(jti)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc
    user = load_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return {"user": user, "payload": payload, "token": token}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return resolve_token(credentials.credentials)["user"]


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any] | None:
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    try:
        return resolve_token(credentials.credentials)["user"]
    except HTTPException:
        return None


async def require_staff(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Require server-controlled staff authority, independent of paid tier."""
    if user.get("role") != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "staff_required",
                "message": "Staff authorization required",
            },
        )
    return user


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Attach user from Bearer access JWT when present.
    Protected routes require a valid token; HTML GETs redirect to /?login=1.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        request.state.user = None
        request.state.token_payload = None

        auth_header = request.headers.get("Authorization") or ""
        token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""

        token_error = False
        if token:
            try:
                resolved = resolve_token(token)
                request.state.user = resolved["user"]
                request.state.token_payload = resolved["payload"]
            except HTTPException:
                token_error = True

        if _needs_auth(path) and (request.state.user is None or token_error):
            wants_html = "text/html" in (request.headers.get("accept") or "")
            if wants_html and request.method == "GET":
                return RedirectResponse(url="/?login=1", status_code=302)
            detail = "Invalid or expired token" if token_error else "Not authenticated"
            return JSONResponse({"detail": detail}, status_code=401)

        return await call_next(request)
