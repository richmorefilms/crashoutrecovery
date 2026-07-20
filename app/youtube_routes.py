"""YouTube resolve + manual override — API key stays server-side."""
from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import VIDEOS_PATH, YOUTUBE_API_KEY
from app.db import get_conn, row_to_dict, utc_now_iso

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
YT_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"
_VIDEOS_LOCK = threading.Lock()

YT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
YT_URL_RE = re.compile(
    r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?v=|embed/|shorts/))([a-zA-Z0-9_-]{11})"
)


class ResolveBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    manual_id: str | None = Field(default=None, max_length=200)
    refId: str | None = Field(default=None, max_length=64)
    persist: bool = False
    # Back-compat
    searchQuery: str | None = Field(default=None, max_length=500)


def _normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip())


def _extract_youtube_id(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="manual_id is required")
    if YT_ID_RE.fullmatch(value):
        return value
    match = YT_URL_RE.search(value)
    if match:
        return match.group(1)
    raise HTTPException(
        status_code=400,
        detail="manual_id must be an 11-character YouTube video id or watch/embed URL",
    )


def _http_get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "CrashoutRecovery/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise HTTPException(status_code=502, detail=f"YouTube API error ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"YouTube API unreachable: {exc.reason}") from exc


def _thumbnail_for(youtube_id: str | None, preferred: str | None = None) -> str | None:
    if preferred:
        return preferred
    if youtube_id:
        return f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
    return None


def _response(
    *,
    youtube_id: str | None,
    title: str | None,
    channel: str | None,
    duration: str | None,
    thumbnail: str | None,
    source: str,
    ref_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "youtubeId": youtube_id,
        "title": title,
        "channel": channel,
        "duration": duration,
        "thumbnail": thumbnail,
        "source": source,
    }
    if ref_id:
        payload["refId"] = ref_id
    return payload


def _cache_get(query: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, query, youtube_id, title, channel, duration, thumbnail_url, source, cached_at
            FROM video_cache
            WHERE query = ? COLLATE NOCASE
            """,
            (query,),
        ).fetchone()
    return row_to_dict(row)


def _cache_put(
    query: str,
    youtube_id: str | None,
    title: str | None,
    channel: str | None,
    duration: str | None,
    thumbnail_url: str | None,
    source: str,
) -> None:
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO video_cache (
                query, youtube_id, title, channel, duration, thumbnail_url, source, cached_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(query) DO UPDATE SET
                youtube_id = excluded.youtube_id,
                title = excluded.title,
                channel = excluded.channel,
                duration = excluded.duration,
                thumbnail_url = excluded.thumbnail_url,
                source = excluded.source,
                cached_at = excluded.cached_at
            """,
            (query, youtube_id, title, channel, duration, thumbnail_url, source, now),
        )


def _fetch_video_meta(youtube_id: str) -> dict[str, Any]:
    """Optional enrichment via videos.list when API key is present."""
    meta = {
        "title": None,
        "channel": None,
        "duration": None,
        "thumbnail": _thumbnail_for(youtube_id),
    }
    if not YOUTUBE_API_KEY:
        return meta

    params = urllib.parse.urlencode(
        {
            "part": "snippet,contentDetails",
            "id": youtube_id,
            "key": YOUTUBE_API_KEY,
        }
    )
    data = _http_get_json(f"{YT_VIDEOS}?{params}")
    items = data.get("items") or []
    if not items:
        return meta

    item = items[0]
    snippet = item.get("snippet") or {}
    thumbs = snippet.get("thumbnails") or {}
    high = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    meta["title"] = snippet.get("title")
    meta["channel"] = snippet.get("channelTitle")
    meta["duration"] = (item.get("contentDetails") or {}).get("duration")
    meta["thumbnail"] = high or meta["thumbnail"]
    return meta


def _upsert_videos_json(
    *,
    query: str,
    youtube_id: str,
    source: str,
    ref_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    """Create or update a clips entry. Returns the refId used."""
    path: Path = VIDEOS_PATH
    meta = meta or {}
    with _VIDEOS_LOCK:
        if not path.is_file():
            raise HTTPException(status_code=500, detail="videos.json missing")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="videos.json is invalid JSON") from exc

        clips = data.setdefault("clips", {})
        modules = data.setdefault("modules", {})

        resolved_ref = (ref_id or "").strip() or f"manual_{youtube_id}"
        is_new = resolved_ref not in clips
        clip = clips.get(resolved_ref) or {}

        title = meta.get("title") or clip.get("title") or query
        channel = meta.get("channel") if meta.get("channel") is not None else clip.get("channel")
        thumbnail = meta.get("thumbnail") or clip.get("thumbnail") or _thumbnail_for(youtube_id)
        duration = meta.get("duration") or clip.get("duration") or clip.get("durationLabel")

        clip.update(
            {
                "refId": resolved_ref,
                "youtubeId": youtube_id,
                "source": source,
                "title": title,
                "channel": channel,
                "thumbnail": thumbnail,
                "searchQuery": clip.get("searchQuery") or query,
            }
        )
        if duration:
            clip["duration"] = duration
        if is_new and "tags" not in clip:
            clip["tags"] = ["manual", "moments"]

        clips[resolved_ref] = clip

        # Surface new creator adds in Moments ordering (momentum module)
        momentum = modules.setdefault("momentum", [])
        if resolved_ref not in momentum:
            momentum.insert(0, resolved_ref)

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return resolved_ref


