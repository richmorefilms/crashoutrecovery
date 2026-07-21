"""TikTok Share Kit helpers — build share intents for web + mobile."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from app.ui_copy import ui_label


def normalize_hashtags(hashtags: list[str] | str | None) -> list[str]:
    if hashtags is None:
        return []
    if isinstance(hashtags, str):
        parts = [p.strip() for p in hashtags.replace(",", " ").split()]
    else:
        parts = [str(h).strip() for h in hashtags]
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        tag = p if p.startswith("#") else f"#{p.lstrip('#')}"
        if tag.lower() not in {x.lower() for x in out}:
            out.append(tag)
    return out


def build_caption(caption: str | None, hashtags: list[str]) -> str:
    base = (caption or "").strip()
    tags = " ".join(hashtags)
    if base and tags:
        return f"{base}\n\n{tags}".strip()
    return base or tags


def build_share_payload(
    *,
    video_url: str | None = None,
    caption: str | None = None,
    hashtags: list[str] | str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """
    TikTok Share Kit is primarily a native SDK.

    For web / Capacitor / React Native we return:
    - web upload URL
    - deep-link style intents (best-effort)
    - composed caption for clipboard / share sheet
    - Web Share API fields for mobile browsers
    """
    tags = normalize_hashtags(hashtags)
    # Recovery-safe default tags when none provided
    if not tags:
        tags = normalize_hashtags(["recovery", "crashoutrecovery"])
    text = build_caption(caption, tags)
    video = (video_url or "").strip() or None

    # Official web creator upload surface
    web_upload = "https://www.tiktok.com/upload?lang=en"

    # Best-effort deep links (OS / app version dependent)
    mobile_intent = "snssdk1233://aweme/share"
    if video:
        mobile_intent = f"snssdk1233://aweme/share?url={quote(video, safe='')}"

    # Universal-style fallback
    app_scheme = "tiktok://"
    share_sheet = {
        "title": title or ui_label("tiktok_share", "Share to TikTok"),
        "text": text,
        "url": video,
    }

    return {
        "ok": True,
        "platform": "tiktok",
        "mode": "share_kit",
        "video_url": video,
        "caption": text,
        "hashtags": tags,
        "share": {
            "web_upload_url": web_upload,
            "mobile_intent": mobile_intent,
            "app_scheme": app_scheme,
            "web_share": share_sheet,
            # Capacitor / RN: open URL or use Share plugin with these fields
            "clipboard_text": text,
            "instructions": (
                "Open the upload screen, paste the caption, and attach your video. "
                "On mobile, prefer the Share sheet or deep link when the app is installed."
            ),
        },
        # Mobile clients can deep-link back after share
        "mobile": {
            "use_share_sheet": True,
            "open_url": mobile_intent if video else web_upload,
            "fallback_url": web_upload,
        },
    }


def share_query_string(payload: dict[str, Any]) -> str:
    share = payload.get("share") or {}
    return urlencode(
        {
            "caption": payload.get("caption") or "",
            "video_url": payload.get("video_url") or "",
            "web_upload_url": share.get("web_upload_url") or "",
        }
    )
