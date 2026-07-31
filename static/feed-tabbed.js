/**
 * Tabbed Crashout-aware feed — Drama | Moments | Headlines | Signals | Posts | Creator
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiLower = (key, fallback) => window.CrashoutUICopy?.labelLower?.(key) || fallback;

  function feedCtas() {
    return {
      seed_post: `Turn your spike into a ${uiLower("seed", "draft idea")}.`,
      draft_dont_delete: "Draft, don't delete.",
      meme_reply: "Drop one meme-level reply.",
      test_variable: "Test one variable.",
      micro_thread: "Start a micro-thread.",
    };
  }

  function laneMeta() {
    return {
      drama: {
        title: "Drama feed",
        desc: "Learn from others' mistakes — meltdowns, beefs, dips, and turnarounds.",
      },
      moments: {
        title: "Video moments",
        desc: "Crashout culture clips — Gucci/Pooh arcs, spike examples, and recovery interviews. Tap play.",
      },
      headlines: {
        title: "Headlines",
        desc: "Pop culture context — drama summaries, creator news, platform meltdowns.",
      },
      signals: {
        title: "Signals",
        desc: `Today's world mood — ${uiLower("signals_pro", "world trends")} unlock forecasts and burnout clusters.`,
      },
      posts: {
        title: "Your circle",
        desc: `${uiLabel("seed", "Draft idea")}s, threads, replies, and micro-threads from the community.`,
      },
      creator: {
        title: "Creator Mode",
        desc: `Your ${uiLower("seed", "draft idea")}s, tone trends, spikes, and ${uiLower("recovery_streak", "win streak")}.`,
      },
      tiktok: {
        title: uiLabel("tiktok_recovery_feed", "TikTok Recovery Feed"),
        desc: uiTip("tiktok_recovery_feed") || "Recovery-themed TikTok clips — #recovery, #motivation, #mentalhealth.",
      },
    };
  }

  function uiTip(key) {
    return window.CrashoutUICopy?.tooltip?.(key) || "";
  }

  function isTikTokLiveMode(mode) {
    if (window.CrashoutTikTokFeed?.isLiveMode) {
      return window.CrashoutTikTokFeed.isLiveMode(mode);
    }
    return mode === "research" || mode === "display";
  }

  function applyMainTikTokModeBadge(mode) {
    const badge = document.getElementById("tiktok-feed-mode-badge-main");
    if (!badge) return;
    const live = isTikTokLiveMode(mode);
    badge.hidden = false;
    badge.classList.remove("tiktok-feed-mode-badge--live", "tiktok-feed-mode-badge--curated");
    badge.classList.add(live ? "tiktok-feed-mode-badge--live" : "tiktok-feed-mode-badge--curated");
    badge.textContent = live
      ? uiLabel("tiktok_feed_live", "Live")
      : uiLabel("tiktok_feed_curated", "Curated");
  }

  const VIDEO_CATEGORIES = {
    reaction: "Reaction commentary",
    spike_moment: "Spike moment",
    emotional_spike: "Emotional spike",
    bad_decision: "Bad decision breakdown",
    turnaround: "Turnaround example",
    sideways: "Everything went sideways",
  };

  const HEADLINE_CATEGORIES = {
    drama_summary: "Drama summary",
    creator_beef: "Creator beef",
    creator_news: "Creator news",
    meltdown: "Meltdown moment",
    algorithm_dip: "Algorithm dip",
    impulsive: "Impulsive decision",
    platform_punishment: "Platform punishment",
    pop_culture: "Pop culture",
  };

  const DRAMA_CATEGORIES = {
    meltdown: "Meltdown moment",
    creator_beef: "Creator beef",
    algorithm_dip: "Algorithm dip",
    impulsive: "Impulsive decision",
    bad_decision: "Bad decision breakdown",
    turnaround: "Turnaround example",
  };

  function postCategories() {
    return {
      seed_post: uiLabel("seed", "Draft idea"),
      thread: "Thread",
      reply: "Reply",
      micro_thread: "Micro-thread",
    };
  }

  const MOMENT_ITEMS = [
    {
      id: "m1",
      tone: "direct",
      category: "sideways",
      title: "The moment the reply-all sent",
      description: "18 seconds before regret — here's where everything went sideways.",
      duration: "0:18",
      creator: "Spike Lab",
      cta: "draft_dont_delete",
    },
    {
      id: "m2",
      tone: "humorous",
      category: "spike_moment",
      title: "Almost deleted the whole account",
      description: "One creator drafts the meltdown instead of posting it.",
      duration: "0:24",
      creator: "@coolhead",
      cta: "meme_reply",
    },
    {
      id: "m3",
      tone: "calm",
      category: "emotional_spike",
      title: "Pause before you post",
      description: "Breathe through the spike — 30 seconds that saved a career.",
      duration: "0:30",
      creator: "Recovery Shorts",
      cta: "seed_post",
    },
    {
      id: "m4",
      tone: "strategic",
      category: "reaction",
      title: "One variable, not a nuke",
      description: "Reaction commentary on testing a caption instead of burning the channel.",
      duration: "0:22",
      creator: "@onevariable",
      cta: "test_variable",
    },
    {
      id: "m5",
      tone: "humorous",
      category: "reaction",
      title: "Meme your meltdown",
      description: "Turn the spike into comedy gold, not collateral damage.",
      duration: "0:28",
      creator: "Spike to Draft",
      cta: "meme_reply",
    },
    {
      id: "m6",
      tone: "direct",
      category: "spike_moment",
      title: "3am post vs morning-you",
      description: "Split screen: impulse spike on the left, draft folder on the right.",
      duration: "0:26",
      creator: "Night Shift",
      cta: "draft_dont_delete",
    },
  ];

  const DRAMA_ITEMS = [
    {
      id: "d1",
      tone: "direct",
      category: "creator_beef",
      headline: "Public call-out spirals into reply-all disaster",
      summary: "Two creators escalated in public. The second screen was worse.",
      source: "Creator wire · 3h ago",
      cta: "draft_dont_delete",
    },
    {
      id: "d2",
      tone: "humorous",
      category: "meltdown",
      headline: "Viral meltdown thread gets saved as drafts",
      summary: "The funniest crashout never posted — and that was the win.",
      source: "Pop pulse · 5h ago",
      cta: "meme_reply",
    },
    {
      id: "d3",
      tone: "strategic",
      category: "algorithm_dip",
      headline: "Reach dipped 40% — creator almost nuked the archive",
      summary: "One metric spike led to delete-everything. They tested one variable instead.",
      source: "Algo watch · 8h ago",
      cta: "test_variable",
    },
    {
      id: "d4",
      tone: "direct",
      category: "bad_decision",
      headline: "Bad decision breakdown: nuked drafts at 2am",
      summary: "Deleted 200 posts. Recovery started with one draft idea the next day.",
      source: "Breakdown desk · 10h ago",
      cta: "draft_dont_delete",
    },
    {
      id: "d5",
      tone: "calm",
      category: "turnaround",
      headline: "Turnaround example: shadowban scare to soft relaunch",
      summary: "Support ticket, draft folder, one calm draft idea — reach came back slow.",
      source: "Recovery log · 1d ago",
      cta: "seed_post",
    },
    {
      id: "d6",
      tone: "universal",
      category: "impulsive",
      headline: "Midnight quote-tweet regret — circle talks them down",
      summary: "Impulsive blast pulled back. Micro-thread replaced the meltdown.",
      source: "Circle signal · 1d ago",
      cta: "micro_thread",
    },
  ];

  const HEADLINE_ITEMS = [
    {
      id: "h1",
      tone: "calm",
      category: "drama_summary",
      headline: "Platform drama recap: punishment, pause, pivot",
      summary: "Stripped reach, cooling-off period, then a soft relaunch with one draft idea.",
      source: "Drama digest · 4h ago",
      cta: "seed_post",
    },
    {
      id: "h2",
      tone: "direct",
      category: "platform_punishment",
      headline: "Shadowban scare triggers account-delete threat",
      summary: "Creator news: support ticket + draft folder beat the irreversible button.",
      source: "Platform beat · 6h ago",
      cta: "draft_dont_delete",
    },
    {
      id: "h3",
      tone: "humorous",
      category: "pop_culture",
      headline: "Pop culture meltdown becomes meme template",
      summary: "The spike went viral as a draft meme — not as a career-ender.",
      source: "Culture wire · 8h ago",
      cta: "meme_reply",
    },
    {
      id: "h4",
      tone: "strategic",
      category: "creator_news",
      headline: "Creator pivots after algorithm punishment",
      summary: "One caption test, one thread, one week — reach recovered without a nuke.",
      source: "Creator news · 12h ago",
      cta: "test_variable",
    },
    {
      id: "h5",
      tone: "direct",
      category: "meltdown",
      headline: "Live meltdown clipped before the delete",
      summary: "Headline: platform meltdown stopped at the draft stage.",
      source: "Live desk · 1d ago",
      cta: "draft_dont_delete",
    },
    {
      id: "h6",
      tone: "universal",
      category: "algorithm_dip",
      headline: "Algo dip week: what the circle posted instead of quitting",
      summary: `${uiLabel("seed", "Draft idea")}s and micro-threads replaced the delete-account impulse.`,
      source: "Algo weekly · 2d ago",
      cta: "micro_thread",
    },
  ];

  const POST_ITEMS = [
    {
      id: "p1",
      tone: "humorous",
      category: "seed_post",
      author: "@coolhead",
      meta: "2h · draft idea",
      text: "Almost nuked my drafts. Posted a draft idea instead. Circle got it.",
      cta: "seed_post",
    },
    {
      id: "p2",
      tone: "direct",
      category: "thread",
      author: "@lineinthesand",
      meta: "4h · thread",
      text: "Thread: I wanted to reply-all. I wrote one line and closed the tab.",
      cta: "micro_thread",
    },
    {
      id: "p3",
      tone: "strategic",
      category: "reply",
      author: "@onevariable",
      meta: "6h · reply",
      text: "Tested one caption change instead of deleting the whole account.",
      cta: "test_variable",
    },
    {
      id: "p4",
      tone: "universal",
      category: "micro_thread",
      author: "@softcheck",
      meta: "1d · micro-thread",
      text: "Anyone else save the rant as a draft and feel better in the morning?",
      cta: "micro_thread",
    },
    {
      id: "p5",
      tone: "calm",
      category: "seed_post",
      author: "@draftfirst",
      meta: "1d · draft idea",
      text: "Draft, don't delete. Morning-me approved this tiny signal.",
      cta: "draft_dont_delete",
    },
    {
      id: "p6",
      tone: "humorous",
      category: "reply",
      author: "@memelevel",
      meta: "2d · reply",
      text: "Dropped one meme-level reply instead of the essay. Peace restored.",
      cta: "meme_reply",
    },
  ];

  const TONE_CATEGORY_BOOST = {
    humorous: ["spike_moment", "meltdown", "reaction", "creator_beef", "pop_culture", "seed_post", "reply"],
    direct: ["bad_decision", "creator_beef", "platform_punishment", "impulsive", "sideways", "thread"],
    strategic: ["turnaround", "algorithm_dip", "reaction", "creator_news"],
    calm: ["turnaround", "drama_summary", "emotional_spike", "seed_post"],
    universal: [],
  };

  let activeTone = null;
  let activeLane = "drama";
  let listEl;
  let titleEl;
  let descEl;
  let sortLabelEl;
  let emptyEl;

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
    const ctas = feedCtas();
    return ctas[key] || ctas.seed_post;
  }

  function categoryLabel(lane, category) {
    const maps = {
      drama: DRAMA_CATEGORIES,
      moments: VIDEO_CATEGORIES,
      headlines: HEADLINE_CATEGORIES,
      posts: postCategories(),
      signals: window.CrashoutWorldSignals?.CATEGORIES || {},
    };
    return (maps[lane] || {})[category] || category;
  }

  function renderCtaFooter(item) {
    const text = ctaText(item.cta);
    return `
      <footer class="feed-item-cta-footer" aria-label="Crashout CTA">
        <p class="feed-item-cta-text">${escapeHtml(text)}</p>
        <button type="button" class="feed-item-cta-btn neon-btn" data-cta-key="${item.cta}" data-item-id="${item.id}">
          Take this move
        </button>
      </footer>`;
  }

  function renderSignalCard(item, rank) {
    const label = categoryLabel("signals", item.category);
    const boosted = activeTone && window.CrashoutWorldSignals?.scoreItem(item, activeTone) >= 3;
    return `
      <article class="feed-item feed-item--signal feed-item--pulse-${item.pulse} unified-card neon-card${boosted ? " feed-item--boosted" : ""}" data-id="${item.id}" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          <header class="world-signal-card-header">
            <span class="world-signal-pulse world-signal-pulse--${item.pulse}" aria-label="Pulse ${item.pulse}"></span>
            <span class="feed-item-category feed-item-category--headline">${escapeHtml(label)}</span>
            <span class="world-signal-region">${escapeHtml(item.region)}</span>
          </header>
          <h4 class="feed-item-headline">${escapeHtml(item.headline)}</h4>
          <p class="feed-item-summary">${escapeHtml(item.summary)}</p>
          ${renderCtaFooter(item)}
        </div>
      </article>`;
  }

  function renderMomentCard(item, rank) {
    const label = categoryLabel("moments", item.category);
    const boosted = activeTone && scoreItem(item, activeTone) >= 3;
    const thumb = item.youtubeId
      ? `https://i.ytimg.com/vi/${escapeHtml(item.youtubeId)}/hqdefault.jpg`
      : "";
    const mediaStyle = thumb
      ? ` style="background-image:url('${thumb}')"`
      : "";
    const playAttr = item.videoId
      ? ` data-video-play="${escapeHtml(item.videoId)}" role="button" tabindex="0" aria-label="Play clip"`
      : "";
    return `
      <article class="feed-item feed-item--video unified-card neon-card${item.videoId ? " feed-item--video-live" : ""}${boosted ? " feed-item--boosted" : ""}" data-id="${item.id}" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-media${thumb ? " feed-item-media--thumb" : ""}" data-tone="${item.tone}"${mediaStyle}${playAttr}>
          <span class="feed-item-duration">${escapeHtml(item.duration)}</span>
          <span class="feed-item-play" aria-hidden="true">▶</span>
          <span class="feed-item-category">${escapeHtml(label)}</span>
        </div>
        <div class="feed-item-content">
          <div class="feed-item-body">
            <h4 class="feed-item-title">${escapeHtml(item.title)}</h4>
            <p class="feed-item-desc">${escapeHtml(item.description)}</p>
            <p class="feed-item-meta">${escapeHtml(item.creator)}</p>
          </div>
          ${
            item.videoId
              ? `<div class="feed-item-video-actions">
                   <button type="button" class="feed-item-cta-btn feed-item-cta-btn--play neon-btn" data-video-play="${escapeHtml(item.videoId)}">Play clip</button>
                 </div>`
              : ""
          }
          ${renderCtaFooter(item)}
        </div>
      </article>`;
  }

  function renderStoryCard(item, rank, lane) {
    const label = categoryLabel(lane, item.category);
    const boosted = activeTone && scoreItem(item, activeTone) >= 3;
    return `
      <article class="feed-item feed-item--headline unified-card neon-card${boosted ? " feed-item--boosted" : ""}" data-id="${item.id}" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          <span class="feed-item-category feed-item-category--headline">${escapeHtml(label)}</span>
          <h4 class="feed-item-headline">${escapeHtml(item.headline)}</h4>
          <p class="feed-item-summary">${escapeHtml(item.summary)}</p>
          <p class="feed-item-source">${escapeHtml(item.source)}</p>
          ${renderCtaFooter(item)}
        </div>
      </article>`;
  }

  function renderPostCard(item, rank) {
    const label = categoryLabel("posts", item.category);
    const boosted = activeTone && scoreItem(item, activeTone) >= 3;
    return `
      <article class="feed-item feed-item--post unified-card neon-card${boosted ? " feed-item--boosted" : ""}" data-id="${item.id}" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          <header class="feed-post-card-header">
            <span class="feed-community-avatar" aria-hidden="true">${item.author.charAt(1).toUpperCase()}</span>
            <div>
              <p class="feed-community-author">${escapeHtml(item.author)}</p>
              <p class="feed-community-meta">${escapeHtml(item.meta)}</p>
            </div>
            <span class="feed-item-category feed-item-category--headline">${escapeHtml(label)}</span>
          </header>
          <p class="feed-item-post-text">${escapeHtml(item.text)}</p>
          ${renderCtaFooter(item)}
        </div>
      </article>`;
  }

  function itemsForLane(lane) {
    switch (lane) {
      case "drama":
        return sortByTone(DRAMA_ITEMS, activeTone);
      case "moments": {
        const catalogItems = window.CrashoutVideos?.momentFeedItems?.() || [];
        // Catalog clips render in the Moments thumbnail grid; demo cards stay below.
        return catalogItems.length ? [] : sortByTone(MOMENT_ITEMS, activeTone);
      }
      case "headlines":
        return sortByTone(HEADLINE_ITEMS, activeTone);
      case "signals":
        return window.CrashoutWorldSignals?.sortByTone(
          window.CrashoutWorldSignals.ITEMS || [],
          activeTone
        ) || [];
      case "posts":
        return sortByTone(POST_ITEMS, activeTone);
      default:
        return [];
    }
  }

  function toggleSignalsProLane(isSignals) {
    const proPanel = document.getElementById("signals-pro-panel");
    const list = document.getElementById("feed-lane-list");
    const recovery = document.getElementById("recovery-week-card");
    const empty = document.getElementById("feed-empty");
    const personal = document.getElementById("feed-posts-personal");
    const panel = document.getElementById("feed-lane-panel");

    if (proPanel) proPanel.hidden = !isSignals;
    if (list) list.hidden = isSignals;
    if (recovery) recovery.hidden = isSignals;
    if (empty) empty.hidden = isSignals;
    if (personal) personal.classList.toggle("stage-hidden", isSignals || activeLane !== "posts");

    panel?.classList.toggle("feed-lane-panel--signals-pro", isSignals);

    if (isSignals) {
      window.CrashoutWorldSignals?.showProPanel?.();
      window.CrashoutWorldSignals?.renderProPanel?.();
    } else {
      window.CrashoutWorldSignals?.hideProPanel?.();
    }
  }

  function toggleCreatorLane(isCreator) {
    const dash = document.getElementById("creator-dashboard");
    const list = document.getElementById("feed-lane-list");
    const recovery = document.getElementById("recovery-week-card");
    const empty = document.getElementById("feed-empty");
    const personal = document.getElementById("feed-posts-personal");
    const panel = document.getElementById("feed-lane-panel");

    if (dash) dash.hidden = !isCreator;
    if (list) list.hidden = isCreator;
    if (recovery) recovery.hidden = isCreator;
    if (empty) empty.hidden = isCreator;
    if (personal) personal.classList.toggle("stage-hidden", isCreator || activeLane !== "posts");

    panel?.classList.toggle("feed-lane-panel--creator", isCreator);

    if (isCreator) {
      window.CrashoutCreatorDashboard?.show?.();
      window.CrashoutTikTokUpload?.mountCreatorControls?.("#creator-dashboard-body");
    } else {
      window.CrashoutCreatorDashboard?.hide?.();
    }
  }

  function renderLaneList(lane) {
    if (!listEl) return;

    if (lane === "creator") {
      toggleSignalsProLane(false);
      toggleCreatorLane(true);
      return;
    }

    if (lane === "signals") {
      toggleCreatorLane(false);
      toggleSignalsProLane(true);
      return;
    }

    if (lane === "tiktok") {
      toggleCreatorLane(false);
      toggleSignalsProLane(false);
      if (emptyEl) emptyEl.hidden = true;
      const renderPromise = window.CrashoutTikTokFeed?.renderInto?.(listEl, {
        hashtags: "recovery,motivation,mentalhealth",
      });
      Promise.resolve(renderPromise).then((data) => {
        if (activeLane !== "tiktok") return;
        const mode = data?.meta?.mode || "curated";
        applyMainTikTokModeBadge(mode);
      });
      return;
    }

    toggleCreatorLane(false);
    toggleSignalsProLane(false);

    const items = itemsForLane(lane);

    if (lane === "moments") {
      const grid = window.CrashoutVideos?.renderMomentsGridHtml?.() || "";
      const cards = items.map((item, i) => renderMomentCard(item, i)).join("");
      listEl.innerHTML = grid + cards;
      if (emptyEl) emptyEl.hidden = Boolean(grid) || items.length > 0;
      window.CrashoutVideos?.resolveMissingIds?.().catch(() => {});
    } else if (lane === "posts") {
      listEl.innerHTML = items.map((item, i) => renderPostCard(item, i)).join("");
      if (emptyEl) emptyEl.hidden = items.length > 0;
    } else if (lane === "signals") {
      listEl.innerHTML = items.map((item, i) => renderSignalCard(item, i)).join("");
      if (emptyEl) emptyEl.hidden = items.length > 0;
    } else {
      listEl.innerHTML = items.map((item, i) => renderStoryCard(item, i, lane)).join("");
      if (emptyEl) emptyEl.hidden = items.length > 0;
    }

    let html = listEl.innerHTML;
    if (lane === "posts" && window.CrashoutPredictor?.renderPostsLaneCard) {
      const predictorCard = window.CrashoutPredictor.renderPostsLaneCard();
      if (predictorCard) html = predictorCard + html;
    }
    if (window.CrashoutMonetization?.injectSponsoredHtml) {
      html = window.CrashoutMonetization.injectSponsoredHtml(lane, html);
    }
    listEl.innerHTML = html;
  }

  function updateLaneIntro(lane) {
    const catalog = laneMeta();
    const meta = catalog[lane] || catalog.drama;
    const seedPlural = `${uiLower("seed", "draft idea")}s`;
    if (titleEl) titleEl.textContent = meta.title;
    if (descEl) descEl.textContent = meta.desc;
    if (sortLabelEl) {
      sortLabelEl.textContent = activeTone
        ? `Sorted for ${activeTone} tone in ${meta.title.toLowerCase()}.`
        : lane === "moments"
          ? "Tap a thumbnail to watch — crashout clips load from videos.json."
          : lane === "signals"
          ? `Tap a pulse above — tiny signals become ${seedPlural}.`
          : lane === "creator"
            ? `Your dashboard — spikes become ${seedPlural}.`
            : lane === "tiktok"
              ? uiLabel("tiktok_recovery_feed", "TikTok Recovery Feed")
            : `Drama teaches. Spikes become ${seedPlural}.`;
    }

    const actions = document.getElementById("feed-lane-actions");
    if (actions) {
      if (lane === "moments") {
        actions.hidden = false;
        actions.innerHTML = `<button type="button" class="moments-add-video-btn neon-btn" data-video-manual-open>Add Video</button>`;
      } else if (lane === "tiktok") {
        actions.hidden = false;
        // Keep feed link; append mode badge for curated vs live
        actions.innerHTML = `
          <span class="tiktok-feed-mode-badge" id="tiktok-feed-mode-badge-main" hidden></span>
          <a class="moments-add-video-btn btn neon-btn" href="/feed">${uiLabel(
            "tiktok_recovery_feed",
            "TikTok Recovery Feed"
          )}</a>`;
      } else {
        actions.hidden = true;
        actions.innerHTML = "";
      }
    }
  }

  function setActiveTab(lane) {
    activeLane = lane;
    document.querySelectorAll(".feed-tab").forEach((tab) => {
      const on = tab.dataset.lane === lane;
      tab.classList.toggle("feed-tab--active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    });

    const activeTab = document.querySelector(`.feed-tab[data-lane="${lane}"]`);
    const panel = document.getElementById("feed-lane-panel");
    if (activeTab && panel) panel.setAttribute("aria-labelledby", activeTab.id);

    const personal = document.getElementById("feed-posts-personal");
    if (personal) {
      personal.classList.toggle("stage-hidden", lane !== "posts");
    }

    updateLaneIntro(lane);
    renderLaneList(lane);
    window.CrashoutRecoveryStreak?.showInPostsLane?.(lane === "posts");
    panel?.classList.toggle("feed-lane-panel--posts", lane === "posts");
    window.CrashoutSpikeAlert?.check?.();
  }

  function switchLane(lane) {
    if (!laneMeta()[lane]) return;
    setActiveTab(lane);
    document.getElementById("feed-tabs")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function highlightLane(lane) {
    const tab = document.querySelector(`.feed-tab[data-lane="${lane}"]`);
    tab?.classList.add("feed-tab--pulse");
    setTimeout(() => tab?.classList.remove("feed-tab--pulse"), 1200);
  }

  function render(tone) {
    activeTone = tone || null;
    document.getElementById("feed-lane-panel")?.classList.toggle("feed-lane-panel--tone-active", Boolean(activeTone));
    window.CrashoutWorldSignals?.renderStrip(activeTone);
    updateLaneIntro(activeLane);
    renderLaneList(activeLane);
  }

  function applyCtaToComposer(ctaKey) {
    const input = document.getElementById("crashout-input");
    const text = ctaText(ctaKey);
    window.CrashoutComposerModal?.open();
    if (input && !input.value.trim()) input.placeholder = `${text} What's running through your head?`;
    input?.focus();
    window.dispatchEvent(new CustomEvent("crashout:feed-cta", { detail: { ctaKey, text } }));
  }

  function playMomentClip(videoId) {
    if (!videoId || !window.CrashoutVideos) return;
    if (window.CrashoutVideos.playInToast) {
      window.CrashoutVideos.playInToast(videoId, "Moments · crashout clip");
      return;
    }
    const clip = window.CrashoutVideos.getClip(videoId);
    if (!clip) return;
    window.CrashoutVideos.showToast(clip, "Moments · crashout clip");
  }

  function handleClick(e) {
    const tab = e.target.closest(".feed-tab");
    if (tab?.dataset.lane) {
      setActiveTab(tab.dataset.lane);
      return;
    }

    const playBtn = e.target.closest("[data-video-play]");
    if (playBtn && !e.target.closest("[data-video-manual]")) {
      playMomentClip(playBtn.dataset.videoPlay);
      return;
    }

    const ctaBtn = e.target.closest(".feed-item-cta-btn");
    if (ctaBtn && !ctaBtn.dataset.videoPlay) applyCtaToComposer(ctaBtn.dataset.ctaKey);
  }

  function init() {
    listEl = document.getElementById("feed-lane-list");
    titleEl = document.getElementById("feed-lane-title");
    descEl = document.getElementById("feed-lane-desc");
    sortLabelEl = document.getElementById("feed-lane-sort-label");
    emptyEl = document.getElementById("feed-empty");

    if (!listEl) return;

    document.getElementById("feed")?.addEventListener("click", handleClick);
    window.addEventListener("crashout:predictor-updated", () => {
      if (activeLane === "posts") renderLaneList("posts");
      if (activeLane === "creator") window.CrashoutCreatorDashboard?.render?.();
    });
    window.addEventListener("crashout:predictor-cleared", () => {
      if (activeLane === "posts") renderLaneList("posts");
    });
    window.addEventListener("crashout:videos-ready", () => {
      if (activeLane === "moments") renderLaneList("moments");
    });
    setActiveTab("drama");
    render(null);
    window.CrashoutVideos?.load?.().then(() => {
      if (activeLane === "moments") renderLaneList("moments");
    });
    try {
      const lane = new URLSearchParams(window.location.search).get("lane");
      if (lane && laneMeta()[lane]) switchLane(lane);
    } catch (_) {
      /* ignore */
    }
  }

  const api = {
    render,
    switchLane,
    highlightLane,
    ctaText,
    get FEED_CTAS() {
      return feedCtas();
    },
    setActiveTab,
    openCreatorDashboard: () => switchLane("creator"),
  };

  window.CrashoutTabbedFeed = api;
  window.CrashoutDualFeed = {
    render: (tone) => api.render(tone),
    scrollToLane: (lane) => {
      if (lane === "video") api.switchLane("moments");
      else if (lane === "headline") api.switchLane("headlines");
      else if (lane === "signal" || lane === "signals") api.switchLane("signals");
      else api.switchLane("drama");
    },
    highlightLane: (lane) => {
      if (lane === "video") api.highlightLane("moments");
      else if (lane === "headline") api.highlightLane("headlines");
      else if (lane === "signal" || lane === "signals") api.highlightLane("signals");
      else api.highlightLane("drama");
    },
    ctaText: api.ctaText,
    get FEED_CTAS() {
      return api.FEED_CTAS;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
