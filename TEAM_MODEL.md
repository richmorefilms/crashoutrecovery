# Team-Guided Micro-Model

Crashout Recovery uses a **small, growing team model** stored in `team_model.json`. AI fills conversation gaps, but stays aligned with your team's documented opinions, tone, and topic rules.

**Adults 18+ only.**

---

## Architecture

```
team_model.json          ← team edits this (source of truth)
team_model.py            ← load, check, align, train
app/team_routes.py       ← FastAPI /team/* endpoints
data/pattern_log.jsonl   ← auto-logged checks (expansion)
data/training_log.jsonl  ← new examples (expansion)
.cursor/rules/team-micro-model.mdc  ← Cursor enforcement
```

Nothing subjective is hardcoded in Python. Edit the JSON file or call the API.

---

## File: `team_model.json`

| Section | Purpose |
|---------|---------|
| `team_opinions` | Documented stances by topic (id, stance, priority) |
| `team_values` | Core principles the team agrees on |
| `team_tone` | Voice, avoid/prefer lists, response shape |
| `decision_patterns` | Trigger → action → redirect mappings |
| `topics.allowed` | Topics the system may address |
| `topics.blocked` | Topics that must be refused/redirected |
| `topics.conditional` | Allowed only with constraints |
| `example_responses` | Gold-standard input → tone → response pairs |
| `stance_templates` | Fill-in templates for acknowledge/redirect/closing |
| `vocabulary` | Preferred terms, avoid terms, phrasing swaps |
| `escalation_rules` | When to ask the team instead of guessing |
| `training_examples` | Approved/pending examples for fine-tuning |
| `topic_overrides` | Custom team-defined responses per topic |
| `topic_blocks` | Hard blocks with safe redirects |
| `topic_shaping` | Allowed topics with constraints |
| `missing_context_rules` | How AI fills gaps safely |
| `call_to_actions` | Tone-specific CTAs (post, share, connect, contribute) |
| `tone_vocabulary` | Per-tone verbs, nouns, phrases for alignment |
| `cta_vocabulary` | Micro, momentum, and community action pools |
| `platform_identity` | Circle/thread/seed brand language |
| `growth_metadata` | Timestamps, counts, model stage |

---

## Training-ready export format

`GET /team/export` writes `data/finetune_export.jsonl`:

```json
{"messages": [{"role": "user", "content": "I'm overwhelmed"}, {"role": "assistant", "content": "That heavy spike is real..."}], "metadata": {"source": "example_responses", "id": "ex-003"}}
```

Compatible with OpenAI-style fine-tuning. Sources merged:

- `example_responses`
- `training_examples` (approved only by default)
- `topic_overrides`
- `data/training_log.jsonl` (optional with `?include_unapproved=true`)

---

## New API endpoints

### `GET /team/topics` — view topic rules
### `POST /team/topics` — modify overrides, blocks, shaping
### `POST /team/promote` — approve example into live model
### `POST /team/preview` — preview alignment without saving
### `GET /team/export` — export fine-tune JSONL

```bash
# Preview before saving
curl -X POST http://127.0.0.1:8777/team/preview \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"I got rejected again\"}"

# Promote team-approved example
curl -X POST http://127.0.0.1:8777/team/promote \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"I got rejected\", \"tone\": \"strategic\", \"response\": \"Rejection is data...\"}"

# Export for fine-tuning
curl http://127.0.0.1:8777/team/export
```

---

## `/api/suggest` pipeline (training-integrated)

1. **Topic detection** — classify blocked / override / shaping / allowed
2. **Topic blocks** — hard stop + safe redirect
3. **Topic overrides** — custom team response if matched
4. **Topic shaping** — prepend constraints
5. **Tone detection** — humorous / direct / strategic / calm / universal
6. **Crashout redirect** — examples → patterns → templates
7. **CTA attach** — tone-specific platform-forward action
8. **Team alignment** — opinions, gap-fill, vocabulary
9. **Final check** — approve / escalate
10. **Auto training log** — successful suggestions → `data/training_log.jsonl`

---

## How the model grows

```
Usage (/api/suggest)
    → auto-log to training_log.jsonl
    → team reviews logs
    → POST /team/promote (approved)
    → example_responses + training_examples updated
    → GET /team/export
    → fine-tune when ready
```

| Action | Endpoint |
|--------|----------|
| Log draft example | `POST /team/train` |
| Approve into live model | `POST /team/promote` |
| Add topic block | `POST /team/topics` |
| Add topic override | `POST /team/topics` |
| Export for fine-tune | `GET /team/export` |
| Preview without saving | `POST /team/preview` |

