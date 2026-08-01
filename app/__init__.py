from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.auth_deps import AuthMiddleware
from app.auth_routes import router as auth_router
from app.compose_routes import router as compose_router
from app.db import init_db, migrate, open_connection
from app.financial_model import (
    build_seeded_growth_projection,
    build_valuation_projection,
)
from app.media import ensure_media_dirs
from app.config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    BASE_DIR,
    MEDIA_LOCAL_DIR,
    STATIC_DIR,
    TEMPLATES_DIR,
    UI_COPY_PATH,
    VIDEOS_PATH,
    assert_jwt_secret_safe,
)
from app.ads_routes import router as ads_router
from app.creator_routes import router as creator_router
from app.feed_routes import router as feed_router
from app.growth_routes import router as growth_router
from app.monetization_routes import router as monetization_router
from app.multiplatform_routes import router as multiplatform_router
from app.oauth_routes import router as oauth_router
from app.public_api_routes import router as public_api_router
from app.ranking_routes import router as ranking_router
from app.recommendation_routes import router as recommendation_router
from app.suggest_engine import build_suggestion
from app.staff_routes import router as staff_router
from app.story_routes import router as story_router
from app.team_routes import router as team_router
from app.tiktok_routes import router as tiktok_router
from app.tones import DEFAULT_TONE, TONE_TEMPLATES, resolve_tone
from app.ui_copy import ui_copy_context
from app.user_data_routes import router as user_data_router
from app.youtube_routes import router as youtube_router


class SuggestRequest(BaseModel):
    text: str = Field(default="", max_length=4000)


class ValuationRequest(BaseModel):
    user_count: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0, le=1)
    arpu: float = Field(..., ge=0)
    ev_sales_multiple: float = Field(default=1.8, ge=0)


