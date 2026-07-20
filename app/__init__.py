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
from app.suggest_engine import build_suggestion
from app.staff_routes import router as staff_router
from app.story_routes import router as story_router
from app.team_routes import router as team_router
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
    app.include_router(auth_router)
    app.include_router(user_data_router)
    app.include_router(team_router)
    app.include_router(youtube_router)
    app.include_router(compose_router)
    app.include_router(staff_router)
    app.include_router(story_router)
    app.include_router(ads_router)
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}

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

    return app
