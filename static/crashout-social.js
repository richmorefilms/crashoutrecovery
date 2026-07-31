document.addEventListener("DOMContentLoaded", () => {
  const socialEl = document.getElementById("crashout-social");
  const inputEl = document.getElementById("crashout-input");
  const submitEl = document.getElementById("crashout-submit");
  const toneRowEl = document.getElementById("crashout-tone-row");
  const toneLabelEl = document.getElementById("crashout-tone-label");
  const toneHintEl = document.getElementById("crashout-tone-hint");
  const ctaCardEl = document.getElementById("crashout-cta-card");
  const feedEmpty = document.getElementById("feed-empty");
  const feedPostsPersonal = document.getElementById("feed-posts-personal");
  const feedTimeline = document.getElementById("feed-timeline");
  const stageToneCard = document.getElementById("stage-tone-card");
  const stageCrashout = document.getElementById("stage-crashout");
  const toneCard = document.getElementById("tone-card");
  const toneBadge = document.getElementById("tone-card-badge");
  const toneReason = document.getElementById("tone-card-reason");
  const container = document.getElementById("crashout-container");

  if (!inputEl || !submitEl || !toneRowEl || !ctaCardEl || !container) return;

  const uiLabel = (key) => window.CrashoutUICopy?.label?.(key) || key;
  const uiLower = (key) => window.CrashoutUICopy?.labelLower?.(key) || key;

  const TONES = (socialEl?.dataset.tones || "humorous,direct,strategic,calm,universal")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const TONE_VERBS = {
    humorous: "spark",
    direct: "signal",
    strategic: "draft",
    calm: "draft",
    universal: "draft",
  };

  const MICRO_ACTIONS = [
    "Write one line — save the draft idea.",
    "Drop a spark instead of the full crash.",
    "Share the tiny version with your circle.",
    "Start a micro-thread around this.",
    "Turn the spike into a draft, not a delete.",
    "Test one variable publicly.",
  ];

  let debounceInput;
  let debouncePipeline;
  let lastPipelineText = "";
  let pipelineRunning = false;
  let lastResult = null;
  let lastRawText = "";
  let lastSelectedRewrite = 0;
  let composeController = null;
  let composeRequestId = 0;

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
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

  function pickMicroAction(tone, suggestion) {
    const idx = (tone.length + (suggestion?.length || 0)) % MICRO_ACTIONS.length;
    return MICRO_ACTIONS[idx];
  }

  function softenThought(raw) {
    return raw
      .replace(/\b(delete|nuke|quit|burn)\w*\b/gi, "draft")
      .replace(/\bforever\b/gi, "for now")
      .replace(/\s+/g, " ")
      .trim();
  }

  function buildPostSeed(rawThought, suggestion, tone) {
    const verb = TONE_VERBS[tone] || "draft";
    const base = suggestion || softenThought(rawThought);
    const line = firstSentence(base);
    return `${verb.charAt(0).toUpperCase() + verb.slice(1)}: ${truncate(line, 160)}`;
  }

  function buildThreadStarter(rawThought, suggestion, tone) {
    const verb = TONE_VERBS[tone] || "thread";
    const soft = softenThought(rawThought);
    const hook = suggestion ? firstSentence(suggestion) : firstSentence(soft);
    return `${verb.charAt(0).toUpperCase() + verb.slice(1)} starter — ${truncate(hook, 120)}`;
  }

  function revealStage(el) {
    if (!el) return;
    el.classList.remove("stage-hidden");
    el.classList.add("stage-visible");
  }

  function hideStage(el) {
    if (!el) return;
    el.classList.remove("stage-visible", "stage-enter");
    el.classList.add("stage-hidden");
  }

  function setFeedActive(active) {
    document.body.classList.toggle("feed--active", active);
    if (feedEmpty) feedEmpty.hidden = active;
    if (feedTimeline) feedTimeline.classList.toggle("feed-timeline--live", active);
    socialEl?.classList.toggle("crashout-social--active", active);
    if (feedPostsPersonal && active) {
      feedPostsPersonal.classList.remove("stage-hidden");
    } else if (feedPostsPersonal && !active) {
      feedPostsPersonal.classList.add("stage-hidden");
    }
  }

  function renderTonePills(tone, reason) {
    toneRowEl.innerHTML = "";
    toneRowEl.classList.remove("crashout-tone-row--visible");
    if (!tone) {
      if (toneHintEl) toneHintEl.hidden = true;
      if (toneLabelEl) toneLabelEl.hidden = true;
      return;
    }

    if (toneLabelEl) toneLabelEl.hidden = false;
    toneRowEl.classList.add("crashout-tone-row--visible");

    TONES.forEach((t) => {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = `crashout-tone-pill crashout-tone-${t}`;
      if (t === tone) pill.classList.add("detected");
      pill.dataset.tone = t;
      pill.setAttribute("aria-pressed", t === tone ? "true" : "false");
      pill.textContent = t.charAt(0).toUpperCase() + t.slice(1);
      pill.addEventListener("click", () => handleManualTone(t));
      toneRowEl.appendChild(pill);
    });

    if (toneHintEl) {
      toneHintEl.hidden = !reason;
      toneHintEl.textContent = reason || "";
    }

    if (toneCard) toneCard.dataset.tone = tone;
    if (toneBadge) toneBadge.dataset.tone = tone;

    window.CrashoutMomentumScore?.render?.();
  }

  function renderCtaCard(payload, rawText) {
    if (!payload) {
      ctaCardEl.classList.add("hidden");
      ctaCardEl.innerHTML = "";
      document.body.classList.remove("crashout-social-has-cta");
      showModalDone(false);
      window.CrashoutPredictor?.clear?.();
      return;
    }

    window.CrashoutMonetization?.renderComposerUpsell?.();
    window.CrashoutMonetization?.renderComposerUpsellBar?.();
    document.body.classList.add("crashout-social-has-cta");
    showModalDone(true);

    const tone = payload.tone || "universal";
    const rewrites = Array.isArray(payload.tone_suggestions) ? payload.tone_suggestions : [];
    const ctas = Array.isArray(payload.cta_suggestions) ? payload.cta_suggestions : [];
    const primary = rewrites[0] || {
      label: "Safer rewrite",
      text: payload.suggestion || payload.aligned || "Take one small reversible step.",
      source: "AI-assisted",
    };
    lastSelectedRewrite = 0;
    const hook = primary.text;
    const seed = hook;
    const rewriteChoices = rewrites
      .map(
        (item, index) => `
          <button type="button" class="feed-action compose-rewrite-choice${index === 0 ? " compose-rewrite-choice--active" : ""}" data-rewrite-index="${index}">
            ${escapeHtml(item.label)}
            <span class="compose-source">${escapeHtml(item.source)}</span>
          </button>`
      )
      .join("");
    const ctaChoices = ctas
      .map(
        (item) => `
          <li class="compose-cta-suggestion">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(item.text)}</span>
            <small>${escapeHtml(item.source)}</small>
          </li>`
      )
      .join("");

    ctaCardEl.classList.remove("hidden");
    ctaCardEl.innerHTML = `
      <article class="feed-post feed-post--momentum unified-card neon-card" data-tone="${tone}">
        <header class="feed-post-header">
          <div class="feed-post-avatar" aria-hidden="true">You</div>
          <div class="feed-post-identity">
            <p class="feed-post-author">You</p>
            <p class="feed-post-meta">
              <span class="feed-post-type">${escapeHtml(uiLabel("seed"))}</span>
              <span aria-hidden="true">·</span>
              <span class="feed-post-tone">${tone}</span>
            </p>
          </div>
          <span class="feed-post-badge">Next step</span>
        </header>
        <p class="crashout-cta-title">${escapeHtml(uiLabel("momentum_cta"))}</p>
        <p class="crashout-cta-body feed-post-hook">${escapeHtml(uiLabel("compose_rewrites"))}</p>
        <div class="compose-rewrite-choices" aria-label="${escapeHtml(uiLabel("compose_rewrites"))}">${rewriteChoices}</div>
        <div class="seed-preview">
          <span class="seed-preview-label">${escapeHtml(uiLabel("seed"))} preview</span>
          <p class="seed-preview-text" id="seed-preview-text" contenteditable="true">${escapeHtml(seed)}</p>
        </div>
        ${ctaChoices ? `<ul class="compose-cta-suggestions">${ctaChoices}</ul>` : ""}
        <div class="crashout-cta-actions feed-post-actions">
          <button type="button" class="feed-action feed-action--primary" data-action="post">${escapeHtml(uiLabel("compose_edit"))}</button>
          <button type="button" class="feed-action" data-action="thread">Make thread starter</button>
          <button type="button" class="feed-action" data-action="save">${escapeHtml(uiLabel("compose_save_review"))}</button>
          <button type="button" class="feed-action" data-action="sparks">See drama lane</button>
          <button type="button" class="feed-action" data-action="video">Watch moments</button>
        </div>
        <p class="feed-post-status" id="feed-post-status" hidden></p>
      </article>`;

    window.CrashoutPredictor?.updateFromServer?.({
      rawText,
      tone: payload.tone || "universal",
      ctaPayload: payload,
      predictor: payload.predictor,
    });
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function setFeedPostStatus(message) {
    const statusEl = ctaCardEl.querySelector("#feed-post-status");
    if (!statusEl) return;
    if (!message) {
      statusEl.hidden = true;
      statusEl.textContent = "";
      return;
    }
    statusEl.hidden = false;
    statusEl.textContent = message;
  }

  function syncDualFeed(tone) {
    window.CrashoutTabbedFeed?.render(tone || null);
  }

  function resetFeedBelow() {
    hideStage(stageToneCard);
    hideStage(stageCrashout);
    container.innerHTML = "";
    toneCard?.classList.remove("is-collapsed");
    ctaCardEl.querySelector(".feed-post--momentum")?.classList.remove("feed-post--expanded", "feed-post--thread");
    setFeedPostStatus("");
  }

  function resetAll() {
    renderTonePills(null);
    renderCtaCard(null);
    resetFeedBelow();
    setFeedActive(false);
    syncDualFeed(null);
    document.body.classList.remove("crashout-social-has-cta");
    lastResult = null;
    lastRawText = "";
    lastSelectedRewrite = 0;
    lastPipelineText = "";
  }

  function populateToneCard(result) {
    if (!toneBadge || !toneReason) return;
    toneBadge.textContent = result.tone;
    toneReason.textContent = result.reason || "Tone detected from your words.";
  }

  function saveSeedToStorage(seed, metadata = {}) {
    try {
      const key = "crashout_seeds";
      const existing = window.CrashoutUserStore
        ? window.CrashoutUserStore.get(key) || []
        : JSON.parse(localStorage.getItem(key) || "[]");
      const list = Array.isArray(existing) ? existing : [];
      list.unshift({ seed, savedAt: new Date().toISOString(), ...metadata });
      const next = list.slice(0, 20);
      if (window.CrashoutUserStore) {
        window.CrashoutUserStore.set(key, next);
      } else {
        localStorage.setItem(key, JSON.stringify(next));
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  async function queueSeedForModeration(seed) {
    const token = window.CrashoutAuth?.token?.();
    if (!token || !lastResult?.compose_receipt) return { queued: false, reason: "signed_out" };
    const response = await fetch("/api/save_seed", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        spike_text: lastRawText,
        suggested_rewrite: seed,
        safe_move: lastResult.predictor?.safe_move || null,
        tone: lastResult.tone || null,
        compose_receipt: lastResult.compose_receipt,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Could not queue draft for review");
    }
    return { queued: true, data: await response.json() };
  }

  async function handleFeedAction(action) {
    if (!lastResult) return;
    const tone = lastResult.tone || "universal";
    const hook = lastResult.tone_suggestions?.[0]?.text || "";
    const post = ctaCardEl.querySelector(".feed-post--momentum");
    const seedPreviewText = ctaCardEl.querySelector("#seed-preview-text");
    const visibleSeed = seedPreviewText?.textContent?.trim() || buildPostSeed(lastRawText, hook, tone);

    switch (action) {
      case "post":
        post?.classList.add("feed-post--expanded");
        if (seedPreviewText) {
          seedPreviewText.contentEditable = "true";
          seedPreviewText.focus();
        }
        setFeedPostStatus(`Edit your ${uiLower("seed")}, then copy or post when ready.`);
        break;
      case "thread": {
        const starter = buildThreadStarter(lastRawText, hook, tone);
        post?.classList.add("feed-post--thread");
        if (seedPreviewText) seedPreviewText.textContent = starter;
        setFeedPostStatus("Thread starter ready — add your first reply below when you are.");
        break;
      }
      case "save":
        if (
          saveSeedToStorage(visibleSeed, {
            tone,
            source:
              lastResult.tone_suggestions?.[lastSelectedRewrite]?.source || null,
          })
        ) {
          window.CrashoutRecoveryStreak?.bumpStreak?.("draft_saved");
          window.CrashoutMomentumScore?.render?.();
          setFeedPostStatus(`${uiLabel("seed")} saved. Queueing for staff review if signed in…`);
          try {
            const queued = await queueSeedForModeration(visibleSeed);
            setFeedPostStatus(
              queued.queued
                ? `${uiLabel("seed")} saved and queued for private staff review.`
                : `${uiLabel("seed")} saved in this browser. Sign in to submit it for staff review.`
            );
          } catch (error) {
            setFeedPostStatus(
              `${uiLabel("seed")} saved in this browser. ${error.message}`
            );
          }
        } else {
          setFeedPostStatus(`Could not save ${uiLower("seed")} in this browser.`);
        }
        break;
      case "sparks":
        window.CrashoutTabbedFeed?.render(tone);
        window.CrashoutTabbedFeed?.switchLane("drama");
        window.CrashoutTabbedFeed?.highlightLane("drama");
        setFeedPostStatus("Drama lane — learn from similar meltdowns and bad decisions.");
        break;
      case "video":
        window.CrashoutTabbedFeed?.render(tone);
        window.CrashoutTabbedFeed?.switchLane("moments");
        window.CrashoutTabbedFeed?.highlightLane("moments");
        setFeedPostStatus("Moments lane — watch spike clips, then take one move.");
        break;
      default:
        break;
    }
  }

  async function fetchSuggestion(text, signal) {
    const res = await fetch("/api/compose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spike_text: text }),
      signal,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || "Composer suggestions are temporarily unavailable");
    }
    return res.json();
  }

  function renderComposerError(message) {
    ctaCardEl.classList.remove("hidden");
    ctaCardEl.innerHTML = `
      <article class="feed-post feed-post--momentum unified-card neon-card">
        <p class="crashout-cta-title">Could not load safer rewrites</p>
        <p class="crashout-cta-body">${escapeHtml(message)}</p>
        <p class="feed-post-micro">Your text has not been saved. Try again when you are ready.</p>
      </article>`;
  }

  async function runPipeline(text) {
    const trimmed = text.trim();
    if (!trimmed) return;
    if (trimmed === lastPipelineText && !ctaCardEl.classList.contains("hidden")) return;

    composeController?.abort();
    composeController = new AbortController();
    const requestId = ++composeRequestId;
    pipelineRunning = true;
    lastPipelineText = trimmed;
    lastRawText = trimmed;
    submitEl.setAttribute("aria-busy", "true");
    submitEl.disabled = true;

    setFeedActive(true);
    resetFeedBelow();

    try {
      const result = await fetchSuggestion(trimmed, composeController.signal);
      if (requestId !== composeRequestId) return;
      lastResult = result;

      const reason = result.tone_reason || "Tone detected from your words.";
      renderTonePills(result.tone, reason);
      populateToneCard({ tone: result.tone, reason });
      renderCtaCard(result, trimmed);
      syncDualFeed(result.tone);
      window.CrashoutTabbedFeed?.switchLane("posts");

      revealStage(stageToneCard);
      stageToneCard?.classList.add("stage-enter");
      await delay(180);

      revealStage(stageCrashout);
      stageCrashout?.classList.add("stage-enter");
      toneCard?.classList.add("is-collapsed");
      await showCrashout(result.tone, { target: container });

      const embedLink = document.querySelector(".embed-link");
      if (embedLink) embedLink.href = `/embed?tone=${encodeURIComponent(result.tone)}`;
    } catch (error) {
      if (error.name !== "AbortError" && requestId === composeRequestId) {
        lastResult = null;
        renderComposerError(error.message);
      }
    } finally {
      if (requestId === composeRequestId) {
        pipelineRunning = false;
        submitEl.removeAttribute("aria-busy");
        submitEl.disabled = false;
      }
    }
  }

  async function handleManualTone(tone) {
    setFeedActive(true);
    renderTonePills(tone, "Manual tone selection.");
    resetFeedBelow();
    populateToneCard({ tone, reason: "Manual tone selection." });
    revealStage(stageToneCard);
    revealStage(stageCrashout);
    await showCrashout(tone, { target: container });
  }

  ctaCardEl.addEventListener("click", (e) => {
    const rewrite = e.target.closest("[data-rewrite-index]");
    if (rewrite && lastResult) {
      const item = lastResult.tone_suggestions?.[Number(rewrite.dataset.rewriteIndex)];
      const preview = ctaCardEl.querySelector("#seed-preview-text");
      if (item && preview) {
        lastSelectedRewrite = Number(rewrite.dataset.rewriteIndex);
        preview.textContent = item.text;
        ctaCardEl
          .querySelectorAll("[data-rewrite-index]")
          .forEach((button) => button.classList.toggle("compose-rewrite-choice--active", button === rewrite));
        setFeedPostStatus(`${item.label} applied. Review and edit before saving.`);
      }
      return;
    }
    const btn = e.target.closest("[data-action]");
    if (btn) handleFeedAction(btn.dataset.action);
  });

  submitEl.addEventListener("click", () => {
    clearTimeout(debouncePipeline);
    const text = inputEl.value.trim();
    if (text) runPipeline(text);
  });

  inputEl.addEventListener("focus", () => socialEl?.classList.add("crashout-social--focused"));
  inputEl.addEventListener("blur", () => socialEl?.classList.remove("crashout-social--focused"));

  inputEl.addEventListener("input", () => {
    clearTimeout(debounceInput);
    clearTimeout(debouncePipeline);

    const text = inputEl.value;
    if (!text.trim()) {
      resetAll();
      return;
    }

    setFeedActive(true);

    debounceInput = setTimeout(() => {
      const local = CrashoutDecisionFlow.explainMatch(text);
      const reason = local.matched
        ? `Feels like ${local.tone} — ${local.reason}`
        : local.reason;
      renderTonePills(local.tone, reason);
      syncDualFeed(local.tone);
    }, 180);

    debouncePipeline = setTimeout(() => runPipeline(text), 850);
  });

  inputEl.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      clearTimeout(debouncePipeline);
      runPipeline(inputEl.value);
    }
  });

  window.addEventListener("crashout:feed-cta", (e) => {
    const text = e.detail?.text;
    if (text) setFeedPostStatus(`${text} — type your spike above.`);
  });

  const modalEl = document.getElementById("composer-modal");
  const modalDoneEl = document.getElementById("composer-modal-done");
  const composeFab = document.getElementById("compose-fab");
  let lastFocusEl = null;

  function showModalDone(show) {
    if (!modalDoneEl) return;
    if (show) modalDoneEl.removeAttribute("hidden");
    else modalDoneEl.setAttribute("hidden", "");
  }

  function openComposerModal() {
    if (!modalEl) return;
    lastFocusEl = document.activeElement;
    modalEl.hidden = false;
    modalEl.setAttribute("aria-hidden", "false");
    document.body.classList.add("composer-modal-open");
    window.CrashoutMonetization?.renderComposerUpsell?.();
    window.CrashoutMonetization?.renderComposerUpsellBar?.();
    window.CrashoutMonetization?.renderPredictorTeaser?.();
    window.CrashoutPredictor?.refresh?.();
    window.setTimeout(() => inputEl?.focus(), 120);
  }

  function closeComposerModal() {
    if (!modalEl) return;
    modalEl.hidden = true;
    modalEl.setAttribute("aria-hidden", "true");
    document.body.classList.remove("composer-modal-open");
    if (lastFocusEl && typeof lastFocusEl.focus === "function") lastFocusEl.focus();
    else composeFab?.focus();
  }

  window.CrashoutComposerModal = { open: openComposerModal, close: closeComposerModal };

  composeFab?.addEventListener("click", openComposerModal);

  modalEl?.querySelectorAll("[data-close-modal]").forEach((el) => {
    el.addEventListener("click", closeComposerModal);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && document.body.classList.contains("composer-modal-open")) {
      e.preventDefault();
      closeComposerModal();
    }
  });

  modalDoneEl?.addEventListener("click", () => {
    window.CrashoutTabbedFeed?.switchLane("posts");
    closeComposerModal();
  });
});
