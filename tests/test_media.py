"""Phase G: media upload helpers."""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import UploadFile

from app.media import MediaUploadError, ensure_media_dirs, upload_image, upload_video


def test_upload_image_returns_public_url(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.media.MEDIA_LOCAL_DIR", media_root)
    monkeypatch.setattr("app.media.HOSTINGER_MEDIA_BASE_URL", "https://cdn.example.com")
    ensure_media_dirs()

    upload = UploadFile(filename="hero.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\nfake"))
    url = asyncio.run(upload_image(upload))
    assert url.startswith("https://cdn.example.com/images/")
    assert url.endswith(".png")
    saved = list((media_root / "images").glob("*.png"))
    assert len(saved) == 1


def test_upload_video_rejects_bad_type(tmp_path, monkeypatch):
    monkeypatch.setattr("app.media.MEDIA_LOCAL_DIR", tmp_path / "media")
    ensure_media_dirs()
    upload = UploadFile(filename="notes.txt", file=io.BytesIO(b"not a video"))
    with pytest.raises(MediaUploadError):
        asyncio.run(upload_video(upload))


def test_upload_image_local_fallback_path(tmp_path, monkeypatch):
    monkeypatch.setattr("app.media.MEDIA_LOCAL_DIR", tmp_path / "media")
    monkeypatch.setattr("app.media.HOSTINGER_MEDIA_BASE_URL", "")
    ensure_media_dirs()
    upload = UploadFile(filename="shot.jpg", file=io.BytesIO(b"jpeg-bytes"))
    url = asyncio.run(upload_image(upload))
    assert url.startswith("/media/images/")
