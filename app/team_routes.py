from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from pydantic import BaseModel, Field

import team_model
from app.auth_deps import require_staff
from app.suggest_engine import preview_suggestion

router = APIRouter(prefix="/team", tags=["team-micro-model"])


class CheckRequest(BaseModel):
    proposed_response: str = Field(..., max_length=8000)
    context: str = Field(default="", max_length=4000)


class BlockRequest(BaseModel):
    text: str = Field(..., max_length=4000)


class PreviewRequest(BaseModel):
    text: str = Field(..., max_length=4000)
    proposed_response: str | None = Field(default=None, max_length=8000)


class PromoteRequest(BaseModel):
    id: str | None = None
    input: str = Field(..., max_length=2000)
    tone: str = Field(default="universal")
    response: str = Field(..., max_length=4000)
    source: str = Field(default="team_approved")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class UpdateRequest(BaseModel):
    team_opinions: list[dict] | None = None
    team_values: list[str] | None = None
    example_responses: list[dict] | None = None
    training_examples: list[dict] | None = None
    topic_overrides: list[dict] | None = None
    topic_blocks: list[dict] | None = None
    topic_shaping: list[dict] | None = None
    decision_patterns: list[dict] | None = None
    escalation_rules: list[dict] | None = None
    topics: dict | None = None
    stance_templates: dict | None = None
    vocabulary: dict | None = None
    team_tone: dict | None = None
    missing_context_rules: dict | None = None
    growth_metadata: dict | None = None


class TopicRulesUpdate(BaseModel):
    topic_overrides: list[dict] | None = None
    topic_blocks: list[dict] | None = None
    topic_shaping: list[dict] | None = None


class TrainExample(BaseModel):
    id: str | None = None
    input: str = Field(..., max_length=2000)
    tone: str = Field(default="universal")
    response: str = Field(..., max_length=4000)
    tags: list[str] = Field(default_factory=list)
    approved: bool = Field(default=False)
    source: str = Field(default="api_train")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TrainRequest(BaseModel):
    examples: list[TrainExample] = Field(..., min_length=1)
    promote: bool = Field(default=False, description="Promote examples into team_model.json")


@router.get("/model")
async def get_model():
    """Return the current team micro-model."""
    try:
        return team_model.load_model()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/update")
async def update_model(
    body: UpdateRequest,
    _staff: dict[str, Any] = Depends(require_staff),
):
    """Add or merge new opinions, examples, or topic rules (staff only)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")
    try:
        return team_model.update_model(updates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/topics")
async def get_topics():
    """View all topic control rules."""
    return team_model.get_topic_rules()


@router.post("/topics")
async def update_topics(
    body: TopicRulesUpdate,
    _staff: dict[str, Any] = Depends(require_staff),
):
    """Modify topic overrides, blocks, or shaping rules (staff only)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No topic updates provided.")
    return team_model.update_topic_rules(updates)


@router.post("/check")
async def check_response(body: CheckRequest):
    """Align a proposed AI response with the team micro-model."""
    return team_model.check_response(body.proposed_response, body.context)


@router.post("/block")
async def block_topic(body: BlockRequest):
    """Enforce topic blocking rules on user or AI text."""
    return team_model.block_topic(body.text)


@router.post("/preview")
async def preview(body: PreviewRequest):
    """Preview aligned output before saving — no training log."""
    return preview_suggestion(body.text, body.proposed_response)


@router.post("/train")
async def train_model(
    body: TrainRequest,
    _staff: dict[str, Any] = Depends(require_staff),
):
    """Submit new examples for training review (staff only)."""
    examples = [ex.model_dump() for ex in body.examples]
    return team_model.train(examples, promote=body.promote)


@router.post("/promote")
async def promote_example(
    body: PromoteRequest,
    _staff: dict[str, Any] = Depends(require_staff),
):
    """Approve an example into the live model (staff only)."""
    return team_model.promote_example(body.model_dump())


@router.get("/export")
async def export_training(
    include_unapproved: bool = Query(
        default=False, description="Include unapproved training log entries"
    ),
    _staff: dict[str, Any] = Depends(require_staff),
):
    """Export training-ready JSONL for future fine-tuning (staff only)."""
    return team_model.prepare_for_finetune(include_unapproved=include_unapproved)
