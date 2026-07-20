/**
 * Dual-lane Crashout-aware feed — videos + headlines with CTA overlays.
 * Client-side only; tone-aware sorting, no backend changes.
 */
(function () {
  const FEED_CTAS = {
    seed_post: "Turn your spike into a draft idea.",
    draft_dont_delete: "Draft, don't delete.",
    meme_reply: "Drop one meme-level reply.",
    test_variable: "Test one variable.",
    micro_thread: "Start a micro-thread.",
  };

  const VIDEO_CATEGORIES = {
    reaction: "Reaction commentary",
    spike_moment: "Spike moment",
    bad_decision: "Bad decision breakdown",
    turnaround: "Turnaround example",
  };

  const HEADLINE_CATEGORIES = {
    drama_summary: "Drama summary",
    creator_beef: "Creator beef",
    meltdown: "Meltdown moment",
    algorithm_dip: "Algorithm dip",
    impulsive: "Impulsive decision",
    platform_punishment: "Platform punishment",
  };

  const VIDEO_ITEMS = [
    {
      id: "v1",
      tone: "direct",
      category: "bad_decision",
      title: "Reply-all rage in 18 seconds",
      description: "Watch the send button win — until the undo window closes.",
      duration: "0:18",
      creator: "Spike Lab",
      cta: "draft_dont_delete",
    },
    {
      id: "v2",
      tone: "humorous",
      category: "spike_moment",
      title: "Almost deleted the whole account",
      description: "One creator drafts the meltdown instead of posting it.",
      duration: "0:24",
      creator: "@coolhead",
      cta: "meme_reply",
    },
    {
      id: "v3",
      tone: "calm",
      category: "turnaround",
      title: "Pause before you post",
      description: "Breathe, draft, decide tomorrow — 30 seconds that saved a career.",
      duration: "0:30",
      creator: "Recovery Shorts",
      cta: "seed_post",
    },
    {
      id: "v4",
      tone: "strategic",
      category: "reaction",
      title: "One variable, not a nuke",
      description: "Commentary on testing a caption instead of burning the channel.",
      duration: "0:22",
      creator: "@onevariable",
      cta: "test_variable",
    },
    {
      id: "v5",
      tone: "universal",
      category: "turnaround",
      title: "Draft folder saved the day",
      description: "The rant lived in drafts. Morning-you was grateful.",
      duration: "0:15",
      creator: "Turnaround Tapes",
      cta: "seed_post",
    },
    {
      id: "v6",
      tone: "humorous",
      category: "reaction",
      title: "Meme your meltdown",
      description: "Reaction clip: turn the spike into comedy gold, not collateral.",
      duration: "0:28",
      creator: "Spike to Draft",
      cta: "meme_reply",
    },
  ];

  const HEADLINE_ITEMS = [
    {
      id: "h1",
      tone: "direct",
      category: "creator_beef",
      headline: "Public call-out spirals into reply-all disaster",
      summary: "Two creators escalated in public. The second screen was worse.",
      source: "Creator wire · 3h ago",
      cta: "draft_dont_delete",
    },
    {
      id: "h2",
      tone: "humorous",
      category: "meltdown",
      headline: "Viral meltdown thread gets saved as drafts",
      summary: "The funniest crashout never posted — and that was the win.",
      source: "Pop pulse · 5h ago",
      cta: "meme_reply",
    },
    {
      id: "h3",
      tone: "strategic",
      category: "algorithm_dip",
      headline: "Reach dipped 40% — creator almost nuked the archive",
      summary: "One metric spike led to a delete-everything impulse. They tested one variable instead.",
      source: "Algo watch · 8h ago",
      cta: "test_variable",
    },
    {
      id: "h4",
      tone: "calm",
      category: "drama_summary",
      headline: "Platform drama recap: punishment, pause, pivot",
      summary: "Stripped reach, cooling-off period, then a soft relaunch with one draft idea.",
      source: "Drama digest · 12h ago",
      cta: "seed_post",
    },
    {
      id: "h5",
      tone: "direct",
      category: "platform_punishment",
      headline: "Shadowban scare triggers account-delete threat",
      summary: "Support ticket + draft folder beat the irreversible button.",
      source: "Platform beat · 1d ago",
      cta: "draft_dont_delete",
    },
    {
      id: "h6",
      tone: "universal",
      category: "impulsive",
      headline: "Midnight post regret — circle talks them down",
      summary: "Impulsive quote-tweet pulled back. Micro-thread replaced the blast.",
      source: "Circle signal · 1d ago",
      cta: "micro_thread",
    },
  ];

  const TONE_CATEGORY_BOOST = {
    humorous: ["spike_moment", "meltdown", "reaction", "creator_beef"],
    direct: ["bad_decision", "creator_beef", "platform_punishment", "impulsive"],
    strategic: ["turnaround", "algorithm_dip", "reaction"],
    calm: ["turnaround", "drama_summary"],
    universal: [],
  };

  let activeTone = null;
  let videoListEl;
  let headlineListEl;
  let sortLabelEl;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function scoreItem(item, tone) {
    if (!tone) return 0;
    let score = 0;
    if (item.tone === tone) score += 3;
    else if (item.tone === "universal") score += 1;
    const boosts = TONE_CATEGORY_BOOST[tone] || [];
    if (boosts.includes(item.category)) score += 2;
    return score;
  }

  function sortByTone(items, tone) {
    if (!tone) return [...items];
    return [...items].sort((a, b) => scoreItem(b, tone) - scoreItem(a, tone));
  }

  function ctaText(key) {
    return FEED_CTAS[key] || FEED_CTAS.seed_post;
  }

  function renderCtaOverlay(item) {
    const text = ctaText(item.cta);
    return `
      <footer class="feed-item-cta-footer" aria-label="Crashout CTA">
        <p class="feed-item-cta-text">${escapeHtml(text)}</p>
        <button type="button" class="feed-item-cta-btn" data-cta-key="${item.cta}" data-item-id="${item.id}">
          Take this move
        </button>
      </footer>`;
  }

  function renderVideoCard(item, rank) {
    const categoryLabel = VIDEO_CATEGORIES[item.category] || item.category;
    const boosted = activeTone && scoreItem(item, activeTone) >= 3;
    return `
      <article
        class="feed-item feed-item--video${boosted ? " feed-item--boosted" : ""}"
        data-id="${item.id}"
        data-tone="${item.tone}"
        data-lane="video"
        style="animation-delay: ${rank * 60}ms"
      >
        <div class="feed-item-media" data-tone="${item.tone}">
          <span class="feed-item-duration">${escapeHtml(item.duration)}</span>
          <span class="feed-item-play" aria-hidden="true">▶</span>
          <span class="feed-item-category">${escapeHtml(categoryLabel)}</span>
        </div>
        <div class="feed-item-content">
          <div class="feed-item-body">
            <h4 class="feed-item-title">${escapeHtml(item.title)}</h4>
            <p class="feed-item-desc">${escapeHtml(item.description)}</p>
            <p class="feed-item-meta">${escapeHtml(item.creator)}</p>
          </div>
          ${renderCtaOverlay(item)}
        </div>
      </article>`;
  }

  function renderHeadlineCard(item, rank) {
    const categoryLabel = HEADLINE_CATEGORIES[item.category] || item.category;
    const boosted = activeTone && scoreItem(item, activeTone) >= 3;
    return `
      <article
        class="feed-item feed-item--headline${boosted ? " feed-item--boosted" : ""}"
        data-id="${item.id}"
        data-tone="${item.tone}"
        data-lane="headline"
        style="animation-delay: ${rank * 60}ms"
      >
        <div class="feed-item-content">
          <span class="feed-item-category feed-item-category--headline">${escapeHtml(categoryLabel)}</span>
          <h4 class="feed-item-headline">${escapeHtml(item.headline)}</h4>
          <p class="feed-item-summary">${escapeHtml(item.summary)}</p>
          <p class="feed-item-source">${escapeHtml(item.source)}</p>
          ${renderCtaOverlay(item)}
        </div>
      </article>`;
  }

  function updateSortLabel(tone) {
    if (!sortLabelEl) return;
    sortLabelEl.textContent = tone
      ? `Sorted for ${tone} tone — drama teaches, spikes become draft ideas.`
      : "Drama teaches. Spikes become draft ideas.";
  }

  function render(tone) {
    activeTone = tone || null;
    if (!videoListEl || !headlineListEl) return;

    const videos = sortByTone(VIDEO_ITEMS, activeTone);
    const headlines = sortByTone(HEADLINE_ITEMS, activeTone);

    videoListEl.innerHTML = videos.map((item, i) => renderVideoCard(item, i)).join("");
    headlineListEl.innerHTML = headlines.map((item, i) => renderHeadlineCard(item, i)).join("");

    updateSortLabel(activeTone);
    document.getElementById("dual-feed")?.classList.toggle("dual-feed--tone-active", Boolean(activeTone));
  }

  function scrollToLane(lane) {
    const el = lane === "video" ? document.getElementById("feed-lane-video") : document.getElementById("feed-lane-headlines");
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function highlightLane(lane) {
    const el = lane === "video" ? document.getElementById("feed-lane-video") : document.getElementById("feed-lane-headlines");
    el?.classList.add("feed-lane--highlight");
    setTimeout(() => el?.classList.remove("feed-lane--highlight"), 1400);
  }

  function applyCtaToComposer(ctaKey) {
    const input = document.getElementById("crashout-input");
    const social = document.getElementById("crashout-social");
    const text = ctaText(ctaKey);

    social?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (input && !input.value.trim()) {
      input.placeholder = `${text} What's running through your head?`;
      input.focus();
    } else {
      input?.focus();
    }

    window.dispatchEvent(
      new CustomEvent("crashout:feed-cta", { detail: { ctaKey, text } })
    );
  }

  function handleClick(e) {
    const btn = e.target.closest(".feed-item-cta-btn");
    if (!btn) return;
    applyCtaToComposer(btn.dataset.ctaKey);
  }

  function init() {
    videoListEl = document.getElementById("feed-lane-video-list");
    headlineListEl = document.getElementById("feed-lane-headlines-list");
    sortLabelEl = document.getElementById("dual-feed-sort-label");

    if (!videoListEl || !headlineListEl) return;

    document.getElementById("dual-feed")?.addEventListener("click", handleClick);
    render(null);
  }

  window.CrashoutDualFeed = {
    render,
    scrollToLane,
    highlightLane,
    ctaText,
    FEED_CTAS,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
