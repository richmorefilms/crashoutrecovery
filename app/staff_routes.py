"""Phase E: staff oversight over compose receipts and retention."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field, model_validator

from app.ad_system import (
    PREMIUM_AD_TYPES,
    create_club_promotion,
    create_premium_ad,
    create_story,
    list_club_promotions,
    list_premium_ads,
    update_club_promotion,
    update_premium_ad,
)
from app.auth_deps import require_staff
from app.db import (
    get_compose_receipt,
    insert_staff_audit_log,
    query_compose_receipts,
    soft_delete_compose_receipt,
    update_compose_receipt_retention,
)
from app.media import MediaUploadError, upload_image, upload_video
from app.rate_limits import (
    LIMIT_STAFF_MODIFY,
    LIMIT_STAFF_VIEW,
    RateLimitExceeded,
    check_rate_limit,
    http_429,
    increment_rate_limit,
    rate_limit_headers,
    staff_modify_policy,
    staff_view_policy,
    subject_for_staff,
)
from app.retention import KNOWN_RETENTION_POLICIES
from app.staff_service import (
    flag_item,
    get_flagged_items,
    get_platform_overview,
    unflag_item,
)

router = APIRouter(prefix="/api/staff", tags=["staff-oversight"])

ACTION_VIEW_RECEIPT = "VIEW_RECEIPT"
ACTION_RETENTION_UPDATE = "RETENTION_UPDATE"
ACTION_SOFT_DELETE = "SOFT_DELETE"


class ComposeReceiptOut(BaseModel):
    id: int
    request_id: str
    user_id: int | None = None
    staff_id: int | None = None
    input_prompt: str
    output_text: str
    tone: str | None = None
    model_name: str | None = None
    parameters_json: str | None = None
    created_at: str
    moderation_flags: str | None = None
    output_hash: str
    engine_version: str
    expires_at: str | None = None
    deleted_at: str | None = None
    retention_policy: str | None = None


class RetentionOverrideRequest(BaseModel):
    new_policy_code: str | None = Field(default=None, max_length=64)
    new_expiry_timestamp: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def require_change(self) -> RetentionOverrideRequest:
        if self.new_policy_code is None and self.new_expiry_timestamp is None:
            raise ValueError("Provide new_policy_code and/or new_expiry_timestamp")
        if (
            self.new_policy_code is not None
            and self.new_policy_code not in KNOWN_RETENTION_POLICIES
        ):
            raise ValueError(
                f"Unknown retention policy; expected one of {sorted(KNOWN_RETENTION_POLICIES)}"
            )
        return self


class MessageStatus(BaseModel):
    status: str
    request_id: str | None = None
    id: int | None = None


def _receipt_out(row: dict[str, Any]) -> ComposeReceiptOut:
    return ComposeReceiptOut(**row)


def _raise_rate_limit(exc: RateLimitExceeded) -> None:
    payload = http_429(exc)
    raise HTTPException(
        status_code=payload["status_code"],
        detail=payload["detail"],
        headers=payload["headers"],
    ) from exc


def _staff_check_view(staff_user: dict[str, Any]) -> None:
    subject = subject_for_staff(int(staff_user["id"]))
    try:
        check_rate_limit(
            subject,
            LIMIT_STAFF_VIEW,
            policy=staff_view_policy(),
            staff_id_for_audit=int(staff_user["id"]),
        )
    except RateLimitExceeded as exc:
        _raise_rate_limit(exc)


def _staff_inc_view(staff_user: dict[str, Any], response: Response) -> None:
    snapshot = increment_rate_limit(
        subject_for_staff(int(staff_user["id"])),
        LIMIT_STAFF_VIEW,
        policy=staff_view_policy(),
    )
    for key, value in rate_limit_headers(snapshot).items():
        response.headers[key] = value


def _staff_check_modify(staff_user: dict[str, Any]) -> None:
    subject = subject_for_staff(int(staff_user["id"]))
    try:
        check_rate_limit(
            subject,
            LIMIT_STAFF_MODIFY,
            policy=staff_modify_policy(),
            staff_id_for_audit=int(staff_user["id"]),
        )
    except RateLimitExceeded as exc:
        _raise_rate_limit(exc)


def _staff_inc_modify(staff_user: dict[str, Any], response: Response) -> None:
    snapshot = increment_rate_limit(
        subject_for_staff(int(staff_user["id"])),
        LIMIT_STAFF_MODIFY,
        policy=staff_modify_policy(),
    )
    for key, value in rate_limit_headers(snapshot).items():
        response.headers[key] = value


@router.get("/receipts", response_model=list[ComposeReceiptOut])
async def list_receipts(
    response: Response,
    user_id: int | None = Query(default=None),
    staff_id: int | None = Query(default=None),
    request_id: str | None = Query(default=None, max_length=128),
    moderation_flags: str | None = Query(default=None, max_length=500),
    retention_policy: str | None = Query(default=None, max_length=64),
    created_from: str | None = Query(default=None, max_length=64),
    created_to: str | None = Query(default=None, max_length=64),
    expires_from: str | None = Query(default=None, max_length=64),
    expires_to: str | None = Query(default=None, max_length=64),
    deleted_from: str | None = Query(default=None, max_length=64),
    deleted_to: str | None = Query(default=None, max_length=64),
    include_deleted: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    staff_user: dict[str, Any] = Depends(require_staff),
) -> list[ComposeReceiptOut]:
    """Staff browser: list compose receipts (active by default)."""
    _staff_check_view(staff_user)
    rows = query_compose_receipts(
        user_id=user_id,
        staff_id=staff_id,
        request_id=request_id,
        retention_policy=retention_policy,
        moderation_flags=moderation_flags,
        created_from=created_from,
        created_to=created_to,
        expires_from=expires_from,
        expires_to=expires_to,
        deleted_from=deleted_from,
        deleted_to=deleted_to,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    _staff_inc_view(staff_user, response)
    return [_receipt_out(row) for row in rows]


@router.get("/receipts/{request_id}", response_model=ComposeReceiptOut)
async def get_receipt(
    request_id: str,
    response: Response,
    include_deleted: bool = Query(default=False),
    staff_user: dict[str, Any] = Depends(require_staff),
) -> ComposeReceiptOut:
    """Staff detail view for one receipt by request_id."""
    _staff_check_view(staff_user)
    row = get_compose_receipt(
        request_id=request_id,
        include_deleted=include_deleted,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    insert_staff_audit_log(
        staff_id=int(staff_user["id"]),
        action_type=ACTION_VIEW_RECEIPT,
        target_request_id=row["request_id"],
        target_receipt_id=int(row["id"]),
        metadata={"include_deleted": include_deleted},
    )
    _staff_inc_view(staff_user, response)
    return _receipt_out(row)


@router.patch("/receipts/{request_id}/retention", response_model=ComposeReceiptOut)
async def override_retention(
    request_id: str,
    body: RetentionOverrideRequest,
    response: Response,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> ComposeReceiptOut:
    """Staff retention override: policy and/or expires_at (no physical delete)."""
    _staff_check_modify(staff_user)
    updated = update_compose_receipt_retention(
        request_id=request_id,
        retention_policy=body.new_policy_code,
        expires_at=body.new_expiry_timestamp,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found or already deleted",
        )
    insert_staff_audit_log(
        staff_id=int(staff_user["id"]),
        action_type=ACTION_RETENTION_UPDATE,
        target_request_id=updated["request_id"],
        target_receipt_id=int(updated["id"]),
        metadata={
            "new_policy_code": body.new_policy_code,
            "new_expiry_timestamp": body.new_expiry_timestamp,
        },
    )
    _staff_inc_modify(staff_user, response)
    return _receipt_out(updated)


@router.post(
    "/receipts/{request_id}/soft-delete",
    response_model=MessageStatus,
    status_code=status.HTTP_200_OK,
)
async def soft_delete_receipt(
    request_id: str,
    response: Response,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> MessageStatus:
    """Staff soft-delete: set deleted_at, keep the row."""
    _staff_check_modify(staff_user)
    existing = get_compose_receipt(request_id=request_id, include_deleted=False)
    if not existing:
        # Distinguish already-deleted vs missing for clearer ops feedback.
        maybe = get_compose_receipt(request_id=request_id, include_deleted=True)
        if maybe:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Receipt already soft-deleted",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    ok = soft_delete_compose_receipt(request_id=request_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receipt already soft-deleted",
        )
    insert_staff_audit_log(
        staff_id=int(staff_user["id"]),
        action_type=ACTION_SOFT_DELETE,
        target_request_id=existing["request_id"],
        target_receipt_id=int(existing["id"]),
    )
    _staff_inc_modify(staff_user, response)
    return MessageStatus(status="soft_deleted", request_id=request_id, id=int(existing["id"]))


# --- Phase G: media upload + premium ads + club promotions + stories ---


class PremiumAdCreate(BaseModel):
    ad_type: str = Field(..., max_length=32)
    media_url: str = Field(..., min_length=1, max_length=2000)
    target_url: str = Field(..., min_length=1, max_length=2000)
    active: bool = True


class PremiumAdUpdate(BaseModel):
    ad_type: str | None = Field(default=None, max_length=32)
    media_url: str | None = Field(default=None, max_length=2000)
    target_url: str | None = Field(default=None, max_length=2000)
    active: bool | None = None


class ClubPromoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    media_url: str | None = Field(default=None, max_length=2000)
    video_url: str | None = Field(default=None, max_length=2000)
    active: bool = True


class ClubPromoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    media_url: str | None = Field(default=None, max_length=2000)
    video_url: str | None = Field(default=None, max_length=2000)
    active: bool | None = None


class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)
    crashout_id: int | None = None
    image_url: str | None = Field(default=None, max_length=2000)
    video_url: str | None = Field(default=None, max_length=2000)
    thumbnail_url: str | None = Field(default=None, max_length=2000)
    published: bool = False


@router.post("/media/image")
async def staff_upload_image(
    file: UploadFile = File(...),
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, str]:
    _ = staff_user
    try:
        url = await upload_image(file)
    except MediaUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"url": url}


@router.post("/media/video")
async def staff_upload_video(
    file: UploadFile = File(...),
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, str]:
    _ = staff_user
    try:
        url = await upload_video(file)
    except MediaUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"url": url}


@router.get("/ads")
async def staff_list_ads(
    staff_user: dict[str, Any] = Depends(require_staff),
) -> list[dict[str, Any]]:
    _ = staff_user
    return list_premium_ads(active_only=False)


@router.post("/ads", status_code=status.HTTP_201_CREATED)
async def staff_create_ad(
    body: PremiumAdCreate,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, Any]:
    _ = staff_user
    if body.ad_type not in PREMIUM_AD_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"ad_type must be one of {sorted(PREMIUM_AD_TYPES)}",
        )
    return create_premium_ad(
        ad_type=body.ad_type,
        media_url=body.media_url,
        target_url=body.target_url,
        active=body.active,
    )


@router.patch("/ads/{ad_id}")
async def staff_update_ad(
    ad_id: int,
    body: PremiumAdUpdate,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, Any]:
    _ = staff_user
    try:
        updated = update_premium_ad(
            ad_id,
            ad_type=body.ad_type,
            media_url=body.media_url,
            target_url=body.target_url,
            active=body.active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Ad not found")
    return updated


@router.get("/clubs")
async def staff_list_clubs(
    staff_user: dict[str, Any] = Depends(require_staff),
) -> list[dict[str, Any]]:
    _ = staff_user
    return list_club_promotions(active_only=False)


@router.post("/clubs", status_code=status.HTTP_201_CREATED)
async def staff_create_club(
    body: ClubPromoCreate,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, Any]:
    _ = staff_user
    return create_club_promotion(
        title=body.title,
        description=body.description,
        media_url=body.media_url,
        video_url=body.video_url,
        active=body.active,
    )


@router.patch("/clubs/{promo_id}")
async def staff_update_club(
    promo_id: int,
    body: ClubPromoUpdate,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, Any]:
    _ = staff_user
    try:
        updated = update_club_promotion(
            promo_id,
            title=body.title,
            description=body.description,
            media_url=body.media_url,
            video_url=body.video_url,
            active=body.active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Club promotion not found")
    return updated


@router.post("/stories", status_code=status.HTTP_201_CREATED)
async def staff_create_story(
    body: StoryCreate,
    staff_user: dict[str, Any] = Depends(require_staff),
) -> dict[str, Any]:
    _ = staff_user
    return create_story(
        title=body.title,
        body=body.body,
        crashout_id=body.crashout_id,
        image_url=body.image_url,
        video_url=body.video_url,
        thumbnail_url=body.thumbnail_url,
        published=body.published,
    )


@router.get("/overview")
async def staff_overview(
    staff_user: dict[str, Any] = Depends(require_staff),
):
    _ = staff_user
    return get_platform_overview()


@router.get("/flags")
async def staff_flags(
    staff_user: dict[str, Any] = Depends(require_staff),
):
    _ = staff_user
    return get_flagged_items()


@router.post("/flag/{item_id}")
async def staff_flag_item(
    item_id: str,
    staff_user: dict[str, Any] = Depends(require_staff),
    reason: str | None = Query(default=None),
):
    return flag_item(
        item_id,
        reason=reason,
        flagged_by=int(staff_user["id"]) if staff_user.get("id") is not None else None,
    )


@router.post("/unflag/{item_id}")
async def staff_unflag_item(
    item_id: str,
    staff_user: dict[str, Any] = Depends(require_staff),
):
    _ = staff_user
    return unflag_item(item_id)