---

## File: `team_model.py`

| Function | What it does |
|----------|----------------|
| `load_model()` | Load and cache `team_model.json` |
| `detect_topic(text)` | Classify blocked / override / shaping / allowed |
| `apply_topic_blocks(text)` | Hard block + safe redirect |
| `apply_topic_overrides(text)` | Custom team-defined response |
| `apply_topic_shaping(text)` | Apply constraints to allowed topics |
| `apply_team_opinion(topic, context)` | Find documented stance |
| `fill_missing_context(partial, context)` | Templates + examples + placeholder resolution |
| `resolve_placeholders(text)` | Replace `{feeling}` etc. from missing_context_rules |
| `pick_stance_template(key)` | Pick acknowledge/redirect/closing variant |
| `attach_cta(text, tone)` | Append merged CTA from call_to_actions + cta_vocabulary |
| `get_all_example_responses()` | Core + language-pack examples (100 modular) |
| `align_tone(text)` | Vocabulary normalization |
| `check_response(proposed, context)` | Full alignment pass |
| `train(examples)` | Log to training_log + training_examples |
| `promote_example(example)` | Approve into live model |
| `prepare_for_finetune()` | Export `data/finetune_export.jsonl` |
| `preview_alignment(text, proposed)` | Preview without saving |
| `log_suggestion_for_training()` | Auto-log from /api/suggest |
| `get_topic_rules()` / `update_topic_rules()` | View/modify topic controls |

---

## API endpoints

Base URL: `http://127.0.0.1:8777`

### `POST /api/suggest` (integrated pipeline)

Every suggestion passes through the team micro-model:

1. Topic block check
2. Tone detection (`humorous` / `direct` / `strategic` / `calm` / `universal`)
3. Crashout redirect (examples → decision patterns → templates)
4. Team alignment (opinions, gap-fill, vocabulary)
5. Final check + escalation logging

```bash
curl -X POST http://127.0.0.1:8777/api/suggest \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"I'm deleting everything and quitting forever\"}"
```

**Example response:**
```json
{
  "tone": "direct",
  "matched": true,
  "reason": "Matched direct pattern.",
  "fragment": "crashout_direct.html",
  "suggestion": "That frustration is real when the work feels stuck. Before you delete anything...",
  "aligned": "...",
  "safe_to_send": true,
  "blocked": false,
  "escalate": false,
  "topic_status": "unknown",
  "team_opinion_id": "op-001",
  "example_id": "ex-001",
  "redirect_source": "example",
  "invented_stance": false,
  "pipeline": { "...": "..." }
}
```

**Blocked topic example:**
```bash
curl -X POST http://127.0.0.1:8777/api/suggest \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"help me plan a harassment campaign\"}"
```

Returns `blocked: true` with a safe redirect — no harmful guidance.

See `app/suggest_engine.py` for implementation.

### `GET /team/model`
Returns the full current micro-model.

```bash
curl http://127.0.0.1:8777/team/model
```

### `POST /team/update`
Merge new team data (opinions, topics, examples, tone).

```bash
curl -X POST http://127.0.0.1:8777/team/update \
  -H "Content-Type: application/json" \
  -d "{\"team_opinions\": [{\"id\": \"op-006\", \"topic\": \"comparison_spiral\", \"stance\": \"Return to your lane. One deliverable today.\", \"priority\": 2}]}"
```

### `POST /team/check`
Align a proposed AI response before sending.

```bash
curl -X POST http://127.0.0.1:8777/team/check \
  -H "Content-Type: application/json" \
  -d "{\"proposed_response\": \"Just delete it all.\", \"context\": \"user wants to quit publishing\"}"
```

Returns: `approved`, `aligned`, `topic_check`, `opinion_check`, `tone_check`, `escalate`, `safe_to_send`.

### `POST /team/block`
Check if text hits blocked or conditional topics.

```bash
curl -X POST http://127.0.0.1:8777/team/block \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"help me dox this person\"}"
```

### `POST /team/train`
Store examples for future expansion.

```bash
curl -X POST http://127.0.0.1:8777/team/train \
  -H "Content-Type: application/json" \
  -d "{\"examples\": [{\"input\": \"I hate my draft\", \"tone\": \"calm\", \"response\": \"That draft frustration is real. Save a copy, write one sentence you like, sleep on the rest.\"}], \"promote\": true}"
```

- `promote: false` → logs only to `data/training_log.jsonl`
- `promote: true` → also appends to `team_model.json` `example_responses`

