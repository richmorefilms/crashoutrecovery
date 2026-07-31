/**
 * Bad Decision Predictor — compact composer panel tied to tone + CTA engines.
 * UI-only; Creator Mode+ unlock via CrashoutMonetization.
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiLower = (key, fallback) => window.CrashoutUICopy?.labelLower?.(key) || fallback;

  const SPIKE_LEVELS = [
    { id: "low", label: "Low", min: 0 },
    { id: "steady", label: "Steady", min: 2 },
    { id: "rising", label: "Rising", min: 4 },
    { id: "hot", label: "Hot", min: 6 },
  ];

  const TONE_SPIKE_BIAS = {
    direct: 2,
    humorous: 1,
    strategic: 0,
    calm: -1,
    universal: 0,
  };

  const TONE_REASON_FRAGMENTS = {
    direct: "urgency + collapse language",
    humorous: "vent energy + public heat",
    strategic: "platform frustration + metric spike",
    calm: "overload + emotional stacking",
    universal: "mixed spike signals",
  };

  const TONE_DEFAULT_RISK = {
    direct: "Irreversible public move",
    humorous: "Public rant spiral",
    strategic: "Reactive strategy pivot",
    calm: "Shutdown or disappear",
    universal: "Post while heated",
  };

  const TONE_DEFAULT_SAFE = {
    direct: "Draft the tiny version",
    humorous: "Drop a spark, not the meltdown",
    strategic: "Test one variable first",
    calm: "Pause — draft one line",
    universal: `Save ${uiLower("seed", "draft idea")}, post later`,
  };

  const RISK_PATTERNS = [
    { pattern: /\b(delet(e|ing|ed)|nuke|wipe|destroy)\w*\b.*\b(all|everything|account|project)\b/i, move: "Delete everything" },
    { pattern: /\b(quit|quitting|walk away|done forever|never again)\b/i, move: "Quit publicly" },
    { pattern: /\b(burn it all down|burn everything|scorched earth)\b/i, move: "Burn it all down" },
    { pattern: /\b(reply(ing)? to (every|all)|reply-all|reply all|every hater)\b/i, move: "Reply-all war" },
    { pattern: /\b(post(ing)? (it )?raw|say (it )?all|tell (them )?off)\b/i, move: "Post the raw spike" },
    { pattern: /\b(block everyone|delete (my )?account|deactivate)\b/i, move: "Nuke your presence" },
    { pattern: /\b(irreversible|can't undo|no turning back)\b/i, move: "Irreversible move" },
  ];

  const SPIKE_SIGNALS = [
    { pattern: /\b(forever|never again|can't undo|irreversible)\b/i, weight: 2 },
    { pattern: /\b(everyone|everything|all of it|whole account)\b/i, weight: 2 },
    { pattern: /\b(hate|furious|rage|meltdown|crash out)\b/i, weight: 1 },
    { pattern: /\b(right now|immediately|this second)\b/i, weight: 1 },
    { pattern: /\b(overwhelmed|panicking|spiraling|can't breathe)\b/i, weight: 1 },
  ];

  let lastAnalysis = null;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function truncate(text, max) {
    const t = (text || "").trim();
    if (t.length <= max) return t;
    return `${t.slice(0, max - 1).trim()}…`;
  }

  function firstSentence(text) {
    const t = (text || "").trim();
    const match = t.match(/^[^.!?]+[.!?]?/);
    return match ? match[0].trim() : t;
  }

  function isUnlocked() {
    return window.CrashoutMonetization?.isFeatureUnlocked?.("predictor") === true;
  }

  function scoreSpike(rawText, tone, localMatch) {
    let score = 1;
    const text = rawText || "";

    SPIKE_SIGNALS.forEach(({ pattern, weight }) => {
      if (pattern.test(text)) score += weight;
    });

    RISK_PATTERNS.forEach(({ pattern }) => {
      if (pattern.test(text)) score += 2;
    });

    score += TONE_SPIKE_BIAS[tone] ?? 0;
    if (localMatch?.matched) score += 1;

    return Math.max(0, Math.min(8, score));
  }

  function spikeLevelFromScore(score) {
    let level = SPIKE_LEVELS[0];
    for (const entry of SPIKE_LEVELS) {
      if (score >= entry.min) level = entry;
    }
    return level;
  }

  function detectRiskMove(rawText, tone) {
    for (const { pattern, move } of RISK_PATTERNS) {
      if (pattern.test(rawText || "")) return move;
    }
    return TONE_DEFAULT_RISK[tone] || TONE_DEFAULT_RISK.universal;
  }

  function detectSafeMove(rawText, tone, ctaPayload) {
    const hook =
      ctaPayload?.suggestion ||
      ctaPayload?.aligned ||
      ctaPayload?.redirect ||
      "";

    if (hook) {
      const line = firstSentence(hook);
      if (line.length > 8) return truncate(line, 72);
    }

    return TONE_DEFAULT_SAFE[tone] || TONE_DEFAULT_SAFE.universal;
  }

  function buildReason(tone, localMatch, riskMove) {
    const toneFrag = TONE_REASON_FRAGMENTS[tone] || TONE_REASON_FRAGMENTS.universal;
    if (localMatch?.matched) {
      return `Tone shows ${toneFrag}`;
    }
    if (riskMove && riskMove !== TONE_DEFAULT_RISK[tone]) {
      return `Input signals ${toneFrag} + impulse toward "${riskMove.toLowerCase()}"`;
    }
    return `Tone shows ${toneFrag} — draft before you post`;
  }

  function analyze({ rawText, tone, ctaPayload, localMatch }) {
    const resolvedTone = tone || "universal";
    const score = scoreSpike(rawText, resolvedTone, localMatch);
    const spike = spikeLevelFromScore(score);
    const riskMove = detectRiskMove(rawText, resolvedTone);
    const safeMove = detectSafeMove(rawText, resolvedTone, ctaPayload);
    const reason = buildReason(resolvedTone, localMatch, riskMove);

    return {
      score,
      spikeLevel: spike.id,
      spikeLabel: spike.label,
      riskMove,
      safeMove,
      reason,
      tone: resolvedTone,
      unlocked: isUnlocked(),
      analyzedAt: new Date().toISOString(),
    };
  }

  function spikeMeterHtml(score, levelId) {
    const pct = Math.round((score / 8) * 100);
    return `
      <div class="predictor-spike-meter" role="meter" aria-valuenow="${score}" aria-valuemin="0" aria-valuemax="8" aria-label="Spike level ${pct} percent">
        <div class="predictor-spike-track">
          <div class="predictor-spike-fill predictor-spike-fill--${levelId}" style="width:${pct}%"></div>
        </div>
      </div>`;
  }

  function renderPanel(analysis, options = {}) {
    const { emit = true } = options;
    const el = document.getElementById("bad-decision-predictor");
    if (!el) return;

    if (!analysis) {
      el.hidden = true;
      el.classList.remove("predictor-panel--visible", "predictor-panel--locked");
      el.innerHTML = "";
      lastAnalysis = null;
      window.dispatchEvent(new CustomEvent("crashout:predictor-cleared"));
      return;
    }

    lastAnalysis = analysis;
    const locked = !analysis.unlocked;

    el.hidden = false;
    el.classList.add("predictor-panel--visible");
    el.classList.toggle("predictor-panel--locked", locked);

    const tierBadge = locked
      ? `<span class="predictor-tier-badge predictor-tier-badge--locked">Creator Mode</span>`
      : `<span class="predictor-tier-badge">Creator Mode</span>`;

    const riskContent = locked
      ? `<span class="predictor-locked-value" aria-hidden="true">████████████</span>`
      : escapeHtml(analysis.riskMove);

    const safeContent = locked
      ? `<span class="predictor-locked-value" aria-hidden="true">████████████</span>`
      : escapeHtml(analysis.safeMove);

    const reasonContent = locked
      ? "Unlock to see why your spike is trending this way."
      : escapeHtml(analysis.reason);

    const actions = locked
      ? `<button type="button" class="predictor-action predictor-action--upgrade" data-monetization-action="upgrade" data-tier="creator">Unlock Creator Mode</button>`
      : `<button type="button" class="predictor-action predictor-action--safe" data-predictor-action="apply-safe">Take safe move</button>
         <button type="button" class="predictor-action" data-predictor-action="copy-safe">Copy safe move</button>`;

    el.innerHTML = `
      <article class="predictor-panel-inner unified-card neon-card" data-tone="${analysis.tone}" data-spike="${analysis.spikeLevel}">
        <header class="predictor-header">
          <div class="predictor-header-text">
            <p class="predictor-kicker">${escapeHtml(uiLabel("bad_decision_predictor", "Risk check"))}</p>
            ${tierBadge}
          </div>
          <div class="predictor-spike-readout">
            <span class="predictor-spike-label">Spike level</span>
            <strong class="predictor-spike-value predictor-spike-value--${analysis.spikeLevel}">${escapeHtml(analysis.spikeLabel)}</strong>
          </div>
        </header>

        ${spikeMeterHtml(analysis.score, analysis.spikeLevel)}

        <div class="predictor-moves">
          <div class="predictor-move predictor-move--risk">
            <span class="predictor-move-label">Risk move</span>
            <p class="predictor-move-text">${riskContent}</p>
          </div>
          <div class="predictor-move predictor-move--safe">
            <span class="predictor-move-label">Safe move</span>
            <p class="predictor-move-text" id="predictor-safe-move-text">${safeContent}</p>
          </div>
        </div>

        <p class="predictor-reason">${reasonContent}</p>

        <footer class="predictor-footer">
          ${actions}
          <p class="predictor-status" id="predictor-status" hidden role="status"></p>
        </footer>
      </article>`;

    if (emit) {
      window.dispatchEvent(
        new CustomEvent("crashout:predictor-updated", { detail: { analysis } })
      );
    }

    requestAnimationFrame(() => {
      el.classList.add("predictor-panel--entered");
    });
  }

  function setPredictorStatus(message) {
    const status = document.getElementById("predictor-status");
    if (!status) return;
    if (!message) {
      status.hidden = true;
      status.textContent = "";
      return;
    }
    status.hidden = false;
    status.textContent = message;
  }

  function applySafeMove() {
    if (!lastAnalysis?.unlocked) return;

    const seedPreview = document.getElementById("seed-preview-text");
    const safeText = lastAnalysis.safeMove;

    if (seedPreview) {
      seedPreview.textContent = safeText;
      seedPreview.classList.add("predictor-applied");
      window.setTimeout(() => seedPreview.classList.remove("predictor-applied"), 1200);
    }

    const post = document.querySelector(".feed-post--momentum");
    post?.classList.add("feed-post--expanded");

    setPredictorStatus("Safe move applied to your draft preview.");
    window.CrashoutRecoveryStreak?.recordWin?.("safe_move");
    window.CrashoutRecoveryStreak?.setLastSafeMove?.(lastAnalysis.safeMove);
    window.CrashoutMomentumScore?.render?.();
  }

  async function copySafeMove() {
    if (!lastAnalysis?.unlocked) return;

    const text = lastAnalysis.safeMove;
    try {
      await navigator.clipboard.writeText(text);
      setPredictorStatus("Safe move copied.");
    } catch (_) {
      setPredictorStatus("Could not copy — select the safe move manually.");
    }
  }

  function updateFromPipeline({ rawText, tone, ctaPayload }) {
    const localMatch = window.CrashoutDecisionFlow?.explainMatch?.(rawText) || null;
    const analysis = analyze({ rawText, tone, ctaPayload, localMatch });
    analysis.rawText = rawText;
    analysis.ctaPayload = ctaPayload;
    analysis.localMatch = localMatch;
    renderPanel(analysis);
    window.CrashoutMonetization?.renderPredictorTeaser?.();
    return analysis;
  }

  function updateFromServer({ rawText, tone, ctaPayload, predictor }) {
    if (!predictor) return updateFromPipeline({ rawText, tone, ctaPayload });
    const levels = {
      low: { score: 1, id: "low", label: "Low" },
      steady: { score: 3, id: "steady", label: "Steady" },
      rising: { score: 5, id: "rising", label: "Rising" },
      high: { score: 8, id: "hot", label: "High" },
    };
    const level = levels[predictor.risk_level] || levels.steady;
    const analysis = {
      score: level.score,
      spikeLevel: level.id,
      spikeLabel: level.label,
      riskMove: predictor.reason || "Posting while the spike is active",
      safeMove: predictor.safe_move || "Save this as a draft and pause",
      reason: predictor.reason || "Keep the next move small and reversible.",
      tone: tone || "universal",
      unlocked: isUnlocked(),
      analyzedAt: new Date().toISOString(),
      rawText,
      ctaPayload,
      serverAuthoritative: true,
    };
    renderPanel(analysis);
    window.CrashoutMonetization?.renderPredictorTeaser?.();
    return analysis;
  }

  function refresh() {
    if (lastAnalysis) {
      const next = analyze({
        rawText: lastAnalysis.rawText,
        tone: lastAnalysis.tone,
        ctaPayload: lastAnalysis.ctaPayload,
        localMatch: lastAnalysis.localMatch,
      });
      next.rawText = lastAnalysis.rawText;
      next.ctaPayload = lastAnalysis.ctaPayload;
      next.localMatch = lastAnalysis.localMatch;
      renderPanel(next, { emit: false });
    }
    window.CrashoutMonetization?.renderPredictorTeaser?.();
  }

  function renderPostsLaneCard() {
    if (!lastAnalysis) return "";

    const locked = !lastAnalysis.unlocked;
    const spike = lastAnalysis.spikeLabel;
    const safe = locked
      ? `Unlock ${uiLower("bad_decision_predictor", "risk check")}`
      : truncate(lastAnalysis.safeMove, 48);

    return `
      <article class="feed-item feed-item--predictor-summary unified-card neon-card" data-tone="${lastAnalysis.tone}">
        <div class="feed-item-content">
          <span class="monetization-badge monetization-badge--premium">${escapeHtml(uiLabel("bad_decision_predictor", "Risk check"))}</span>
          <h4 class="feed-item-headline">Your spike: ${escapeHtml(spike)}</h4>
          <p class="feed-item-summary">${locked ? "Creator Mode unlocks your safe move." : `Safe move: ${escapeHtml(safe)}`}</p>
          <footer class="feed-item-cta-footer">
            <button type="button" class="feed-action feed-action--primary" data-predictor-lane-action="open-composer">Open ${escapeHtml(uiLower("composer", "draft box"))}</button>
            ${
              locked
                ? `<button type="button" class="feed-action feed-action--upgrade" data-monetization-action="upgrade" data-tier="creator">Unlock</button>`
                : ""
            }
          </footer>
        </div>
      </article>`;
  }

  function handleClick(e) {
    const action = e.target.closest("[data-predictor-action]");
    if (!action) return;

    e.preventDefault();
    const kind = action.dataset.predictorAction;
    if (kind === "apply-safe") applySafeMove();
    if (kind === "copy-safe") copySafeMove();
  }

  function handleLaneClick(e) {
    const btn = e.target.closest("[data-predictor-lane-action]");
    if (!btn) return;
    e.preventDefault();
    window.CrashoutComposerModal?.open();
  }

  function init() {
    document.body.addEventListener("click", handleClick);
    document.body.addEventListener("click", handleLaneClick);
    window.addEventListener("crashout:upgrade-preview", refresh);
  }

  window.CrashoutPredictor = {
    analyze,
    render: renderPanel,
    updateFromPipeline,
    updateFromServer,
    refresh,
    clear: () => renderPanel(null),
    lastAnalysis: () => lastAnalysis,
    renderPostsLaneCard,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
