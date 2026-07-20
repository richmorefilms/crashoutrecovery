"""Public ad config + impression logging."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.ad_system import AD_SOURCES, admob_mobile_config, log_ad_impression
from app.auth_deps import get_optional_user

router = APIRouter(prefix="/ads", tags=["ads"])


class ImpressionRequest(BaseModel):
    ad_id: int = Field(..., ge=1)
    ad_source: str = Field(..., max_length=32)
    surface: str = Field(default="web", max_length=64)


@router.get("/mobile-config")
async def mobile_config() -> dict[str, Any]:
    """AdMob configuration payload for mobile clients."""
    return admob_mobile_config()


@router.post("/impression", status_code=201)
async def record_impression(
    body: ImpressionRequest,
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> dict[str, Any]:
    if body.ad_source not in AD_SOURCES:
        raise HTTPException(
            status_code=422,
            detail=f"ad_source must be one of {sorted(AD_SOURCES)}",
        )
    impression_id = log_ad_impression(
        ad_id=body.ad_id,
        ad_source=body.ad_source,
        user_id=int(user["id"]) if user and user.get("id") is not None else None,
        surface=body.surface,
    )
    return {"status": "logged", "id": impression_id}
