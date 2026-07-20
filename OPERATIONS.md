# Crashout Recovery — Operations Instruction Manual

Adults 18+ only. Account-enabled UI preview — no real billing.

**Run locally:** `python main.py` → [http://127.0.0.1:8777](http://127.0.0.1:8777)

**In-app Help / Ops panel:** tap **Help / Ops** in the app header (also `/#ops` or `/#help`).

The panel covers **Overview**, **Modes**, **Composer**, **Streak**, **Premium**, **Alerts**, **How-to**, and **Console**.

**Printable / downloadable (plain language):**

- HTML print page: [http://127.0.0.1:8777/ops](http://127.0.0.1:8777/ops) (or `/manual`) — use **Print / Save PDF**
- Markdown download: [http://127.0.0.1:8777/ops.md](http://127.0.0.1:8777/ops.md) → `PLAIN_OPS.md`
- Technical full guide: [http://127.0.0.1:8777/ops-full.md](http://127.0.0.1:8777/ops-full.md) → `OPERATIONS.md`

---

## Quick map: what do you want to do?

| Goal | Go here | Notes |
|------|---------|--------|
| Browse drama / meltdowns | **Drama** tab | Learn from others' mistakes |
| Watch or manage YouTube clips | **Moments** tab | Shared catalog; Add Video / Set ID = Creator+ |
| Read culture context | **Headlines** tab | Pop-culture / platform news |
| See global spikes | **Signals** tab | Today free; Pro = forecast + burnout + tip |
| Your circle + “Your Week” | **Posts** tab | Streak card + community seeds |
| Compare safer wording | **Compose** | Curated rewrites first; labeled assistance fills gaps |
| Check streak / seeds / score | **Creator** tab | Dashboard; Momentum always visible |
| Turn a spike into a seed | **Compose** FAB | Tone → CTA → Predictor |
| Preview premium tiers | Upgrade modal | Login required; preview tier syncs to the account |
| React to a high world spike | Pulse strip (any lane) | High chip flashes + jumps to Signals |

---

## 1. Feed lanes (tabs)

Horizontal tab bar. One panel at a time (`hidden` panels).

| Option | Lane | What it shows | Primary action |
|--------|------|---------------|----------------|
| A | **Drama** | Meltdown / beef / bad-decision story cards | Open CTA → Compose |
| B | **Moments** | Shared `/videos.json` YouTube thumbnail grid | Play/Search; Creator+ Add Video / Set ID |
| C | **Headlines** | News / culture cards | Open CTA → Compose |
| D | **Signals** | World Signals Pro panel | Read today; unlock Pro for deep layers |
| E | **Posts** | Circle posts + predictor summary + **Your Week** | Compose / review streak |
| F | **Creator** | Dashboard: momentum, streak, tones, spikes, seeds | Review recovery ops |

**How to switch**

- Tap a tab, or in console:  
  `CrashoutTabbedFeed.switchLane('drama' | 'moments' | 'headlines' | 'signals' | 'posts' | 'creator')`

### Moments catalog operations

- Tap a resolved thumbnail to open the privacy-enhanced YouTube player; unresolved clips fall back to YouTube search.
- Creator+ can open **Add Video** with a required query and optional 11-character YouTube ID or supported YouTube URL.
- **Set ID** selects an existing catalog clip for update.
- Manual IDs work without a YouTube API key. Query-only lookup needs `CRASHOUT_YOUTUBE_API_KEY` unless cached.
- Saves mutate the shared server `videos.json`, refetch it with browser caching disabled, and rerender Moments for all users. There is no delete control.
- The client-side Creator check is not server authorization: `/api/youtube/*` is currently public.

---

## 2. World Signals pulse strip

Always visible above the tabs on every lane.

| Option | Action | Result |
|--------|--------|--------|
| A | Tap any pulse chip | Jump to **Signals**; highlight matching row |
| B | Tap a **high** pulse chip | Same + Global Spike Alert row flash (`.signal-row-alert`) |
| C | Watch for red flash | High spikes auto-flash chips + strip (`.pulse-alert` / `.pulse-alert-global`) |
| D | Tap premium lock chip (if shown) | Opens upgrade toward Pro |

**Ops tip:** Flash is visual only — not gated. Basic users still get flash + lane jump. Pro users also flash relevant forecast rows.

---

## 3. Composer operations (main loop)

Open with the **+ Compose** FAB.

| Step | Option / action | What happens |
|------|-----------------|--------------|
| 1 | Type the raw thought | Local tone preview; after ~850 ms idle, the full server request runs automatically |
| 2 | **Read tone & suggest a move** | Run the full pipeline immediately: tone → momentum CTA → predictor |
| 3 | Compare rewrite choices | Curated calm, clear, and stable wording appears first |
| 4 | Use CTA actions | Post / thread / **Save seed** / drama / moments |
| 5 | Review recovery actions | Contextual CTAs come from curated entries or labeled assistance |
| 6 | Take / copy **safe move** | Predictor (Creator+); bumps recovery streak |
| 7 | **Done** | Closes composer; Posts remains active |

**Pipeline (always this order)**

```
Spike text → Tone read → Momentum CTA (seed preview) → Bad Decision Predictor
```

**Save seed** writes to browser cache key `crashout_seeds`, bumps recovery streak, and syncs when logged in. Full suggestions send the entered text to `/api/suggest`; server-side pattern/training logs may retain previews or successful inputs.

---

## 4. Recovery streak & “Your Week”

| Option | Where | What it tracks |
|--------|-------|----------------|
| A | Posts → **Your Week** card | Streak days, spike history bars, tone trend slot |
| B | Creator dashboard | Same data, denser view |
| C | After **Save seed** | Win / streak bump |
| D | After **Take safe move** | Win + `lastSafeMove` stored |

**Storage:** `crashout_recovery`  
Fields: `streak`, `history`, `tones`, `wins`, `lastSafeMove`, `lastSafeAt`

**Tier note:** Full spike graph / tone trend depth is Pro-oriented; basic still sees core streak framing.

---

## 5. Bad Decision Predictor

| Option | Requirement | Action |
|--------|-------------|--------|
| A | Basic | See locked preview / teaser; CTA to Unlock Creator Mode |
| B | Creator+ | Full spike level, risk vs safe move, reason |
| C | Creator+ | **Take safe move** → applies to seed preview + streak |
| D | Creator+ | **Copy safe move** |
| E | Posts lane | Summary card after a recent analysis |

**Console test:** `CrashoutMonetization.setTier('creator')`

---

## 6. Creator Mode dashboard

| Option / block | Meaning | Gated? |
|----------------|---------|--------|
| **Momentum score** | 0–100 live habit score | Always visible |
| Recovery streak | Days + win count | Body dimmed until Creator+ |
| Tone trend | Last 7 tone dots | Creator+ to read clearly |
| Spike history | Last 7 bars | Creator+ |
| Saved seeds | List from `crashout_seeds` | Creator+ |
| Last safe move | Last predictor safe move | Creator+ |

**Unlock:** Upgrade CTA or `CrashoutMonetization.setTier('creator')`

---

## 7. Momentum Score (how the number is built)

Displayed on Creator tab. Not gated as a card; score can change with Pro bonus.

| Signal | Points |
|--------|--------|
| Recovery streak | +4 per day (max 40) |
| Safe move taken (`lastSafeMove`) | +20 |
| Seeds saved | +2 each (max 20) |
| Spike history | low +2, rising −1, hot −3 |
| Pro + calm signal day (no `high` pulse) | +10 |
| Clamp | 0–100 |

| Level | Range | Meaning |
|-------|-------|---------|
| low | 0–39 | Rebuild with one safe move / seed |
| medium | 40–69 | Building — stay consistent |
| high | 70–100 | Habits stabilizing |

**Console:** `CrashoutMomentumScore.compute()` / `.describe(n)` / `.render()`

---

## 8. World Signals Pro panel

| Option | Audience | Content |
|--------|----------|---------|
| A | Everyone | Today's signals list |
| B | Pro | 72h forecast |
| C | Pro | Burnout clusters |
| D | Pro | Algorithm dip recovery tip |
| E | Non-Pro | Locked upsell → Unlock Pro |

**Storage:** `crashout_world_signals`  
**Console:** `CrashoutMonetization.setTier('pro')`

---

## 9. Curated Composer pipeline

`POST /api/compose` is read-only. It queries reviewed crashout episodes and
returns structured rewrite choices, recovery actions, and server-authoritative
risk logic. Curated content is preferred; gap-filled output is labeled
`AI-assisted`.

`POST /api/save_seed` requires authentication and a short-lived signed compose
receipt. The receipt binds provenance to the exact submitted text, so clients
cannot set `ai_generated`.

Staff-only moderation routes:

- `GET /api/moderation/queue`
- `POST /api/moderation/approve/{queue_id}`
- `POST /api/moderation/reject/{queue_id}`

Approval and rejection redact user-derived text atomically and append an
immutable, non-sensitive audit event. Only staff-edited commentary is promoted.

---

## 10. Monetization tiers (scaffolding only)

| Tier | Price label | Main unlocks |
|------|-------------|--------------|
| **basic** | Free | Feed, composer core, pulse, rewrite choices, Signals today |
| **plus** | $4.99/mo | Reserved deeper tone / CTA coaching feature flags; no separate Plus flow yet |
| **creator** | $9.99/mo | Predictor, Creator dashboard depth, Moments Add Video |
| **pro** | $14.99/mo | Signals Pro, full streak graphs, momentum +10 calm-day bonus |

**UI:** Upgrade modal from any Unlock button.

**Dev / ops testing (browser console):**

```js
CrashoutMonetization.getTier()
CrashoutMonetization.setTier('basic')
CrashoutMonetization.setTier('plus')
CrashoutMonetization.setTier('creator')
CrashoutMonetization.setTier('pro')
CrashoutMonetization.openUpgrade('creator')
```

No payment processing is wired. Tier preview changes require login, are pushed to SQLite, and are restored on later login.

---

## 11. Global Spike Alert operations

| Option | Trigger | Result |
|--------|---------|--------|
| A | App load / lane switch / tier change / signals refresh | `CrashoutSpikeAlert.check()` |
| B | Any signal today is “high” | Strip + high chips flash 1.5s |
| C | No high signals | Flash cleared |
| D | Tap high chip | Jump to Signals + highlight + row flash |
| E | Pro + jump | Extra forecast-row flash |

**Console:**

```js
CrashoutSpikeAlert.check()
CrashoutSpikeAlert.jumpToSignals('ws3')
CrashoutSpikeAlert.clearFlash()
```

---

## 12. Browser cache, account sync, and reset

Guest state is local-first. Registration uploads existing guest data before pulling the new account; login to an existing account pulls server records and replaces the four browser content caches. Access JWTs default to 20 minutes, refresh tokens to 14 days, and a 401 triggers one refresh rotation/retry. Logout revokes/clears session tokens but leaves content caches in the browser.

| Key | Module | Purpose |
|-----|--------|---------|
| `crashout_recovery` | Recovery streak | Streak, spikes, tones, wins, last safe move |
| `crashout_seeds` | Composer / Creator | Saved post seeds |
| `crashout_market_packs` | Legacy compatibility | Retained temporarily for old account payloads; no current UI |
| `crashout_world_signals` | Signals Pro + Spike Alert | Forecast / burnout / tip / today |
| `crashout_jwt` / `crashout_refresh` / `crashout_user` | Auth | Access token, refresh token, cached identity |

The four content caches synchronize through `/api/user/data` to structured SQLite account records.

**Reset browser content caches:**

```js
localStorage.removeItem('crashout_recovery')
localStorage.removeItem('crashout_seeds')
localStorage.removeItem('crashout_market_packs')
localStorage.removeItem('crashout_world_signals')
location.reload()
```

Log out first for a guest-only reset. If still logged in, account data may sync back after reload. This does not erase authentication keys, account records, `videos.json`, SQLite YouTube cache rows, pattern logs, or training logs. There is currently no supported account-data deletion endpoint.

---

## 13. Recommended operator walkthrough (first 10 minutes)

Use this sequence to learn the full loop:

1. **Drama** — open a card CTA → Compose opens  
2. Type a spike → wait for automatic analysis or press **Read tone** → see CTA + predictor  
3. Sign in → `setTier('creator')` → Take **safe move** + **Save seed**  
4. **Posts** — check **Your Week**  
5. Compose again — compare curated and labeled assisted rewrites  
6. **Creator** — read Momentum score + dashboard  
7. **Moments** → play a clip → use **Add Video** with a query + optional YouTube ID  
8. Tap a flashing high pulse → **Signals**  
9. `setTier('pro')` → open forecast / burnout / tip  
10. Optional: log out, then reset browser content caches for a guest-only clean pass  

---

## 14. Module → API cheat sheet

| Module | Global | Main methods |
|--------|--------|--------------|
| Feed | `CrashoutTabbedFeed` | `switchLane`, `render`, `openCreatorDashboard` |
| Composer | `CrashoutComposerModal` | `open`, `close` |
| Monetization | `CrashoutMonetization` | `getTier`, `setTier`, `openUpgrade`, `isFeatureUnlocked` |
| World Signals | `CrashoutWorldSignals` | `renderStrip`, `renderProPanel`, `focusSignal` |
| Spike Alert | `CrashoutSpikeAlert` | `check`, `jumpToSignals`, `applyFlash`, `clearFlash` |
| Predictor | `CrashoutPredictor` | `updateFromServer`, `refresh` |
| Streak | `CrashoutRecoveryStreak` | `load`, `bumpStreak`, `recordWin`, `setLastSafeMove` |
| Momentum | `CrashoutMomentumScore` | `compute`, `describe`, `render` |
| Creator | `CrashoutCreatorDashboard` | `render`, `show`, `hide` |
| Videos | `CrashoutVideos` | `openAddVideoModal`, `allClips`, `resolveClip`, `resolveQuery`, `refreshCatalog` |
| Auth | `CrashoutAuth` | `openModal`, `isLoggedIn`, `user`, `login`, `logout` |
| User sync | `CrashoutUserStore` | `push`, `pull`, `get`, `set` |

### HTTP API: YouTube resolve

`GET` and `POST /api/youtube/resolve` accept:

- `query` (or legacy `searchQuery`)
- optional `manual_id` (11-character ID or supported watch/embed/shorts/youtu.be URL)
- optional `refId`
- optional `persist`

Responses include `youtubeId`, `title`, `channel`, `duration`, `thumbnail`, `source`, and optional `refId`. Manual resolution always persists. Automatic search requires `CRASHOUT_YOUTUBE_API_KEY` unless the normalized query exists in SQLite `video_cache`.

### `videos.json` catalog contract

- Root: `{ "clips": { ... }, "modules": { ... } }`
- Clip fields: `refId`, `youtubeId`, `source`, `title`, `channel`, `thumbnail`, `searchQuery`, optional `duration`, and `tags`
- Module arrays: `momentum`, `spike_alert`, `risk_check`, `console_recipes`
- New clips default to `manual_<youtubeId>`, tags `["manual", "moments"]`, and are inserted at the front of `modules.momentum`

---

## 15. What this is / isn’t

| Is | Isn’t |
|----|-------|
| Local-first creator recovery UI with account sync | Live payments / IAP |
| Server-assisted tone → CTA → safe-move coaching | Therapy / diagnosis |
| Lane-native feed + shared YouTube catalog | Production social feed |
| JWT auth and SQLite persistence | Production billing |

---

## Need a faster decision?

| If you care about… | Start with section |
|--------------------|--------------------|
| Day-to-day user ops | §§1–3, §13 |
| Premium / unlock testing | §§5–10 |
| Retention / alerts | §§4, 7, 11 |
| Storage / reset / debugging | §§12, 14 |
