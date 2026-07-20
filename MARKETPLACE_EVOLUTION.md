# Crashout Recovery — Marketplace Evolution

> Superseded: the user-facing Marketplace and installable packs were removed.
> Curated episodes, rewrites, and recovery actions now feed the Composer
> directly through the database-first pipeline. This document is retained as
> historical product context only.

## Vision

The Marketplace should grow from demo add-ons into a library shaped by real staff judgment.

Staff-curated crashout episodes, commentary, rewrites, and recovery strategies are the primary source. Every pack should preserve a specific observation or useful point of view instead of repeating generic advice.

AI may fill temporary gaps while the library is small. It should extend staff-created seeds, never replace the staff voice. AI-assisted material stays clearly labeled until a staff-written entry replaces it.

## Categories

### 🎬 Episode Packs

Curated crashout stories with staff commentary.

Each entry should include:

- A concise episode or moment summary
- What made the situation escalate
- The unique lesson staff identified
- A safer turning point or recovery angle
- Relevant themes and tags

Episode Packs help people recognize patterns without celebrating the crashout.

### 🌱 Recovery Packs

Practical rewrites based on staff-approved recovery language.

Examples include:

- Calm version
- Clear rewrite
- Stable phrasing
- Draft-first response
- Morning-you rewrite

These packs should produce a real rewrite of the person's draft while preserving its meaning. The result should lower escalation, avoid diagnosis, and keep the writer's voice recognizable.

### 🧭 CTA Packs

Small action buttons tied to recovery strategies.

Examples include:

- Save this as a draft
- Wait ten minutes
- Remove the accusation
- Ask one clear question
- Test one reversible step
- Start a private note

Each action should explain what it does and why it is safer.

## Database Schema

The `crashout_packs` collection stores the shared Marketplace library.

| Field | Purpose |
|---|---|
| `id` | Stable unique identifier for the pack |
| `category` | `episode`, `recovery`, or `cta` |
| `title` | Short staff-facing and user-facing pack name |
| `description` | Plain-language explanation of the pack's value |
| `curated_content` | Staff-written episodes, commentary, rewrites, or actions |
| `ai_generated_content` | Temporary gap-filling entries with clear AI-assisted labels |
| `tags` | Themes used for discovery, matching, and duplicate review |

Each content entry should also carry its source, author type, review status, and creation date. This makes staff work distinguishable from AI-assisted material and supports later replacement.

### Staff curation

Staff can add episodes, commentary, rewrites, and recovery actions directly.

Before publishing, staff should:

1. Identify the story's distinct lesson.
2. Compare it with existing entries that share similar themes.
3. Remove repeated or generic phrasing.
4. Keep the strongest original observation.
5. Confirm that the entry supports reflection or recovery.
6. Mark the content reviewed and ready.

Two stories may cover the same theme when their lessons are genuinely different. Rewording an existing idea is not enough to justify a duplicate.

## AI Augmentation Rules

### Fill gaps, do not replace staff voice

AI augmentation runs only when a matching pack lacks enough reviewed staff content.

It may:

- Turn a staff seed into calm, clear, or stable variations
- Suggest a small set of safe moves
- Adapt an approved rewrite to a closely related situation
- Fill an uncovered tone or edge case

It may not:

- Invent staff commentary or present AI output as staff-authored
- overwrite reviewed staff content
- mass-produce near-duplicate packs
- add unsupported facts to an episode
- intensify conflict, diagnose a person, or imitate a real individual

### Sparse-content threshold

Each category should have a minimum reviewed-content target. AI may fill only the difference between the current reviewed count and that target.

For example:

- Enough staff entries: use staff content only
- A small gap: generate only the missing variations
- No relevant staff seed: do not generate a pack automatically; send the gap to staff review

### Labels and replacement

Every generated entry displays **AI-assisted** in its preview and result.

AI-assisted entries remain separate from curated entries. When staff publishes a suitable replacement, the staff entry takes priority and the generated entry is retired.

### Quality checks

Before an AI-assisted entry appears:

1. Compare it with existing content for repeated meaning.
2. Confirm that it stays grounded in a staff-approved seed.
3. Check that it preserves the draft's intent.
4. Reject shaming, escalation, diagnosis, or unsafe advice.
5. Keep the wording short and actionable.

## User Flow

1. Open **Market**.
2. Browse Episode, Recovery, and CTA Packs.
3. Tap a pack to preview its curated entries and staff commentary.
4. Clearly see which entries are staff-curated and which are **AI-assisted**.
5. Install the pack.
6. Open **Compose**.
7. See the installed pack's real rewrites, templates, or recovery actions.
8. Choose a Recovery Pack option to rewrite the current draft through `/api/rewrite`.
9. Review the rewrite before applying it. The original draft remains available.

### Composer behavior

- Episode Pack chips open a relevant example and staff takeaway.
- Recovery Pack pills request a real rewrite using the selected staff-approved style.
- CTA Pack buttons apply or explain a specific recovery strategy.
- Curated content is preferred whenever it matches the situation.
- AI-assisted content appears only when curated options do not cover the need.
- Nothing posts automatically.

### Rewrite expectations

The rewrite service receives the draft, selected pack, and requested style. It returns:

- The rewritten draft
- A short explanation of the change
- Whether the result is staff-curated or AI-assisted
- The pack and content entry that guided it

Users should be able to keep the original, accept the rewrite, or edit either version.

## Growth Path

### Stage 1 — Seed the library

- Staff publishes a small set of strong Episode, Recovery, and CTA Packs.
- AI fills only missing rewrite styles and closely related safe-move phrases.
- Every generated entry is labeled and queued for staff review.

### Stage 2 — Learn from gaps

- Track which themes have no useful curated match.
- Ask staff to fill frequently requested gaps first.
- Replace high-use AI-assisted entries with reviewed staff versions.
- Merge or retire generic and overlapping content.

### Stage 3 — Curated by default

- Most requests resolve to reviewed staff content.
- AI use declines automatically as category coverage grows.
- New AI-assisted content is limited to uncommon edge cases.
- Staff voice and editorial quality define the Marketplace.

### Long-term principle

The Marketplace is a staff-curated recovery library with selective AI assistance—not an AI content feed.

Success means the database becomes more distinctive and useful over time while the need for generated filler steadily decreases.