def _resolve_manual(query: str, manual_id: str, ref_id: str | None) -> dict[str, Any]:
    youtube_id = _extract_youtube_id(manual_id)
    meta = _fetch_video_meta(youtube_id)
    title = meta.get("title") or query
    channel = meta.get("channel")
    duration = meta.get("duration")
    thumbnail = meta.get("thumbnail") or _thumbnail_for(youtube_id)

    _cache_put(query, youtube_id, title, channel, duration, thumbnail, "manual")
    saved_ref = _upsert_videos_json(
        query=query,
        youtube_id=youtube_id,
        source="manual",
        ref_id=ref_id,
        meta={"title": title, "channel": channel, "duration": duration, "thumbnail": thumbnail},
    )

    return _response(
        youtube_id=youtube_id,
        title=title,
        channel=channel,
        duration=duration,
        thumbnail=thumbnail,
        source="manual",
        ref_id=saved_ref,
    )


def _resolve_auto(query: str, ref_id: str | None = None, *, persist: bool = False) -> dict[str, Any]:
    cached = _cache_get(query)
    if cached and cached.get("youtube_id"):
        source = cached.get("source") or "auto"
        youtube_id = cached.get("youtube_id")
        title = cached.get("title")
        channel = cached.get("channel")
        duration = cached.get("duration")
        thumbnail = _thumbnail_for(youtube_id, cached.get("thumbnail_url"))
        saved_ref = None
        if persist and youtube_id:
            saved_ref = _upsert_videos_json(
                query=query,
                youtube_id=youtube_id,
                source=source,
                ref_id=ref_id,
                meta={
                    "title": title,
                    "channel": channel,
                    "duration": duration,
                    "thumbnail": thumbnail,
                },
            )
        return _response(
            youtube_id=youtube_id,
            title=title,
            channel=channel,
            duration=duration,
            thumbnail=thumbnail,
            source=source,
            ref_id=saved_ref or ref_id,
        )

    if not YOUTUBE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="YouTube API key not configured. Set CRASHOUT_YOUTUBE_API_KEY on the server.",
        )

    search_params = urllib.parse.urlencode(
        {
            "part": "snippet",
            "type": "video",
            "maxResults": 1,
            "q": query,
            "key": YOUTUBE_API_KEY,
        }
    )
    search_data = _http_get_json(f"{YT_SEARCH}?{search_params}")
    items = search_data.get("items") or []
    if not items:
        raise HTTPException(status_code=404, detail="No YouTube video found for that query")

    item = items[0]
    youtube_id = (item.get("id") or {}).get("videoId")
    snippet = item.get("snippet") or {}
    title = snippet.get("title")
    channel = snippet.get("channelTitle")
    thumbs = snippet.get("thumbnails") or {}
    thumbnail = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    duration = None

    if youtube_id:
        enriched = _fetch_video_meta(youtube_id)
        title = title or enriched.get("title")
        channel = channel or enriched.get("channel")
        duration = enriched.get("duration")
        thumbnail = thumbnail or enriched.get("thumbnail")

    thumbnail = thumbnail or _thumbnail_for(youtube_id)
    _cache_put(query, youtube_id, title, channel, duration, thumbnail, "auto")

    saved_ref = None
    if youtube_id and (persist or ref_id):
        saved_ref = _upsert_videos_json(
            query=query,
            youtube_id=youtube_id,
            source="auto",
            ref_id=ref_id,
            meta={"title": title, "channel": channel, "duration": duration, "thumbnail": thumbnail},
        )

    return _response(
        youtube_id=youtube_id,
        title=title,
        channel=channel,
        duration=duration,
        thumbnail=thumbnail,
        source="auto",
        ref_id=saved_ref or ref_id,
    )


def resolve(
    query: str,
    *,
    manual_id: str | None = None,
    ref_id: str | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    normalized = _normalize_query(query)
    if not normalized:
        raise HTTPException(status_code=400, detail="query is required")

    if manual_id:
        return _resolve_manual(normalized, manual_id, ref_id)
    # Creator "Add Video" without manual_id still persists a new clip when persist=True
    return _resolve_auto(normalized, ref_id, persist=persist or bool(ref_id))


@router.get("/resolve")
async def resolve_get(
    query: str | None = Query(default=None, min_length=1, max_length=500),
    searchQuery: str | None = Query(default=None, min_length=1, max_length=500),
    manual_id: str | None = Query(default=None, max_length=200),
    refId: str | None = Query(default=None, max_length=64),
    persist: bool = Query(False),
):
    q = query or searchQuery
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    return resolve(q, manual_id=manual_id, ref_id=refId, persist=persist)


@router.post("/resolve")
async def resolve_post(body: ResolveBody):
    q = body.query or body.searchQuery
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    # Adding via modal always persists when manual_id is set; otherwise honor persist flag
    persist = body.persist or bool(body.manual_id) or bool(body.refId)
    return resolve(q, manual_id=body.manual_id, ref_id=body.refId, persist=persist)
