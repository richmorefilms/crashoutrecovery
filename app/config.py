from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from project .env without requiring python-dotenv."""
    path = BASE_DIR / ".env"
    if not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


_load_dotenv()

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
TEAM_MODEL_PATH = BASE_DIR / "team_model.json"
UI_COPY_PATH = BASE_DIR / "UI_COPY.json"
VIDEOS_PATH = BASE_DIR / "videos.json"
PATTERN_LOG_PATH = DATA_DIR / "pattern_log.jsonl"
TRAINING_LOG_PATH = DATA_DIR / "training_log.jsonl"
EXAMPLE_PACK_PATH = DATA_DIR / "language_pack_examples.json"
FINETUNE_EXPORT_PATH = DATA_DIR / "finetune_export.jsonl"
DATABASE_PATH = DATA_DIR / "crashout.db"

APP_NAME = "Crashout Recovery"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Friendly redirects for adults 18+"
HOST = "127.0.0.1"
PORT = 8777

# YouTube Data API v3 — server only; never ship to the browser
YOUTUBE_API_KEY = os.environ.get("CRASHOUT_YOUTUBE_API_KEY", "").strip()

# Local/dev marker. Non-development environments reject the default JWT secret.
CRASHOUT_ENV = os.environ.get("CRASHOUT_ENV", "development").strip().lower()
DEV_ENVIRONMENTS = frozenset({"development", "dev", "test"})

DEV_JWT_SECRET = "crashout-dev-secret-change-me-please-32b+"
JWT_SECRET = os.environ.get("CRASHOUT_JWT_SECRET", DEV_JWT_SECRET)
JWT_ALGORITHM = "HS256"
# Short-lived access token (default 20 minutes)
JWT_EXPIRE_SECONDS = int(os.environ.get("CRASHOUT_JWT_EXPIRE", str(20 * 60)))
# Refresh token (default 14 days)
JWT_REFRESH_EXPIRE_SECONDS = int(
    os.environ.get("CRASHOUT_JWT_REFRESH_EXPIRE", str(60 * 60 * 24 * 14))
)


def assert_jwt_secret_safe() -> None:
    """Refuse known-default JWT secrets outside development/test."""
    if JWT_SECRET == DEV_JWT_SECRET and CRASHOUT_ENV not in DEV_ENVIRONMENTS:
        raise RuntimeError(
            "CRASHOUT_JWT_SECRET is still the development default. "
            "Set a strong secret, or set CRASHOUT_ENV=development for local use only."
        )


# Phase G — media origin (Hostinger CDN/base URL) + local fallback under data/media
HOSTINGER_MEDIA_BASE_URL = os.environ.get(
    "HOSTINGER_MEDIA_BASE_URL",
    os.environ.get("CRASHOUT_MEDIA_BASE_URL", ""),
).strip().rstrip("/")
MEDIA_LOCAL_DIR = DATA_DIR / "media"

# Web AdSense
ADSENSE_CLIENT_ID = os.environ.get("CRASHOUT_ADSENSE_CLIENT_ID", "").strip()
ADSENSE_SLOT_TOP = os.environ.get("CRASHOUT_ADSENSE_SLOT_TOP", "").strip()
ADSENSE_SLOT_MID = os.environ.get("CRASHOUT_ADSENSE_SLOT_MID", "").strip()
ADSENSE_SLOT_FOOTER = os.environ.get("CRASHOUT_ADSENSE_SLOT_FOOTER", "").strip()

# Mobile AdMob (delivered to apps via /ads/mobile-config)
ADMOB_APP_ID = os.environ.get("CRASHOUT_ADMOB_APP_ID", "").strip()
ADMOB_AD_UNIT_ID = os.environ.get("CRASHOUT_ADMOB_AD_UNIT_ID", "").strip()
ADMOB_BANNER_UNIT_ID = os.environ.get("CRASHOUT_ADMOB_BANNER_UNIT_ID", "").strip()
ADMOB_INTERSTITIAL_UNIT_ID = os.environ.get(
    "CRASHOUT_ADMOB_INTERSTITIAL_UNIT_ID", ""
).strip()

# TikTok Open Platform (Login Kit / Content Posting / Display)
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
TIKTOK_REDIRECT_URI = os.environ.get(
    "TIKTOK_REDIRECT_URI", "http://127.0.0.1:8777/auth/tiktok/callback"
).strip()
TIKTOK_MOBILE_REDIRECT_URI = os.environ.get(
    "TIKTOK_MOBILE_REDIRECT_URI", "crashout://tiktok/callback"
).strip()
# Optional app-level tokens (Display/Research) when user OAuth is not used
TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
TIKTOK_REFRESH_TOKEN = os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip()
TIKTOK_SCOPES = os.environ.get(
    "TIKTOK_SCOPES",
    "user.info.basic,video.upload,video.publish",
).strip()