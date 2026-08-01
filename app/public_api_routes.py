"""Public developer API — read-only Crashout ecosystem endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.growth_service import compute_creator_growth
from app.rate_limits import enforce_endpoint_rate_limit
from app.recommendation_service import build_topics_response

router = APIRouter(prefix="/api/public", tags=["public-api"])


def _uid(x_user_id: str | None) -> int:
    if x_user_id and str(x_user_id).isdigit():
        return int(x_user_id)
    return 0


@router.get("/feed/signals")
async def public_feed_signals(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/public/feed/signals")
    if blocked is not None:
        return blocked
    items = [
        {
            "id": "sig_activity",
            "kind": "creator_activity",
            "title": "Creator activity",
            "strength": 72,
        },
        {
            "id": "sig_social",
            "kind": "social_boost",
            "title": "Social boosts",
            "strength": 64,
        },
        {
            "id": "sig_challenge",
            "kind": "challenge",
            "title": "Challenge completions",
            "strength": 58,
        },
        {
            "id": "sig_vault",
            "kind": "vault",
            "title": "Vault uploads",
            "strength": 51,
        },
        {
            "id": "sig_identity",
            "kind": "identity",
            "title": "Identity updates",
            "strength": 47,
        },
    ]
    return JSONResponse(
        {
            "ok": True,
            "platform": "crashout",
            "lane": "public_signals",
            "title": "Creator Feed Signals",
            "items": items,
            "count": len(items),
            "meta": {"rate_limit": "per-user soft cap"},
        }
    )


@router.get("/topics")
async def public_topics(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/public/topics")
    if blocked is not None:
        return blocked
    payload = build_topics_response(max_results=24)
    return JSONResponse(payload)


@router.get("/momentum")
async def public_momentum(
    creator_id: str = Query(default="1"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id or creator_id), "/api/public/momentum")
    if blocked is not None:
        return blocked
    return JSONResponse(compute_creator_growth(creator_id))


@router.get("/vault/meta")
async def public_vault_meta(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    blocked = enforce_endpoint_rate_limit(_uid(x_user_id), "/api/public/vault/meta")
    if blocked is not None:
        return blocked
    meta: dict[str, Any] = {
        "ok": True,
        "platform": "crashout",
        "lane": "vault_meta",
        "title": "Vault metadata",
        "items": [
            {"id": "clip", "label": "Clip"},
            {"id": "draft", "label": "Draft"},
            {"id": "thumbnail", "label": "Thumbnail"},
            {"id": "script", "label": "Script"},
        ],
        "count": 4,
        "meta": {
            "storage": "client_local_pwa",
            "note": "Content stays on-device; this endpoint exposes schema only.",
        },
    }
    return JSONResponse(meta)
