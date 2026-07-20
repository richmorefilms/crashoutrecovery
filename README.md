# Crashout Recovery

Standalone app for friendly, adult-appropriate redirects when impulses run hot.

**Adults 18+ only.**

## Quick start

```powershell
cd C:\crashoutRecovery
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Or double-click `run.ps1`.

Open http://127.0.0.1:8777

## Routes

| Route | Description |
|-------|-------------|
| `/` | Main app — tone switcher, modal, decision-flow |
| `/embed?tone=calm` | Minimal embeddable view (iframe-friendly) |
| `/crashout?tone=direct` | HTML fragment only |
| `/api/tones` | List valid tones |
| `/api/suggest` | POST `{ "text": "..." }` → full team-aligned suggestion + tone |
| `/api/compose` | POST `{ "spike_text": "..." }` → database-first rewrites, recovery actions, and risk check |
| `/api/save_seed` | Authenticated explicit submission to the private moderation queue |
| `/api/moderation/*` | Staff-only queue, approval, and rejection operations |
| `/api/valuation` | POST users, conversion, ARPU, and EV/sales multiple → 1/3/5-year projection |
| `/api/growth-valuation` | POST free launch users, conversion, retention, ARPU, and multiple → seeded growth projection |
| `/api/youtube/resolve` | Resolve `query` → youtubeId (auto cache / Data API). Optional `manual_id` + `refId` for Creator overrides |
| `/videos.json` | Crashout clip catalog + module maps |
| `/health` | Health check |
| `/team/model` | Team micro-model (JSON) |
| `/team/update` | Merge new opinions, topics, examples |
| `/team/check` | Align proposed AI response |
| `/team/block` | Enforce topic blocking |
| `/team/train` | Store training examples |
| `/team/promote` | Approve example into live model |
| `/team/topics` | View/modify topic rules |
| `/team/preview` | Preview alignment without saving |
| `/team/export` | Export fine-tune JSONL |

## Curated Composer

The Draft box queries staff-curated crashout episodes first. When reviewed
coverage is sparse, bounded suggestions from the team model fill the gap and
are labeled `AI-assisted`.

Saving in the browser remains immediate. A signed-in user can explicitly queue
the draft for private staff moderation. Approval redacts submitted text,
records an immutable audit event, and promotes only staff-edited commentary.

Set `CRASHOUT_INITIAL_STAFF_EMAIL` before that account registers (or restart
after setting it for an existing matching account) to bootstrap staff access.
Subscription tier does not grant moderation authority.

## Financial model

`conversion_rate` is supplied as a decimal fraction (`0.10` means 10%).

```powershell
$body = @{
  user_count = 50000
  conversion_rate = 0.10
  arpu = 120
  ev_sales_multiple = 1.8
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8777/api/valuation `
  -ContentType "application/json" -Body $body
```

For a free-account launch model, call `/api/growth-valuation`:

```powershell
$body = @{
  launch_users = 10000
  conversion_rate = 0.08
  retention_rate = 0.85
  arpu = 120
  ev_sales_multiple = 1.8
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8777/api/growth-valuation `
  -ContentType "application/json" -Body $body
```

## Team micro-model

Team opinions, tone, and topic rules live in `team_model.json` — not hardcoded in Python.

See **[TEAM_MODEL.md](TEAM_MODEL.md)** for full docs.

```bash
curl http://127.0.0.1:8777/team/model
curl -X POST http://127.0.0.1:8777/team/check -H "Content-Type: application/json" -d "{\"proposed_response\": \"Try one small step.\", \"context\": \"user overwhelmed\"}"
```

## Tones

`universal` · `calm` · `humorous` · `direct` · `strategic`

### Tone Priority Fix

Humorous now takes precedence over direct for social-reaction patterns (`hater`, `rant`, `meltdown`, `reply-to-everyone`).
Direct remains reserved for irreversible actions (delete everything, quit forever, burn it all down, reply-all disasters).

### Placeholder Resolution

`{feeling}` and other stance-template placeholders are resolved using `missing_context_rules` and will never leak into user-facing output.

## JavaScript

```javascript
showCrashout("calm");
showCrashout("direct", { mode: "modal" });
CrashoutDecisionFlow.suggestTone("I'm deleting everything");
```

## Project layout

```
crashoutRecovery/
  app/              # FastAPI app package
  team_model.json   # Team opinions, tone, topic rules (edit this)
  team_model.py     # Load, check, align, train helpers
  data/             # Pattern & training logs (expansion)
  templates/        # Jinja2 HTML fragments
  static/           # CSS + JS
  main.py           # Entry point
  TEAM_MODEL.md     # Micro-model documentation
```
