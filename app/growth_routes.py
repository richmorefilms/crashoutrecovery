"""Creator growth API — /api/growth/*."""
from __future__ import annotations

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.growth_service import (
    compute_creator_growth,
    get_creator_growth_trends,
    get_creator_opportunities,
)
from app.rate_limits import enforce_endpoint_rate_limit

router = APIRouter(prefix="/api/growth", tags=["growth"])


def _uid(x_user_id: str | None, creator_id: int) -> int:
    if x_user_id and str(x_user_id).isdigit():
        return int(x_user_id)
    return int(creator_id)


@router.get("/{creator_id}/score")
async def growth_score(
    creator_id: int,
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id, creator_id), "/api/growth/score")
    if blocked is not None:
        return blocked
    return JSONResponse(compute_creator_growth(creator_id))


@router.get("/{creator_id}/trends")
async def growth_trends(
    creator_id: int,
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id, creator_id), "/api/growth/trends")
    if blocked is not None:
        return blocked
    return JSONResponse(get_creator_growth_trends(creator_id))


@router.get("/{creator_id}/opportunities")
async def growth_opportunities(
    creator_id: int,
    x_user_id: str | None = Header(default=None),
    _max: int = Query(default=12, ge=1, le=50),
):
    _ = _max
    blocked = enforce_endpoint_rate_limit(
        _uid(x_user_id, creator_id), "/api/growth/opportunities"
    )
    if blocked is not None:
        return blocked
    return JSONResponse(get_creator_opportunities(creator_id))
