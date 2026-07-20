from fastapi import HTTPException

TONE_TEMPLATES: dict[str, str] = {
    "universal": "crashout.html",
    "calm": "crashout_calm.html",
    "humorous": "crashout_humorous.html",
    "direct": "crashout_direct.html",
    "strategic": "crashout_strategic.html",
}

DEFAULT_TONE = "universal"


def resolve_tone(tone: str | None) -> str:
    if not tone:
        return DEFAULT_TONE
    key = tone.lower().strip()
    if key not in TONE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tone '{tone}'. Valid: {', '.join(TONE_TEMPLATES)}",
        )
    return key


def fragment_template(tone: str | None) -> str:
    return TONE_TEMPLATES[resolve_tone(tone)]
