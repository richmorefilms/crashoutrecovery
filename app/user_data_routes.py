"""Per-user persistence API — structured tables, localStorage-compatible payloads."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth_deps import get_current_user
from app.auth_schemas import ALLOWED_DATA_KEYS, MessageResponse, UserDataBundle, UserDataPut
from app.user_persistence import load_bundle, save_bundle

router = APIRouter(prefix="/api/user", tags=["user-data"])


@router.get("/data", response_model=UserDataBundle)
async def get_user_data(user: dict[str, Any] = Depends(get_current_user)) -> UserDataBundle:
    return UserDataBundle(**load_bundle(int(user["id"])))


@router.put("/data", response_model=MessageResponse)
async def put_user_data(
    body: UserDataPut,
    user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    save_bundle(int(user["id"]), body.data)
    return MessageResponse(message="Saved")


@router.put("/data/{data_key}", response_model=MessageResponse)
async def put_user_data_key(
    data_key: str,
    payload: dict[str, Any],
    user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    if data_key not in ALLOWED_DATA_KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown data key")
    value = payload.get("value", payload)
    save_bundle(int(user["id"]), {data_key: value})
    return MessageResponse(message="Saved")