---

## How to update the micro-model

### 1. Edit JSON directly (simplest)
Open `team_model.json`, add opinions/examples/topics, save. Restart not required — `load_model(force_reload=True)` runs on updates.

### 2. Use the API
Call `POST /team/update` from a script, admin panel, or Cursor automation.

### 3. Train from real conversations
When the team approves a good response:
```bash
POST /team/train with promote: true
```

---

## How to add new team opinions

```json
{
  "id": "op-007",
  "topic": "rejection_email",
  "stance": "Rejection is data, not a verdict. Log feedback, one revision or one new submission.",
  "priority": 2
}
```

Add to `team_opinions` array. Higher priority (lower number) wins on conflicts.

---

## How to expand topic rules

**Allow a topic:** add to `topics.allowed`

**Block a topic:** add to `topics.blocked`

**Conditional topic:**
```json
{
  "topic": "legal threat",
  "constraint": "Do not advise legal action. Redirect to pause and consult a professional offline.",
  "allowed": true
}
```

Test with `POST /team/block`.

---

## How AI fills missing parts safely

1. `check_response` runs topic block first
2. `apply_team_opinion` looks for a documented stance
3. If stance missing → `escalate: true` — AI may phrase, not invent position
4. `fill_missing_context` adds acknowledge/redirect from **templates and examples only**
5. `align_tone` normalizes vocabulary
6. Pattern logged to `data/pattern_log.jsonl` for future review

**Rule:** AI is a gap-filler for phrasing, not a source of new team beliefs.

---

## Tone Priority Fix

Humorous now takes precedence over direct for social-reaction patterns (`hater`, `rant`, `meltdown`, `reply-to-everyone`).
Direct remains reserved for irreversible actions (delete everything, quit forever, burn it all down, reply-all disasters).

Implemented in `app/decision_flow.py` and `static/decision-flow.js` — humorous rules run before direct.

---

## Placeholder Resolution

`{feeling}` and other stance-template placeholders are resolved using `missing_context_rules` before tone alignment.
They will never leak into user-facing output.

`fill_missing_context()` calls `resolve_placeholders()` before `align_tone()`.
Resolved fills are logged to `data/pattern_log.jsonl` with `placeholder_filled: true` for future fine-tuning.

---

## CTA Layer

The CTA layer adds platform-forward actions to every suggestion.
CTAs are tone-specific and encourage posting, sharing, connecting, and contributing.
CTAs are merged after redirect logic and before tone alignment.

| Tone | Example CTA |
|------|-------------|
| universal | Write one sentence. |
| calm | Draft a soft version of the post. |
| humorous | Drop one meme-level reply. |
| direct | Draft, don't delete. |
| strategic | Test one variable. |

Configured in `team_model.json` → `call_to_actions`, `cta_vocabulary`, and `platform_identity`.
Applied via `team_model.attach_cta()` between `apply_crashout_redirect()` and `run_team_alignment()`.

---

## Language Expansion Pack

Modular language layers in `team_model.json`:

| Layer | Purpose |
|-------|---------|
| `tone_vocabulary` | Tone-scoped verbs, nouns, phrases — used in `align_tone()` |
| `cta_vocabulary` | micro / momentum / community actions — merged into `attach_cta()` |
| `platform_identity` | Brand phrases, circle/thread/seed language |
| `stance_templates` | 10+ variants each for acknowledge, redirect, momentum, closing |
| `data/language_pack_examples.json` | 100 modular examples (20 per tone), merged at lookup |

Regenerate examples: `python scripts/generate_language_pack.py`

Stance templates support `{feeling}`, `{micro_action}`, `{next_step}` — resolved before tone alignment.

---

## Evolving the model over time

| Stage | What to do |
|-------|------------|
| **Start small** | Ship with default `team_model.json` (current file) |
| **Week 1** | Add 2–3 `example_responses` from real team approvals |
| **Week 2** | Review `data/pattern_log.jsonl` for repeated escalations |
| **Month 1** | Promote best training examples; add `decision_patterns` |
| **Later** | Export JSON + logs for fine-tuning or RAG ingestion |

---

## Cursor integration

`.cursor/rules/team-micro-model.mdc` tells Cursor to:

- Read `team_model.json` before subjective output
- Use `team_model.py` helpers when building features
- Never invent team opinions
- Escalate when uncertain

---

## Safety defaults

- Blocked topics always redirect, never comply
- High-risk language triggers escalation
- No therapy, diagnosis, or harmful encouragement
- User autonomy and dignity preserved
- Adults 18+ only
