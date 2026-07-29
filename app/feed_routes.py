"""Unified feed API — /api/feed/*."""
from __future__ import annotations

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.feed_service import (
    build_creator_feed_response,
    build_trending_response,
    build_unified_all_response,
)
from app.rate_limits import enforce_endpoint_rate_limit

# Prefix is applied in create_app(): include_router(feed_router, prefix="/api/feed")
router = APIRouter(tags=["feed"])


def _uid(x_user_id: str | None, fallback: int = 0) -> int:
    if x_user_id and str(x_user_id).isdigit():
        return int(x_user_id)
    return fallback


@router.get("/all")
async def feed_all(
    max_results: int = Query(default=12, ge=1, le=50),
    with_ads: bool = Query(default=False),
    ranked: bool = Query(default=False),
    personalized: str | None = Query(
        default=None,
        description="User id for personalized ranking",
    ),
    recommended: str | None = Query(
        default=None,
        description="User id for collaborative + topic recommendations",
    ),
    x_user_id: str | None = Header(default=None),
):
    uid = _uid(x_user_id)
    if personalized and str(personalized).isdigit():
        uid = int(personalized)
    elif recommended and str(recommended).isdigit():
        uid = int(recommended)
    blocked = enforce_endpoint_rate_limit(uid, "/api/feed/all")
    if blocked is not None:
        return blocked
    return JSONResponse(
        build_unified_all_response(
            max_results=max_results,
            with_ads=with_ads,
            ranked=ranked,
            personalized_user_id=personalized,
            recommended_user_id=recommended,
        )
    )


@router.get("/trending")
async def feed_trending(
    max_results: int = Query(default=12, ge=1, le=50),
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/feed/trending")
    if blocked is not None:
        return blocked
    return JSONResponse(build_trending_response(max_results=max_results))


@router.get("/creator/{creator_id}")
async def feed_creator(creator_id: str, x_user_id: str | None = Header(default=None)):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/feed/creator")
    if blocked is not None:
        return blocked
    return JSONResponse(build_creator_feed_response(creator_id))
