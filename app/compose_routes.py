"""Composer and staff moderation API routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.auth_deps import get_current_user, get_optional_user, require_staff
from app.compose_engine import (
    InvalidComposeReceipt,
    build_compose_response,
)
from app.compose_schemas import (
    ApproveSeedRequest,
    ComposeRequest,
    ComposeResponse,
    ModerationQueueItem,
    ModerationResult,
    RejectSeedRequest,
    SaveSeedRequest,
    SaveSeedResponse,
)
from app.moderation_service import (
    ModerationConflictError,
    ModerationNotFoundError,
    ModerationValidationError,
    list_pending_moderation,
    promote_moderation_item,
    queue_seed,
    reject_moderation_item,
)
from app.rate_limits import (
    LIMIT_COMPOSE,
    RateLimitExceeded,
    check_rate_limit,
    compose_policy_for_user,
    compose_subject,
    http_429,
    increment_rate_limit,
    rate_limit_headers,
)

router = APIRouter(prefix="/api", tags=["composer"])


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _raise_rate_limit(exc: RateLimitExceeded) -> None:
    payload = http_429(exc)
    raise HTTPException(
        status_code=payload["status_code"],
        detail=payload["detail"],
        headers=payload["headers"],
    ) from exc


@router.post("/compose", response_model=ComposeResponse)
async def compose(
    body: ComposeRequest,
    request: Request,
    response: Response,
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> ComposeResponse:
    subject = compose_subject(user, _client_ip(request))
    policy = compose_policy_for_user(user)
    try:
        check_rate_limit(subject, LIMIT_COMPOSE, policy=policy)
    except RateLimitExceeded as exc:
        _raise_rate_limit(exc)

    result = build_compose_response(
        body.spike_text,
        user_id=int(user["id"]) if user and user.get("id") is not None else None,
    )
    snapshot = increment_rate_limit(subject, LIMIT_COMPOSE, policy=policy)
    for key, value in rate_limit_headers(snapshot).items():
        response.headers[key] = value
    return result


@router.post(
    "/save_seed",
    response_model=SaveSeedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_seed(
    body: SaveSeedRequest,
    user: dict = Depends(get_current_user),
) -> SaveSeedResponse:
    try:
        queue_id = queue_seed(body, submitted_by=int(user["id"]))
    except InvalidComposeReceipt as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SaveSeedResponse(id=queue_id)


@router.get(
    "/moderation/queue",
    response_model=list[ModerationQueueItem],
)
async def moderation_queue(
    limit: int = Query(default=50, ge=1, le=200),
    _staff: dict = Depends(require_staff),
) -> list[ModerationQueueItem]:
    return [ModerationQueueItem(**item) for item in list_pending_moderation(limit=limit)]


def _translate_moderation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ModerationNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ModerationConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ModerationValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Moderation action failed")


@router.post(
    "/moderation/approve/{queue_id}",
    response_model=ModerationResult,
)
async def approve_seed(
    queue_id: int,
    body: ApproveSeedRequest,
    staff_user: dict = Depends(require_staff),
) -> ModerationResult:
    try:
        crashout_id = promote_moderation_item(
            queue_id,
            body,
            curated_by=int(staff_user["id"]),
        )
    except (ModerationNotFoundError, ModerationConflictError, ModerationValidationError) as exc:
        raise _translate_moderation_error(exc) from exc
    return ModerationResult(status="approved", id=queue_id, crashout_id=crashout_id)


@router.post(
    "/moderation/reject/{queue_id}",
    response_model=ModerationResult,
)
async def reject_seed(
    queue_id: int,
    body: RejectSeedRequest,
    staff_user: dict = Depends(require_staff),
) -> ModerationResult:
    try:
        reject_moderation_item(
            queue_id,
            reviewed_by=int(staff_user["id"]),
            reason=body.reason,
        )
    except (ModerationNotFoundError, ModerationConflictError) as exc:
        raise _translate_moderation_error(exc) from exc
    return ModerationResult(status="rejected", id=queue_id)
