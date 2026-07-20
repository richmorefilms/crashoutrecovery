(function () {
  const input = document.getElementById("crashout-input");
  const composer = document.getElementById("feed-composer");
  const feedEmpty = document.getElementById("feed-empty");
  const feedTimeline = document.getElementById("feed-timeline");
  const stagePills = document.getElementById("stage-tone-pills");
  const stageToneCard = document.getElementById("stage-tone-card");
  const stageCta = document.getElementById("stage-cta");
  const stageCrashout = document.getElementById("stage-crashout");
  const feedCommunity = document.getElementById("feed-community");
  const feedCommunityList = document.getElementById("feed-community-list");
  const pillsHint = document.getElementById("tone-pills-hint");
  const toneCard = document.getElementById("tone-card");
  const toneBadge = document.getElementById("tone-card-badge");
  const toneReason = document.getElementById("tone-card-reason");
  const momentumPost = document.getElementById("momentum-feed-post");
  const ctaBody = document.getElementById("cta-card-body");
  const ctaMicro = document.getElementById("cta-micro-action");
  const seedPreviewText = document.getElementById("seed-preview-text");
  const feedPostTone = document.getElementById("feed-post-tone");
  const feedPostStatus = document.getElementById("feed-post-status");
  const ctaMeta = document.getElementById("cta-card-meta");
  const container = document.getElementById("crashout-container");
  const btnAuto = document.getElementById("btn-auto-tone");

  if (!input || !container) return;

  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiLower = (key, fallback) => window.CrashoutUICopy?.labelLower?.(key) || fallback;

  const TONE_VERBS = {
    humorous: "spark",
    direct: "signal",
    strategic: "draft",
    calm: "draft",
    universal: "draft",
  };

  const MICRO_ACTIONS = [
    `Write one line — save the ${uiLower("seed", "draft idea")}.`,
    "Drop a spark instead of the full crash.",
    "Share the tiny version with your circle.",
    "Start a micro-thread around this.",
    "Turn the spike into a draft, not a delete.",
    "Test one variable publicly.",
  ];

  const COMMUNITY_ITEMS = [
    {
      id: "c-1",
      type: "spark",
      tone: "humorous",
      author: "@coolhead",
      meta: "2h · spark",
      text: `Almost nuked my drafts. Posted a ${uiLower("seed", "draft idea")} instead. Circle got it.`,
    },
    {
      id: "c-2",
      type: "thread",
      tone: "direct",
      author: "@lineinthesand",
      meta: "4h · thread",
      text: "Thread: I wanted to reply-all. I wrote one line and closed the tab.",
    },
    {
      id: "c-3",
      type: "video",
      tone: "calm",
      author: "Recovery Shorts",
      meta: "6h · 0:42",
      text: "Pause before you post — breathe, draft, decide tomorrow.",
    },
    {
      id: "c-4",
      type: "spark",
      tone: "strategic",
      author: "@onevariable",
      meta: "8h · spark",
      text: "Tested one caption change instead of deleting the whole account.",
    },
    {
      id: "c-5",
      type: "thread",
      tone: "universal",
      author: "@softcheck",
      meta: "1d · thread",
      text: "Anyone else save the rant as a draft and feel better in the morning?",
    },
    {
      id: "c-6",
      type: "video",
      tone: "humorous",
      author: "Spike to Draft",
      meta: "1d · 1:05",
      text: "Turn the meltdown into a meme draft — your future self will thank you.",
    },
  ];

  let debounceInput;
  let debouncePipeline;
  let lastPipelineText = "";
  let pipelineRunning = false;
  let lastResult = null;
  let lastRawText = "";

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
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

  function setFeedPostStatus(message) {
    if (!feedPostStatus) return;
    if (!message) {
      feedPostStatus.hidden = true;
      feedPostStatus.textContent = "";
      return;
    }
    feedPostStatus.hidden = false;
    feedPostStatus.textContent = message;
  }

  function resetBelowPills() {
    hideStage(stageToneCard);
    hideStage(stageCta);
    hideStage(stageCrashout);
    hideStage(feedCommunity);
    container.innerHTML = "";
    if (feedCommunityList) feedCommunityList.innerHTML = "";
    toneCard?.classList.remove("is-collapsed");
    setFeedPostStatus("");
    momentumPost?.classList.remove("feed-post--expanded", "feed-post--thread");
  }

  function resetAll() {
    hideStage(stagePills);
    hideStage(stageToneCard);
    hideStage(stageCta);
    hideStage(stageCrashout);
    hideStage(feedCommunity);
    container.innerHTML = "";
    if (feedCommunityList) feedCommunityList.innerHTML = "";
    if (pillsHint) pillsHint.hidden = true;
    setPillHighlight(null);
    setFeedActive(false);
    composer?.classList.remove("composer--expanded", "composer--typing", "composer--focused");
    toneCard?.classList.remove("is-collapsed");
    lastResult = null;
    lastRawText = "";
    setFeedPostStatus("");
  }

  function setPillHighlight(tone) {
    document.querySelectorAll(".tone-pill").forEach((btn) => {
      const active = tone && btn.dataset.tone === tone;
      btn.classList.toggle("detected", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    if (toneCard) toneCard.dataset.tone = tone || "";
    if (toneBadge) toneBadge.dataset.tone = tone || "";
    if (momentumPost) momentumPost.dataset.tone = tone || "universal";
  }

  function updatePillsFromClient(text) {
    const result = CrashoutDecisionFlow.explainMatch(text);
    setPillHighlight(result.tone);
    if (pillsHint) {
      pillsHint.hidden = false;
      pillsHint.textContent = result.matched
        ? `Feels like ${result.tone} — ${result.reason}`
        : result.reason;
    }
    return result;
  }

  function populateToneCard(result) {
    if (!toneBadge || !toneReason) return;
    toneBadge.textContent = result.tone;
    toneReason.textContent = result.reason || "Tone detected from your words.";
  }

  function populateMomentumFeedPost(result, rawText) {
    const tone = result.tone || "universal";
    const hook = result.suggestion || result.aligned || "Take one small reversible step.";
    const seed = buildPostSeed(rawText, hook, tone);
    const micro = pickMicroAction(tone, hook);

    if (ctaBody) ctaBody.textContent = hook;
    if (ctaMicro) ctaMicro.textContent = micro;
    if (seedPreviewText) seedPreviewText.textContent = seed;
    if (feedPostTone) feedPostTone.textContent = tone;

    if (ctaMeta) {
      const parts = [];
      if (result.redirect_source) parts.push(`via ${result.redirect_source}`);
      if (result.example_id) parts.push(result.example_id);
      if (parts.length) {
        ctaMeta.hidden = false;
        ctaMeta.textContent = parts.join(" · ");
      } else {
        ctaMeta.hidden = true;
      }
    }

    momentumPost?.classList.remove("feed-post--expanded", "feed-post--thread");
    setFeedPostStatus("");
  }

  function renderCommunityFeed(tone, filter) {
    if (!feedCommunityList) return;

    let items = COMMUNITY_ITEMS.filter((item) => item.tone === tone || item.tone === "universal");
    if (filter === "video") {
      items = items.filter((item) => item.type === "video");
    } else if (filter === "sparks") {
      items = items.filter((item) => item.type === "spark" || item.type === "thread");
    }

    if (!items.length) {
      items = COMMUNITY_ITEMS.slice(0, 3);
    }

    feedCommunityList.innerHTML = items
      .map(
        (item) => `
        <article class="feed-community-item feed-community-item--${item.type}" data-tone="${item.tone}">
          <header class="feed-community-item-header">
            <span class="feed-community-avatar" aria-hidden="true">${item.author.charAt(1).toUpperCase()}</span>
            <div>
              <p class="feed-community-author">${item.author}</p>
              <p class="feed-community-meta">${item.meta}</p>
            </div>
            <span class="feed-community-type">${item.type}</span>
          </header>
          <p class="feed-community-text">${item.text}</p>
        </article>`
      )
      .join("");

    revealStage(feedCommunity);
    feedCommunity?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function saveSeedToStorage(seed) {
    try {
      const key = "crashout_seeds";
      const existing = JSON.parse(localStorage.getItem(key) || "[]");
      existing.unshift({ seed, savedAt: new Date().toISOString() });
      localStorage.setItem(key, JSON.stringify(existing.slice(0, 20)));
      return true;
    } catch (_) {
      return false;
    }
  }

  function handleFeedAction(action) {
    if (!lastResult) return;
    const tone = lastResult.tone || "universal";
    const hook = lastResult.suggestion || lastResult.aligned || "";
    const seed = buildPostSeed(lastRawText, hook, tone);

    switch (action) {
      case "post":
        momentumPost?.classList.add("feed-post--expanded");
        if (seedPreviewText) {
          seedPreviewText.contentEditable = "true";
          seedPreviewText.focus();
        }
        setFeedPostStatus(`Edit your ${uiLower("seed", "draft idea")}, then copy or post when ready.`);
        break;
      case "thread": {
        const starter = buildThreadStarter(lastRawText, hook, tone);
        momentumPost?.classList.add("feed-post--thread");
        if (seedPreviewText) seedPreviewText.textContent = starter;
        setFeedPostStatus("Thread starter ready — add your first reply below when you are.");
        break;
      }
      case "save":
        if (saveSeedToStorage(seed)) {
          setFeedPostStatus(`${uiLabel("seed", "Draft idea")} saved locally. You can revisit it anytime.`);
        } else {
          setFeedPostStatus(`Could not save ${uiLower("seed", "draft idea")} in this browser.`);
        }
        break;
      case "sparks":
        renderCommunityFeed(tone, "sparks");
        setFeedPostStatus("Similar sparks from your circle.");
        break;
      case "video":
        renderCommunityFeed(tone, "video");
        setFeedPostStatus("Related videos — watch, then decide.");
        break;
      default:
        break;
    }
  }

  async function suggestFromServer(text) {
    try {
      const res = await fetch("/api/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (res.ok) return res.json();
    } catch (_) {
      /* fall through */
    }
    const local = CrashoutDecisionFlow.explainMatch(text);
    return { ...local, suggestion: null, aligned: null };
  }

  async function runPipeline(text) {
    const trimmed = text.trim();
    if (!trimmed || pipelineRunning) return;
    if (trimmed === lastPipelineText && stageToneCard?.classList.contains("stage-visible")) return;

    pipelineRunning = true;
    lastPipelineText = trimmed;
    lastRawText = trimmed;
    btnAuto?.setAttribute("aria-busy", "true");
    btnAuto?.setAttribute("disabled", "true");

    setFeedActive(true);
    resetBelowPills();
    revealStage(stagePills);
    composer?.classList.add("composer--expanded");

    const result = await suggestFromServer(trimmed);
    lastResult = result;
    setPillHighlight(result.tone);
    updatePillsFromClient(trimmed);

    populateToneCard(result);
    revealStage(stageToneCard);
    stageToneCard?.classList.add("stage-enter");
    await delay(200);

    populateMomentumFeedPost(result, trimmed);
    revealStage(stageCta);
    stageCta?.classList.add("stage-enter");
    toneCard?.classList.add("is-collapsed");
    await delay(240);

    revealStage(stageCrashout);
    stageCrashout?.classList.add("stage-enter");
    await showCrashout(result.tone, { target: container });

    const embedLink = document.querySelector(".embed-link");
    if (embedLink) embedLink.href = `/embed?tone=${encodeURIComponent(result.tone)}`;

    pipelineRunning = false;
    btnAuto?.removeAttribute("aria-busy");
    btnAuto?.removeAttribute("disabled");
  }

  momentumPost?.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => handleFeedAction(btn.dataset.action));
  });

  input.addEventListener("input", () => {
    clearTimeout(debounceInput);
    clearTimeout(debouncePipeline);

    const text = input.value;
    if (!text.trim()) {
      resetAll();
      lastPipelineText = "";
      return;
    }

    setFeedActive(true);
    composer?.classList.add("composer--typing");

    debounceInput = setTimeout(() => {
      revealStage(stagePills);
      updatePillsFromClient(text);
      composer?.classList.remove("composer--typing");
      composer?.classList.add("composer--expanded");
    }, 180);

    debouncePipeline = setTimeout(() => runPipeline(text), 850);
  });

  input.addEventListener("focus", () => composer?.classList.add("composer--focused"));
  input.addEventListener("blur", () => composer?.classList.remove("composer--focused"));

  btnAuto?.addEventListener("click", () => {
    clearTimeout(debouncePipeline);
    if (input.value.trim()) runPipeline(input.value);
  });

  document.querySelectorAll(".tone-pill").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const tone = btn.dataset.tone;
      if (!tone) return;
      setFeedActive(true);
      setPillHighlight(tone);
      resetBelowPills();
      revealStage(stagePills);
      populateToneCard({ tone, reason: "Manual tone selection." });
      revealStage(stageToneCard);
      revealStage(stageCrashout);
      await showCrashout(tone, { target: container });
    });
  });

  input.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      clearTimeout(debouncePipeline);
      runPipeline(input.value);
    }
  });
})();
