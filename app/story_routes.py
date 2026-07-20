"""Public story presentation pages and APIs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.ad_system import (
    active_story_inventory,
    adsense_context,
    get_story,
    list_stories,
)
from app.config import APP_NAME, APP_TAGLINE, TEMPLATES_DIR
from app.ui_copy import ui_copy_context

router = APIRouter(tags=["stories"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/stories", response_class=HTMLResponse)
async def stories_index(request: Request):
    stories = list_stories(published_only=True, limit=50)
    return templates.TemplateResponse(
        request,
        "story/list.html",
        {
            "app_name": APP_NAME,
            "app_tagline": APP_TAGLINE,
            "stories": stories,
            "ui_copy": ui_copy_context(),
            **adsense_context(),
        },
    )


@router.get("/stories/{story_id}", response_class=HTMLResponse)
async def story_detail(request: Request, story_id: int):
    story = get_story(story_id)
    if not story or not int(story.get("published") or 0):
        raise HTTPException(status_code=404, detail="Story not found")
    inventory = active_story_inventory()
    return templates.TemplateResponse(
        request,
        "story/detail.html",
        {
            "app_name": APP_NAME,
            "app_tagline": APP_TAGLINE,
            "story": story,
            "ads": inventory,
            "ui_copy": ui_copy_context(),
            **adsense_context(),
        },
    )


@router.get("/api/stories")
async def api_list_stories(limit: int = 50):
    return list_stories(published_only=True, limit=limit)


@router.get("/api/stories/{story_id}")
async def api_get_story(story_id: int):
    story = get_story(story_id)
    if not story or not int(story.get("published") or 0):
        raise HTTPException(status_code=404, detail="Story not found")
    return story
