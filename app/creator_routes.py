"""Creator dashboard API — /api/creator/*."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.creator_service import get_creator_analytics, get_creator_channels
from app.monetization_service import (
    get_creator_earnings,
    get_creator_monetization,
    process_creator_payout,
)

router = APIRouter(prefix="/api/creator", tags=["creator"])


@router.get("/{creator_id}/channels")
async def creator_channels(creator_id: str):
    return JSONResponse(get_creator_channels(creator_id))


@router.get("/{creator_id}/analytics")
async def creator_analytics(creator_id: str):
    return JSONResponse(get_creator_analytics(creator_id))


@router.get("/{creator_id}/earnings")
async def creator_earnings(creator_id: str):
    return JSONResponse(get_creator_earnings(creator_id))


@router.get("/{creator_id}/monetization")
async def creator_monetization(creator_id: str):
    return JSONResponse(get_creator_monetization(creator_id))


@router.post("/{creator_id}/payout")
async def creator_payout(creator_id: str):
    try:
        payload = process_creator_payout(creator_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(payload)
