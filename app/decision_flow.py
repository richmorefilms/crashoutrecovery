RULES = [
    {
        "tone": "humorous",
        "patterns": [
            r"(hater|haters|clown|meltdown|rant|replying to everyone|reply to every hater|reply to haters)",
            r"\b(main character|season finale|dynamite|demolition)\b",
            r"\b(worst day|comedy of errors|disaster)\b",
            r"\b(i'm so done|over it|hate this|this is ridiculous)\b",
            r"\b(vent|scream)\b",
        ],
    },
    {
        "tone": "direct",
        "patterns": [
            r"\b(delet(e|ing|ed)|destroy(ing|ed)?|burn(ing|t)?|trash(ing)?|wipe(s|d)?)\b.*\b(all|everything|it all|account|project)\b",
            r"\b(quit|quitting|walk away|done forever|never again)\b",
            r"\b(burn it all down|reply-all|reply all)\b",
            r"\b(irreversible|can't undo|no turning back)\b",
            r"\b(screw|fuck)\s+(this|it|you|them)\b",
        ],
    },
    {
        "tone": "strategic",
        "patterns": [
            r"\b(algorithm|metrics|reach|engagement|conversion|funnel)\b",
            r"\b(strategy|strategic|optimize|test|variable|experiment)\b",
            r"\b(plan|approach|pivot|reposition)\b.*\b(not working|failed|broken)\b",
            r"\b(platform|audience|publish|launch)\b.*\b(drop|tank|crash|fail)\b",
        ],
    },
    {
        "tone": "calm",
        "patterns": [
            r"\b(overwhelmed|anxious|panicking|can't breathe|spiraling)\b",
            r"\b(heavy|sharp|intense|stacked against)\b",
            r"\b(need a moment|step back|pause|reset)\b",
            r"\b(exhausted|burnt out|burned out|drained)\b",
        ],
    },
]

DEFAULT_TONE = "universal"


def explain_match(text: str | None) -> dict:
    if not text or not text.strip():
        return {
            "tone": DEFAULT_TONE,
            "matched": False,
            "reason": "No input — defaulting to universal.",
        }

    import re

    for rule in RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "tone": rule["tone"],
                    "matched": True,
                    "reason": f"Matched {rule['tone']} pattern.",
                }

    return {
        "tone": DEFAULT_TONE,
        "matched": False,
        "reason": "No strong pattern — universal tone.",
    }
