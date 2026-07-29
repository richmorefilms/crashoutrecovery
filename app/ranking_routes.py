"""Ranking + personalization API — /api/ranking/*."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.ranking_service import (
    build_personalized_feed_response,
    build_score_demo_response,
    get_preferences,
    record_history,
)

router = APIRouter(prefix="/api/ranking", tags=["ranking"])


class HistoryBody(BaseModel):
    user_id: int = Field(..., ge=1)
    item_id: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(default="unknown", max_length=64)


@router.get("/score")
async def ranking_score():
    return JSONResponse(build_score_demo_response())


@router.get("/feed/{user_id}")
async def ranking_personalized_feed(user_id: int):
    return JSONResponse(build_personalized_feed_response(user_id))


@router.post("/history")
async def ranking_history(body: HistoryBody):
    try:
        payload = record_history(body.user_id, body.item_id, body.platform)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(payload)


@router.get("/preferences/{user_id}")
async def ranking_preferences(user_id: int):
    return JSONResponse(get_preferences(user_id))
