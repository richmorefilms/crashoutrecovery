"""Multi-platform feed API — /api/multi/*."""
from __future__ import annotations

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.multiplaform_service import (
    fetch_facebook_feed,
    fetch_instagram_feed,
    fetch_pinterest_feed,
    fetch_twitter_feed,
)
from app.rate_limits import enforce_endpoint_rate_limit

router = APIRouter(prefix="/api/multi", tags=["multiplatform"])


def _uid(x_user_id: str | None) -> int:
    if x_user_id and str(x_user_id).isdigit():
        return int(x_user_id)
    return 0


@router.get("/instagram")
async def multi_instagram(x_user_id: str | None = Header(default=None)):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/multi/instagram")
    if blocked is not None:
        return blocked
    return JSONResponse(fetch_instagram_feed())


@router.get("/facebook")
async def multi_facebook(x_user_id: str | None = Header(default=None)):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/multi/facebook")
    if blocked is not None:
        return blocked
    return JSONResponse(fetch_facebook_feed())


@router.get("/twitter")
async def multi_twitter(x_user_id: str | None = Header(default=None)):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/multi/twitter")
    if blocked is not None:
        return blocked
    return JSONResponse(fetch_twitter_feed())


@router.get("/pinterest")
async def multi_pinterest(x_user_id: str | None = Header(default=None)):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/multi/pinterest")
    if blocked is not None:
        return blocked
    return JSONResponse(fetch_pinterest_feed())
