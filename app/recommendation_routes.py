"""Recommendations API — /api/recommendations/*."""
from __future__ import annotations

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.rate_limits import enforce_endpoint_rate_limit
from app.recommendation_service import (
    build_graph_response,
    build_similar_response,
    build_topics_response,
    recommend_all,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _uid(x_user_id: str | None, fallback: int = 0) -> int:
    if x_user_id and str(x_user_id).isdigit():
        return int(x_user_id)
    return fallback


@router.get("/topics")
async def recommendation_topics(
    max_results: int = Query(default=24, ge=1, le=50),
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/recommendations/topics")
    if blocked is not None:
        return blocked
    return JSONResponse(build_topics_response(max_results=max_results))


@router.get("/graph")
async def recommendation_graph(
    max_results: int = Query(default=24, ge=1, le=50),
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/recommendations/graph")
    if blocked is not None:
        return blocked
    return JSONResponse(build_graph_response(max_results=max_results))


@router.get("/similar/{user_id}")
async def recommendation_similar(
    user_id: int,
    limit: int = Query(default=12, ge=1, le=50),
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(
        _uid(x_user_id, user_id), "/api/recommendations/similar"
    )
    if blocked is not None:
        return blocked
    return JSONResponse(build_similar_response(user_id, limit=limit))


@router.get("/all/{user_id}")
async def recommendation_all(
    user_id: int,
    max_results: int = Query(default=12, ge=1, le=50),
    x_user_id: str | None = Header(default=None),
):
    blocked = enforce_endpoint_rate_limit(
        _uid(x_user_id, user_id), "/api/recommendations/all"
    )
    if blocked is not None:
        return blocked
    return JSONResponse(recommend_all(user_id, max_results=max_results))
