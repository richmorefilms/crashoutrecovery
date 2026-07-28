"""Hostinger-oriented media uploads with local filesystem fallback."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import HOSTINGER_MEDIA_BASE_URL, MEDIA_LOCAL_DIR

_SAFE_EXT = re.compile(r"^[a-z0-9]{1,8}$", re.IGNORECASE)

IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "gif", "webp"})
VIDEO_EXTENSIONS = frozenset({"mp4", "webm", "mov", "m4v"})

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_VIDEO_BYTES = 80 * 1024 * 1024


class MediaUploadError(ValueError):
    """Invalid or oversized media upload."""


def _extension(filename: str | None, allowed: frozenset[str], default: str) -> str:
    raw = (filename or "").rsplit(".", 1)
    ext = raw[-1].lower() if len(raw) == 2 else default
    if not _SAFE_EXT.match(ext) or ext not in allowed:
        raise MediaUploadError(f"Unsupported file type: .{ext}")
    return ext


def _public_url(relative_path: str) -> str:
    rel = relative_path.lstrip("/")
    if HOSTINGER_MEDIA_BASE_URL:
        return f"{HOSTINGER_MEDIA_BASE_URL}/{rel}"
    return f"/media/{rel}"


async def _save_upload(
    file: UploadFile,
    *,
    kind: str,
    allowed: frozenset[str],
    max_bytes: int,
    default_ext: str,
) -> str:
    ext = _extension(file.filename, allowed, default_ext)
    payload = await file.read()
    if not payload:
        raise MediaUploadError("Empty upload")
    if len(payload) > max_bytes:
        raise MediaUploadError(f"File exceeds {max_bytes} bytes")

    dest_dir = MEDIA_LOCAL_DIR / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = dest_dir / name
    path.write_bytes(payload)
    return _public_url(f"{kind}/{name}")


async def upload_image(file: UploadFile) -> str:
    """Store an image and return its public URL (Hostinger base or /media)."""
    return await _save_upload(
        file,
        kind="images",
        allowed=IMAGE_EXTENSIONS,
        max_bytes=MAX_IMAGE_BYTES,
        default_ext="jpg",
    )


async def upload_video(file: UploadFile) -> str:
    """Store a video and return its public URL (Hostinger base or /media)."""
    return await _save_upload(
        file,
        kind="videos",
        allowed=VIDEO_EXTENSIONS,
        max_bytes=MAX_VIDEO_BYTES,
        default_ext="mp4",
    )


def save_video_bytes(
    content: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    """Persist raw video bytes into the media pipeline; return public URL."""
    if not content:
        raise MediaUploadError("Empty upload")
    if len(content) > MAX_VIDEO_BYTES:
        raise MediaUploadError(f"File exceeds {MAX_VIDEO_BYTES} bytes")
    # Prefer filename extension; fall back from content-type
    default = "mp4"
    if content_type and "webm" in content_type:
        default = "webm"
    ext = _extension(filename, VIDEO_EXTENSIONS, default)
    dest_dir = MEDIA_LOCAL_DIR / "videos"
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = dest_dir / name
    path.write_bytes(content)
    return _public_url(f"videos/{name}")


def ensure_media_dirs() -> Path:
    """Create local media directories used as Hostinger staging/fallback."""
    (MEDIA_LOCAL_DIR / "images").mkdir(parents=True, exist_ok=True)
    (MEDIA_LOCAL_DIR / "videos").mkdir(parents=True, exist_ok=True)
    return MEDIA_LOCAL_DIR
