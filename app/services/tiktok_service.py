"""TikTok Open API client with automatic token refresh."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import (
    TIKTOK_ACCESS_TOKEN,
    TIKTOK_CLIENT_KEY,
    TIKTOK_CLIENT_SECRET,
    TIKTOK_REFRESH_TOKEN,
)

logger = logging.getLogger("crashout.tiktok")

TIKTOK_API_BASE = "https://open.tiktokapis.com"
TIKTOK_AUTH_BASE = "https://www.tiktok.com"
TOKEN_URL = f"{TIKTOK_API_BASE}/v2/oauth/token/"
USER_INFO_URL = f"{TIKTOK_API_BASE}/v2/user/info/"
VIDEO_INIT_URL = f"{TIKTOK_API_BASE}/v2/post/publish/video/init/"
PUBLISH_STATUS_URL = f"{TIKTOK_API_BASE}/v2/post/publish/status/fetch/"
VIDEO_QUERY_URL = f"{TIKTOK_API_BASE}/v2/video/query/"
RESEARCH_VIDEO_QUERY_URL = f"{TIKTOK_API_BASE}/v2/research/video/query/"

# Soft skew so we refresh a bit before expiry
_TOKEN_SKEW_SECONDS = 60


class TikTokAPIError(Exception):
    """Raised when TikTok returns a non-success response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class TikTokService:
    """Async TikTok API base client (httpx) with token refresh."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: float | None = None,
        client_key: str | None = None,
        client_secret: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.client_key = (client_key if client_key is not None else TIKTOK_CLIENT_KEY) or ""
        self.client_secret = (
            client_secret if client_secret is not None else TIKTOK_CLIENT_SECRET
        ) or ""
        self.access_token = (
            access_token if access_token is not None else TIKTOK_ACCESS_TOKEN
        ) or ""
        self.refresh_token = (
            refresh_token if refresh_token is not None else TIKTOK_REFRESH_TOKEN
        ) or ""
        self.token_expires_at = token_expires_at
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.client_key and self.client_secret)

    @property
    def has_access_token(self) -> bool:
        return bool(self.access_token)

    async def __aenter__(self) -> "TikTokService":
        self._client = httpx.AsyncClient(
            base_url=TIKTOK_API_BASE,
            timeout=self._timeout,
            headers={"User-Agent": "CrashoutRecovery/1.0"},
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=TIKTOK_API_BASE,
                timeout=self._timeout,
                headers={"User-Agent": "CrashoutRecovery/1.0"},
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def token_needs_refresh(self) -> bool:
        if not self.refresh_token:
            return False
        if not self.access_token:
            return True
        if self.token_expires_at is None:
            return False
        return time.time() >= (self.token_expires_at - _TOKEN_SKEW_SECONDS)

    async def refresh_access_token(self) -> dict[str, Any]:
        """Exchange refresh_token for a new access_token (+ optional new refresh)."""
        if not self.is_configured:
            raise TikTokAPIError("TikTok client key/secret not configured")
        if not self.refresh_token:
            raise TikTokAPIError("No TikTok refresh_token available")

        client = self._ensure_client()
        data = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        logger.info("Refreshing TikTok access token")
        resp = await client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        payload = _safe_json(resp)
        if resp.status_code >= 400 or payload.get("error"):
            logger.error("TikTok token refresh failed: %s", payload)
            raise TikTokAPIError(
                str(payload.get("error_description") or payload.get("error") or "refresh failed"),
                status_code=resp.status_code,
                payload=payload,
            )

        self.access_token = str(payload.get("access_token") or "")
        if payload.get("refresh_token"):
            self.refresh_token = str(payload["refresh_token"])
        expires_in = payload.get("expires_in")
        if expires_in is not None:
            try:
                self.token_expires_at = time.time() + float(expires_in)
            except (TypeError, ValueError):
                pass
        return payload

    async def ensure_fresh_token(self) -> str:
        if self.token_needs_refresh():
            await self.refresh_access_token()
        if not self.access_token:
            raise TikTokAPIError("No TikTok access_token available")
        return self.access_token

    async def exchange_code(
        self,
        code: str,
        *,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for access_token + refresh_token."""
        if not self.is_configured:
            raise TikTokAPIError("TikTok client key/secret not configured")

        client = self._ensure_client()
        data = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        resp = await client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        payload = _safe_json(resp)
        if resp.status_code >= 400 or payload.get("error"):
            logger.error("TikTok code exchange failed: %s", payload)
            raise TikTokAPIError(
                str(payload.get("error_description") or payload.get("error") or "code exchange failed"),
                status_code=resp.status_code,
                payload=payload,
            )

        self.access_token = str(payload.get("access_token") or "")
        self.refresh_token = str(payload.get("refresh_token") or self.refresh_token)
        expires_in = payload.get("expires_in")
        if expires_in is not None:
            try:
                self.token_expires_at = time.time() + float(expires_in)
            except (TypeError, ValueError):
                self.token_expires_at = None
        return payload

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: bool = True,
        absolute_url: str | None = None,
    ) -> dict[str, Any]:
        client = self._ensure_client()
        hdrs = dict(headers or {})
        if auth:
            token = await self.ensure_fresh_token()
            hdrs.setdefault("Authorization", f"Bearer {token}")

        url = absolute_url or path
        resp = await client.request(
            method.upper(),
            url,
            params=params,
            json=json_body,
            data=data,
            headers=hdrs,
        )
        payload = _safe_json(resp)
        error = payload.get("error")
        if isinstance(error, dict):
            error_code = error.get("code")
            if error_code and str(error_code).lower() not in ("ok", "success", ""):
                logger.error("TikTok API error %s %s → %s", method, url, payload)
                raise TikTokAPIError(
                    str(error.get("message") or error_code or f"HTTP {resp.status_code}"),
                    status_code=resp.status_code,
                    payload=payload,
                )
        elif error and resp.status_code >= 400:
            logger.error("TikTok API error %s %s → %s", method, url, payload)
            raise TikTokAPIError(
                str(error),
                status_code=resp.status_code,
                payload=payload,
            )
        if resp.status_code >= 400:
            logger.error("TikTok API HTTP %s %s → %s", resp.status_code, url, payload)
            raise TikTokAPIError(
                f"HTTP {resp.status_code}",
                status_code=resp.status_code,
                payload=payload,
            )
        return payload

    async def get_user_info(
        self,
        fields: str = "open_id,union_id,avatar_url,display_name,username",
    ) -> dict[str, Any]:
        payload = await self.request(
            "GET",
            USER_INFO_URL,
            params={"fields": fields},
            absolute_url=USER_INFO_URL,
        )
        return (payload.get("data") or {}).get("user") or payload.get("data") or {}

    async def init_video_upload(
        self,
        *,
        post_info: dict[str, Any],
        source_info: dict[str, Any],
    ) -> dict[str, Any]:
        body = {"post_info": post_info, "source_info": source_info}
        return await self.request(
            "POST",
            VIDEO_INIT_URL,
            json_body=body,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            absolute_url=VIDEO_INIT_URL,
        )

    async def upload_video_bytes(self, upload_url: str, content: bytes, content_type: str) -> None:
        client = self._ensure_client()
        resp = await client.put(
            upload_url,
            content=content,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(len(content)),
            },
        )
        if resp.status_code >= 400:
            raise TikTokAPIError(
                f"Upload PUT failed ({resp.status_code})",
                status_code=resp.status_code,
                payload=_safe_json(resp),
            )

    async def fetch_publish_status(self, publish_id: str) -> dict[str, Any]:
        return await self.request(
            "POST",
            PUBLISH_STATUS_URL,
            json_body={"publish_id": publish_id},
            headers={"Content-Type": "application/json; charset=UTF-8"},
            absolute_url=PUBLISH_STATUS_URL,
        )

    async def query_videos(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {"filters": filters or {}}
        return await self.request(
            "POST",
            VIDEO_QUERY_URL,
            json_body=body,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            absolute_url=VIDEO_QUERY_URL,
        )

    async def research_hashtag_videos(
        self,
        hashtag: str,
        *,
        max_count: int = 10,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Research API hashtag query (requires approved research access)."""
        body = {
            "query": {
                "and": [
                    {
                        "operation": "EQ",
                        "field_name": "hashtag_name",
                        "field_values": [hashtag.lstrip("#")],
                    }
                ]
            },
            "max_count": max_count,
            "cursor": cursor,
        }
        return await self.request(
            "POST",
            RESEARCH_VIDEO_QUERY_URL,
            json_body=body,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            absolute_url=RESEARCH_VIDEO_QUERY_URL,
        )

    def token_snapshot(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": self.token_expires_at,
        }


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {"data": data}
    except Exception:
        return {"raw": resp.text[:2000]}
