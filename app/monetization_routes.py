"""Monetization API — /api/monetization/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.monetization_service import (
    get_ads,
    get_creator_earnings,
    get_monetization_lanes,
    record_ad_click,
)

router = APIRouter(prefix="/api/monetization", tags=["monetization"])


@router.get("/lanes")
async def monetization_lanes():
    return JSONResponse(get_monetization_lanes())


@router.get("/ads")
async def monetization_ads():
    return JSONResponse(get_ads())


@router.post("/ads/click/{ad_id}")
async def monetization_ad_click(
    ad_id: int,
    creator_id: str | None = Query(default=None),
):
    try:
        payload = record_ad_click(ad_id, creator_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(payload)


@router.get("/creator/{creator_id}/earnings")
async def monetization_creator_earnings(creator_id: str):
    return JSONResponse(get_creator_earnings(creator_id))
