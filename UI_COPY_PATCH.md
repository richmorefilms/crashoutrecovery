# UI_COPY wiring — patch review (do not commit until approved)

Source of truth: [`UI_COPY.json`](UI_COPY.json)  
Loader: [`app/ui_copy.py`](app/ui_copy.py) · Client: [`static/ui-copy.js`](static/ui-copy.js) · Route: `GET /UI_COPY.json`

**Unchanged (by design):** `OPERATIONS.md`, `/ops-full.md`, JS APIs, CSS/HTML ids, localStorage keys (`crashout_*`).

## Dictionary keys → plain labels

| Key | Label |
|-----|--------|
| `pulse_strip` | Signal bar |
| `composer` | Draft box |
| `seed` | Draft idea |
| `tone_pills` | Tone buttons |
| `momentum_cta` | Suggested next step |
| `recovery_streak` | Win streak |
| `momentum_score` | Progress meter |
| `bad_decision_predictor` | Risk check |
| `signals_pro` | World trends |
| `marketplace_packs` | Add-on tools |
| `premium_tiers` | Unlock levels |
| `global_spike_alert` | World flash |

## Infrastructure (already present / confirmed)

| File | Change |
|------|--------|
| `UI_COPY.json` | Full label + tooltip dictionary |
| `app/ui_copy.py` | `load_ui_copy`, `ui_label`, `ui_tooltip`, `ui_copy_context` |
| `app/config.py` | `UI_COPY_PATH` |
| `app/__init__.py` | Injects `ui_copy` into `/` + `/ops`; serves `/UI_COPY.json` |
| `static/ui-copy.js` | `CrashoutUICopy.label` / `.tooltip` / `.labelLower` / `.applyDom` |

## Template replacements → `ui_copy` / `uc.*`

### `templates/index.html`
| Surface | Pattern |
|---------|---------|
| Signal bar | `uc.signals_pro` / `uc.pulse_strip` title + tooltip |
| Creator dashboard | `uc.momentum_score`, `uc.recovery_streak`, `uc.seed` |
| World trends / Market panels | `uc.signals_pro`, `uc.marketplace_packs` |
| Draft FAB + modal | `uc.composer`, `uc.seed`, `uc.momentum_cta`, `uc.tone_pills`, `uc.bad_decision_predictor` |
| Upgrade modal | Tier copy references `uc.composer`, `uc.signals_pro`, `uc.bad_decision_predictor` |
| Help nav | Buttons bind labels/tooltips to dictionary keys |
| Help prose (Overview…Alerts) | Headings + body use `{{ uc.*.label }}` / `| lower` for all 12 terms |
| Embedded JSON | `#ui-copy-data` + `/static/ui-copy.js` before app scripts |

### `templates/ops_manual.html` (`/ops`)
| Surface | Pattern |
|---------|---------|
| TOC + section H2s | Labels from `uc.*` |
| Tooltips in prose | `uc.*.tooltip` for pulse, streak, score, risk, signals, market, tiers, flash |
| Tier / recipe tables | Composer, seed, risk check, world trends, etc. from dictionary |

**Not edited:** `PLAIN_OPS.md` (download markdown remains static plain text; still matches labels), `OPERATIONS.md`.

## JS replacements → `CrashoutUICopy.label(...)`

| File | What now reads the dictionary |
|------|-------------------------------|
| `static/crashout-social.js` | Suggested next step title, draft idea meta/badge/preview, save toasts |
| `static/bad-decision-predictor.js` | Risk check kicker/badge, open draft box CTA, unlock string |
| `static/monetization.js` | Feature map, tier preview bullets, predictor teaser/upsell, sponsored signals blurb |
| `static/feed-tabbed.js` | Lane intros, FEED CTA for seed, post category “Draft idea”, market/signals desc |
| `static/app.js` | Draft idea status lines / micro-actions |
| `static/creator-dashboard.js` | Locked seed list blur text |
| `static/recovery-streak.js` | Win streak toasts + Your Week notes |

**Intentionally left as developer identifiers:** `CrashoutMomentumScore`, `composer-modal`, `seed-preview`, pack `id`s, tier `id`s (`basic`/`plus`/`creator`/`pro`).

## How to verify (before commit)

1. Restart `python main.py`
2. Open `/` — signal bar + Draft FAB tooltips match `UI_COPY.json`
3. Open Help → section names match plain labels
4. Open `/ops` — TOC/headings pull from same dictionary
5. Run draft flow — next-step card + risk check + save toast use dictionary labels
6. Edit a label in `UI_COPY.json`, restart, confirm Templates + Help move with it (JS modules pick up via `#ui-copy-data` on reload)

## Commit-time enforcement

Run before every commit (report only — never auto-replaces):

```bash
python scripts/check_ui_copy.py --working
```

- Cursor hook: `.cursor/hooks.json` → asks for confirmation on `git commit` when findings exist
- Agent rule: `.cursor/rules/ui-copy.mdc`
- Optional strict CI: `python scripts/check_ui_copy.py --working --strict`