class SeededGrowthRequest(BaseModel):
    launch_users: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0, le=1)
    retention_rate: float = Field(..., ge=0, le=1)
    arpu: float = Field(..., ge=0)
    ev_sales_multiple: float = Field(default=1.8, ge=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Phase B: DB init + migration ladder once at startup (not at import)."""
    init_db()
    conn = open_connection()
    try:
        migrate(conn)
    finally:
        conn.close()
    ensure_media_dirs()
    yield


def create_app() -> FastAPI:
    # Phase A: reject known-default JWT secrets outside development/test.
    assert_jwt_secret_safe()
    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    ensure_media_dirs()
    app.mount("/media", StaticFiles(directory=str(MEDIA_LOCAL_DIR)), name="media")

    # --- API routers first (never after HTML pages; avoid /api/* shadowing) ---
    app.include_router(feed_router, prefix="/api/feed")
    app.include_router(recommendation_router)
    app.include_router(growth_router)
    app.include_router(multiplatform_router)
    app.include_router(monetization_router)
    app.include_router(public_api_router)
    app.include_router(youtube_router)
    app.include_router(tiktok_router)
    app.include_router(ranking_router)
    app.include_router(oauth_router)
    app.include_router(creator_router)
    app.include_router(auth_router)
    app.include_router(user_data_router)
    app.include_router(team_router)
    app.include_router(compose_router)
    app.include_router(staff_router)
    app.include_router(story_router)
    app.include_router(ads_router)

    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}

    @app.get("/api/tones")
    async def list_tones():
        return {"tones": list(TONE_TEMPLATES.keys()), "default": DEFAULT_TONE}

    @app.get("/api/crashout")
    async def crashout_json(tone: str | None = Query(default=DEFAULT_TONE)):
        selected = resolve_tone(tone)
        return {
            "tone": selected,
            "template": TONE_TEMPLATES[selected],
        }

    @app.post("/api/suggest")
    async def suggest_tone(body: SuggestRequest):
        return build_suggestion(body.text)

    @app.post("/api/valuation")
    async def valuation(body: ValuationRequest):
        return build_valuation_projection(
            user_count=body.user_count,
            conversion_rate=body.conversion_rate,
            arpu=body.arpu,
            ev_sales_multiple=body.ev_sales_multiple,
        )

    @app.post("/api/growth-valuation")
    async def growth_valuation(body: SeededGrowthRequest):
        return build_seeded_growth_projection(
            launch_users=body.launch_users,
            conversion_rate=body.conversion_rate,
            retention_rate=body.retention_rate,
            arpu=body.arpu,
            ev_sales_multiple=body.ev_sales_multiple,
        )

    # --- Exact HTML page routes (no catch-alls; do not shadow /api/*) ---
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request, tone: str | None = Query(default=DEFAULT_TONE)):
        selected = resolve_tone(tone)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "tone": selected,
                "tones": list(TONE_TEMPLATES.keys()),
                "ui_copy": ui_copy_context(),
            },
        )

    @app.get("/UI_COPY.json")
    async def ui_copy_json():
        return FileResponse(
            UI_COPY_PATH,
            media_type="application/json; charset=utf-8",
            filename="UI_COPY.json",
        )

    @app.get("/videos.json")
    async def videos_json():
        return FileResponse(
            VIDEOS_PATH,
            media_type="application/json; charset=utf-8",
            filename="videos.json",
        )

    @app.get("/ops", response_class=HTMLResponse)
    async def ops_manual(request: Request):
        return templates.TemplateResponse(
            request,
            "ops_manual.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "ui_copy": ui_copy_context(),
            },
        )

    @app.get("/ops.md")
    async def ops_manual_markdown():
        path = BASE_DIR / "PLAIN_OPS.md"
        return FileResponse(
            path,
            media_type="text/markdown; charset=utf-8",
            filename="Crashout-Recovery-Plain-Ops.md",
        )

    @app.get("/ops-full.md")
    async def ops_manual_full_markdown():
        path = BASE_DIR / "OPERATIONS.md"
        return FileResponse(
            path,
            media_type="text/markdown; charset=utf-8",
            filename="Crashout-Recovery-OPERATIONS.md",
        )

    @app.get("/manual", response_class=HTMLResponse)
    async def ops_manual_alias(request: Request):
        return await ops_manual(request)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "ui_copy": ui_copy_context(),
            },
        )

    @app.get("/login/tiktok", response_class=HTMLResponse)
    async def login_tiktok_page(request: Request):
        return templates.TemplateResponse(
            request,
            "login_tiktok.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "ui_copy": ui_copy_context(),
            },
        )

    @app.get("/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "ui_copy": ui_copy_context(),
            },
        )

    @app.get("/feed", response_class=HTMLResponse)
    async def feed_page(request: Request):
        return templates.TemplateResponse(
            request,
            "feed_tiktok.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "ui_copy": ui_copy_context(),
            },
        )

    @app.get("/feed/tiktok", response_class=HTMLResponse)
    async def feed_tiktok_page(request: Request):
        return templates.TemplateResponse(
            request,
            "feed_tiktok.html",
            {
                "app_name": APP_NAME,
                "app_tagline": APP_TAGLINE,
                "ui_copy": ui_copy_context(),
            },
        )

    def _page_ctx(**extra):
        ctx = {
            "app_name": APP_NAME,
            "app_tagline": APP_TAGLINE,
            "ui_copy": ui_copy_context(),
        }
        ctx.update(extra)
        return ctx

    @app.get("/feed/all", response_class=HTMLResponse)
    async def feed_all_page(request: Request):
        return templates.TemplateResponse(request, "feed_all.html", _page_ctx())

    @app.get("/feed/trending", response_class=HTMLResponse)
    async def feed_trending_page(request: Request):
        return templates.TemplateResponse(request, "feed_trending.html", _page_ctx())

    @app.get("/feed/recommended", response_class=HTMLResponse)
    async def feed_recommended_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "recommended_feed.html", _page_ctx(user_id=id or "")
        )

    @app.get("/youtube/video/{video_id}", response_class=HTMLResponse)
    async def youtube_video_page(request: Request, video_id: str):
        return templates.TemplateResponse(
            request, "youtube_video.html", _page_ctx(video_id=video_id)
        )

    @app.get("/youtube/channel/{channel_id}", response_class=HTMLResponse)
    async def youtube_channel_page(request: Request, channel_id: str):
        return templates.TemplateResponse(
            request, "youtube_channel.html", _page_ctx(channel_id=channel_id)
        )

    @app.get("/youtube/search", response_class=HTMLResponse)
    async def youtube_search_page(
        request: Request, q: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "youtube_search.html", _page_ctx(query=q or "")
        )

    @app.get("/oauth/youtube", response_class=HTMLResponse)
    async def oauth_youtube_login_page(request: Request):
        return templates.TemplateResponse(
            request, "oauth_youtube_login.html", _page_ctx()
        )

    @app.get("/oauth/youtube/callback", response_class=HTMLResponse)
    async def oauth_youtube_callback_page(request: Request):
        return templates.TemplateResponse(
            request, "oauth_youtube_callback.html", _page_ctx()
        )

    @app.get("/manifest.webmanifest")
    async def pwa_manifest():
        path = STATIC_DIR / "manifest.webmanifest"
        return FileResponse(
            path,
            media_type="application/manifest+json",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/sw.js")
    async def pwa_service_worker():
        path = STATIC_DIR / "sw.js"
        return FileResponse(
            path,
            media_type="application/javascript; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Service-Worker-Allowed": "/",
            },
        )

    @app.get("/offline", response_class=HTMLResponse)
    async def offline_page(request: Request):
        return templates.TemplateResponse(request, "offline.html", _page_ctx())

    @app.get("/creator/home", response_class=HTMLResponse)
    async def creator_home_page(request: Request):
        return templates.TemplateResponse(request, "creator_home.html", _page_ctx())

    @app.get("/creator/studio", response_class=HTMLResponse)
    async def creator_studio_page(request: Request):
        return templates.TemplateResponse(request, "clip_studio.html", _page_ctx())

    @app.get("/creator/badges", response_class=HTMLResponse)
    async def creator_badges_page(request: Request):
        return templates.TemplateResponse(request, "creator_badges.html", _page_ctx())

    @app.get("/topics/radar", response_class=HTMLResponse)
    async def topics_radar_page(request: Request):
        return templates.TemplateResponse(
            request, "opportunity_radar.html", _page_ctx()
        )

    @app.get("/recovery/mode", response_class=HTMLResponse)
    async def recovery_mode_page(request: Request):
        return templates.TemplateResponse(request, "recovery_mode.html", _page_ctx())

    @app.get("/notifications", response_class=HTMLResponse)
    async def notifications_page(request: Request):
        return templates.TemplateResponse(request, "notifications.html", _page_ctx())

    @app.get("/economy", response_class=HTMLResponse)
    async def creator_economy_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "creator_economy.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/creator/profile", response_class=HTMLResponse)
    async def creator_identity_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "creator_identity.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/social", response_class=HTMLResponse)
    async def social_layer_page(request: Request):
        return templates.TemplateResponse(request, "social_layer.html", _page_ctx())

    @app.get("/challenges", response_class=HTMLResponse)
    async def creator_challenges_page(request: Request):
        return templates.TemplateResponse(
            request, "creator_challenges.html", _page_ctx()
        )

    @app.get("/assistant", response_class=HTMLResponse)
    async def creator_assistant_page(request: Request):
        return templates.TemplateResponse(
            request, "creator_assistant.html", _page_ctx()
        )

    @app.get("/vault", response_class=HTMLResponse)
    async def creator_vault_page(request: Request):
        return templates.TemplateResponse(request, "creator_vault.html", _page_ctx())

    @app.get("/feed/signals", response_class=HTMLResponse)
    async def feed_signals_page(request: Request):
        return templates.TemplateResponse(request, "feed_signals.html", _page_ctx())

    @app.get("/rooms", response_class=HTMLResponse)
    async def creator_rooms_page(request: Request):
        return templates.TemplateResponse(request, "creator_rooms.html", _page_ctx())

    @app.get("/creator/studio/pro", response_class=HTMLResponse)
    async def creator_studio_pro_page(request: Request):
        return templates.TemplateResponse(request, "clip_studio_pro.html", _page_ctx())

    @app.get("/recovery/journal", response_class=HTMLResponse)
    async def recovery_journal_page(request: Request):
        return templates.TemplateResponse(
            request, "recovery_journal.html", _page_ctx()
        )

    @app.get("/sync", response_class=HTMLResponse)
    async def creator_sync_page(request: Request):
        return templates.TemplateResponse(request, "creator_sync.html", _page_ctx())

    @app.get("/developer/api", response_class=HTMLResponse)
    async def developer_api_page(request: Request):
        return templates.TemplateResponse(request, "developer_api.html", _page_ctx())

    @app.get("/creator/dashboard", response_class=HTMLResponse)
    async def creator_dashboard_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "creator_dashboard.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/monetization", response_class=HTMLResponse)
    async def monetization_lanes_page(request: Request):
        return templates.TemplateResponse(
            request, "monetization_lanes.html", _page_ctx()
        )

    @app.get("/monetization/ads", response_class=HTMLResponse)
    async def monetization_ads_page(request: Request):
        return templates.TemplateResponse(
            request, "monetization_ads.html", _page_ctx()
        )

    @app.get("/earnings", response_class=HTMLResponse)
    async def creator_earnings_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "creator_earnings.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/ranked", response_class=HTMLResponse)
    async def ranked_feed_page(request: Request):
        return templates.TemplateResponse(request, "ranked_feed.html", _page_ctx())

    @app.get("/personalized", response_class=HTMLResponse)
    async def personalized_feed_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "personalized_feed.html", _page_ctx(user_id=id or "")
        )

    @app.get("/recommendations", response_class=HTMLResponse)
    async def recommendations_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "recommendations.html", _page_ctx(user_id=id or "")
        )

    @app.get("/topics", response_class=HTMLResponse)
    async def topic_clusters_page(request: Request):
        return templates.TemplateResponse(
            request, "topic_clusters.html", _page_ctx()
        )

    @app.get("/topic-graph", response_class=HTMLResponse)
    async def topic_graph_page(request: Request):
        return templates.TemplateResponse(request, "topic_graph.html", _page_ctx())

    @app.get("/growth/score", response_class=HTMLResponse)
    async def growth_score_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "growth_score.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/growth/trends", response_class=HTMLResponse)
    async def growth_trends_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "growth_trends.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/growth/opportunities", response_class=HTMLResponse)
    async def growth_opportunities_page(
        request: Request, id: str | None = Query(default=None)
    ):
        return templates.TemplateResponse(
            request, "growth_opportunities.html", _page_ctx(creator_id=id or "")
        )

    @app.get("/staff/overview", response_class=HTMLResponse)
    async def staff_overview_page(request: Request):
        return templates.TemplateResponse(
            request, "staff_overview.html", _page_ctx()
        )

    @app.get("/staff/flags", response_class=HTMLResponse)
    async def staff_flags_page(request: Request):
        return templates.TemplateResponse(request, "staff_flags.html", _page_ctx())

    @app.get("/public", response_class=HTMLResponse)
    async def public_home_page(request: Request):
        return templates.TemplateResponse(request, "home_public.html", _page_ctx())

    @app.get("/publish", response_class=HTMLResponse)
    async def publish_ready_page(request: Request):
        return templates.TemplateResponse(request, "publish_ready.html", _page_ctx())

    @app.get("/multi/instagram", response_class=HTMLResponse)
    async def multi_instagram_page(request: Request):
        return templates.TemplateResponse(
            request, "multi_instagram.html", _page_ctx()
        )

    @app.get("/multi/facebook", response_class=HTMLResponse)
    async def multi_facebook_page(request: Request):
        return templates.TemplateResponse(
            request, "multi_facebook.html", _page_ctx()
        )

    @app.get("/multi/twitter", response_class=HTMLResponse)
    async def multi_twitter_page(request: Request):
        return templates.TemplateResponse(request, "multi_twitter.html", _page_ctx())

    @app.get("/multi/pinterest", response_class=HTMLResponse)
    async def multi_pinterest_page(request: Request):
        return templates.TemplateResponse(
            request, "multi_pinterest.html", _page_ctx()
        )

    @app.get("/embed", response_class=HTMLResponse)
    async def embed(request: Request, tone: str | None = Query(default=DEFAULT_TONE)):
        selected = resolve_tone(tone)
        return templates.TemplateResponse(
            request,
            "embed.html",
            {
                "tone": selected,
            },
        )

    @app.get("/crashout", response_class=HTMLResponse)
    async def crashout_fragment(
        request: Request,
        tone: str | None = Query(default=DEFAULT_TONE),
    ):
        selected = resolve_tone(tone)
        return templates.TemplateResponse(
            request,
            TONE_TEMPLATES[selected],
            {"tone": selected},
        )

    return app
