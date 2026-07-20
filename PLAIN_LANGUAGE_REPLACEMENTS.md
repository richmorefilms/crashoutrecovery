# Plain-language UI copy — replacement patch set (review before commit)

Source of truth: `PLAIN_OPS.md`  
Technical docs left alone: `OPERATIONS.md`, `/ops-full.md`

## Dictionary applied

| Insider term | Plain term |
|--------------|------------|
| pulse strip | signal bar |
| composer / Compose | draft box / Draft |
| seed / post seed | draft idea |
| tone pills | tone buttons |
| Momentum CTA / momentum move | suggested next step |
| recovery streak | win streak |
| Momentum score | progress meter |
| Bad Decision Predictor | risk check |
| Signals Pro / World Signals Pro | world trends |
| Marketplace packs | add-on tools |
| premium tiers | unlock levels |
| Global Spike Alert | world flash |
| CTA: (tone fragment labels) | Next step: |
| Momentum: (tone callouts) | Next step: |

## Patch set (user-facing only)

### Core app chrome & panels (`templates/index.html`)
- Signal bar title → World trends; aria → World trends signal bar
- FAB → Draft / Open draft box
- Progress meter, Win streak, Saved draft ideas
- World trends lock copy; Add-on tools Market panel
- Action packs / Draft templates section titles
- Suggested next step / Risk check aria-labels
- Upgrade modal unlock-level copy
- Help / Ops sections rewritten to plain terms
- Unlock Pro CTA → Unlock Pro button (help)

### Printable plain guide
- `PLAIN_OPS.md` — full guide in plain language
- `templates/ops_manual.html` — mirrors PLAIN_OPS (`/ops`, `/ops.md`)

### Draft box (`static/crashout-social.js`)
- Suggested next step header & badge
- Draft idea / Draft preview / Save draft idea
- Status toasts: draft idea saved / edit your draft idea
- Tone verbs: strategic/universal → draft (preview lines)

### Risk check (`static/bad-decision-predictor.js`)
- Kicker & badge → Risk check
- Open draft box; Unlock risk check
- Safe move applied to your draft preview

### Monetization UI (`static/monetization.js`)
- Feature labels: Risk check, Add-on tools, World trends, Win streak …
- Tier preview bullets plain
- Upsells / teasers → Risk check
- Unlock world trends / Unlock Advanced actions
- Sponsored author → @drafttools

### Feed (`static/feed-tabbed.js`)
- CTAs & categories use Draft idea
- Lane meta: world trends, add-on tools, win streak
- Creator display name Spike to Draft
- Empty/sort: spikes become draft ideas

### Legacy feed / app (`static/feed-dual-lane.js`, `static/app.js`)
- Same seed → draft idea string updates
- Status messages / micro-actions plain

### Market (`static/marketplace.js`)
- Draft Template Pack; Progress Action Pack
- Draft Tools sponsor; Steady draft item
- Draft templates label in draft box

### World trends data (`static/world-signals.js`)
- headlines/summaries / algo tip use draft idea

### Streak / progress / creator
- `recovery-streak.js` — win streak toasts
- `momentum-score.js` — Your progress is …
- `creator-dashboard.js` — Draft idea saved — unlock to read

### Tone support fragments (`templates/crashout*.html`)
- **CTA:** → **Next step:**
- **Momentum:** → **Next step:**
- Momentum without damage → Progress without damage

## Intentionally unchanged (internal)

| Kind | Examples |
|------|----------|
| localStorage keys | `crashout_seeds`, `crashout_recovery`, `crashout_market_packs`, `crashout_world_signals` |
| JS APIs | `CrashoutComposerModal`, `CrashoutPredictor`, `CrashoutMomentumScore`, `CrashoutMarketplace` |
| HTML/CSS ids & classes | `composer-modal`, `seed-preview`, `pulse-alert`, `bad-decision-predictor` |
| Feature ids | `seed_optimizer`, `seed_post`, `marketplace_packs`, `predictor` |
| Developer docs | `OPERATIONS.md`, `/ops-full.md` |
| Help Console code samples | Shows real API names (for testing) |

## Review checklist

1. Hard-refresh app → FAB says **Draft**
2. Signal bar says **World trends**
3. Run draft flow → Suggested next step / Save draft idea / Risk check
4. Creator → Progress meter + Win streak
5. Market → Add-on tools / Action packs / Draft templates
6. Open `/ops` → matches PLAIN_OPS wording
7. Confirm `OPERATIONS.md` still technical

When ready: approve this patch set, then ask to commit.
