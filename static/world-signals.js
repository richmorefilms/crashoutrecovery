/**
 * World Signals — global pulse strip + signal feed data.
 * Tiny signals from the wider world; tone-aware sorting. Client-side only.
 */
(function () {
  const SIGNAL_CATEGORIES = {
    algo_pulse: "Algo pulse",
    meltdown_index: "Meltdown index",
    platform_shift: "Platform shift",
    culture_spike: "Culture spike",
    crashout_risk: "Crashout risk",
    turnaround_pulse: "Turnaround pulse",
  };

  const WORLD_SIGNAL_ITEMS = [
    {
      id: "ws1",
      tone: "strategic",
      category: "algo_pulse",
      pulse: "high",
      chip: "Algo dip ↑",
      headline: "Reach signals dipping across mid-tier creators",
      summary: "Engagement clusters show a synchronized dip — test one variable before you nuke the archive.",
      region: "Global · Algo watch",
      cta: "test_variable",
    },
    {
      id: "ws2",
      tone: "humorous",
      category: "meltdown_index",
      pulse: "medium",
      chip: "Meltdown pulse",
      headline: "Main-character meltdown index spiking tonight",
      summary: "Pop-culture spike in public rants — drafts are outperforming live posts 3:1.",
      region: "Culture wire",
      cta: "meme_reply",
    },
    {
      id: "ws3",
      tone: "direct",
      category: "crashout_risk",
      pulse: "high",
      chip: "Delete impulse",
      headline: "Account-delete threats up after shadowban scares",
      summary: "Irreversible-action language rising in support tickets — draft-first is winning.",
      region: "Platform beat",
      cta: "draft_dont_delete",
    },
    {
      id: "ws4",
      tone: "calm",
      category: "turnaround_pulse",
      pulse: "low",
      chip: "Soft recovery",
      headline: "Turnaround signals: draft ideas stabilizing reach",
      summary: "Creators who posted one calm draft idea after a spike recovered faster than delete-and-restart.",
      region: "Recovery index",
      cta: "seed_post",
    },
    {
      id: "ws5",
      tone: "strategic",
      category: "platform_shift",
      pulse: "medium",
      chip: "Policy shift",
      headline: "Platform policy nudge — comment reach throttled",
      summary: "New distribution rules favor threads over quote-blasts. Micro-threads trending up.",
      region: "Platform wire",
      cta: "micro_thread",
    },
    {
      id: "ws6",
      tone: "humorous",
      category: "culture_spike",
      pulse: "medium",
      chip: "Beef spike",
      headline: "Creator beef crossover into reply-all territory",
      summary: "Public call-outs spiking — meme-level replies cooling things faster than essays.",
      region: "Drama pulse",
      cta: "meme_reply",
    },
    {
      id: "ws7",
      tone: "universal",
      category: "algo_pulse",
      pulse: "low",
      chip: "Signal flat",
      headline: "Low-signal day across most niches",
      summary: "Tiny signals matter more when reach is flat — one line beats silence or a nuke.",
      region: "World index",
      cta: "seed_post",
    },
    {
      id: "ws8",
      tone: "direct",
      category: "meltdown_index",
      pulse: "high",
      chip: "2am spike",
      headline: "Midnight crashout window — impulse posts peaking",
      summary: "Historical pattern: draft-folder saves peak between 1–4am local. Wait for morning-you.",
      region: "Time signal",
      cta: "draft_dont_delete",
    },
  ];

  let activeTone = null;
  let stripEl;

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
    const boosts = {
      humorous: ["meltdown_index", "culture_spike"],
      direct: ["crashout_risk", "meltdown_index"],
      strategic: ["algo_pulse", "platform_shift"],
      calm: ["turnaround_pulse"],
    };
    if ((boosts[tone] || []).includes(item.category)) score += 2;
    if (item.pulse === "high") score += 1;
    return score;
  }

  function sortByTone(items, tone) {
    if (!tone) return [...items];
    return [...items].sort((a, b) => scoreItem(b, tone) - scoreItem(a, tone));
  }

  function renderStrip(tone) {
    activeTone = tone || null;
    if (!stripEl) return;

    const items = sortByTone(WORLD_SIGNAL_ITEMS, activeTone).slice(0, 6);
    stripEl.innerHTML =
      items
        .map(
          (item) => `
        <button
          type="button"
          class="world-signal-chip world-signal-chip--${item.pulse}${activeTone && item.tone === activeTone ? " detected-tone" : ""}"
          data-signal-id="${item.id}"
          data-tone="${item.tone}"
          data-pulse="${item.pulse}"
          role="listitem"
        >
          <span class="world-signal-chip-dot" aria-hidden="true"></span>
          <span class="world-signal-chip-text">${escapeHtml(item.chip)}</span>
        </button>`
        )
        .join("") + (window.CrashoutMonetization?.renderPremiumSignalChip?.() || "");

    stripEl.classList.toggle("world-signals-track--tone-active", Boolean(activeTone));
    window.CrashoutSpikeAlert?.check?.();
    window.dispatchEvent(new CustomEvent("crashout:signals-refreshed"));
  }

  function focusSignal(signalId) {
    window.CrashoutTabbedFeed?.switchLane("signals");
    window.CrashoutTabbedFeed?.highlightLane("signals");

    window.setTimeout(() => {
      const proRow = document.querySelector(`[data-signal-id="${signalId}"]`);
      if (proRow) {
        proRow.classList.add("signals-list-item--highlight");
        proRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
        window.setTimeout(() => proRow.classList.remove("signals-list-item--highlight"), 1600);
        return;
      }

      const card = document.querySelector(`[data-id="${signalId}"]`);
      card?.classList.add("feed-item--highlight");
      card?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      window.setTimeout(() => card?.classList.remove("feed-item--highlight"), 1600);
    }, 120);
  }

  const PRO_STORAGE_KEY = "crashout_world_signals";

  const DEFAULT_PRO_DATA = {
    forecast: [
      "Drama cooling in 24h",
      "Burnout cluster forming in creator niche",
      "Spike surge expected in 48h",
      "Algorithm dip likely in 72h",
    ],
    burnout: [
      "Gaming creators: Elevated",
      "Lifestyle creators: Stable",
      "News creators: Rising",
    ],
    algoTip: "Post draft ideas instead of full posts during turbulence windows.",
  };

  function loadProData() {
    try {
      const raw = window.CrashoutUserStore
        ? window.CrashoutUserStore.get(PRO_STORAGE_KEY)
        : (() => {
            const item = localStorage.getItem(PRO_STORAGE_KEY);
            return item ? JSON.parse(item) : null;
          })();
      if (!raw) return { ...DEFAULT_PRO_DATA };
      return { ...DEFAULT_PRO_DATA, ...raw };
    } catch (_) {
      return { ...DEFAULT_PRO_DATA };
    }
  }

  function isProUnlocked() {
    return window.CrashoutMonetization?.isFeatureUnlocked?.("signals_dashboard") === true;
  }

  function buildTodaySignals() {
    return WORLD_SIGNAL_ITEMS.map((item) => ({
      id: item.id,
      text: `${item.chip} — ${SIGNAL_CATEGORIES[item.category] || item.category}`,
      detail: item.headline,
      pulse: item.pulse,
      tone: item.tone,
    }));
  }

  function renderSignalList(listEl, items, options = {}) {
    if (!listEl || !items?.length) {
      if (listEl) listEl.innerHTML = "";
      return;
    }
    const { locked = false, showDetail = false } = options;

    listEl.innerHTML = items
      .map((item) => {
        const text = typeof item === "string" ? item : item.text;
        const id = item.id ? ` data-signal-id="${item.id}"` : "";
        const pulse = item.pulse ? ` data-pulse="${item.pulse}"` : "";
        const detail =
          showDetail && item.detail && !locked
            ? `<span class="signals-list-detail">${escapeHtml(item.detail)}</span>`
            : locked && item.detail
              ? `<span class="signals-list-detail signals-list-detail--locked">Pro unlock</span>`
              : "";
        return `<li class="signals-list-item signal-row${pulse ? ` signals-list-item--${item.pulse}` : ""}"${id}${pulse}>
          <span class="signals-list-text">${escapeHtml(text)}</span>
          ${detail}
        </li>`;
      })
      .join("");
  }

  function renderProPanel() {
    const data = loadProData();
    const unlocked = isProUnlocked();
    const today = buildTodaySignals();

    const todayList = document.getElementById("signals-today-list");
    const forecastList = document.getElementById("signals-forecast-list");
    const burnoutList = document.getElementById("signals-burnout-list");
    const algoTip = document.getElementById("signals-algo-tip");
    const proExpand = document.getElementById("signals-pro-expand");
    const lockedEl = document.getElementById("signals-pro-locked");
    const panel = document.getElementById("signals-pro-panel");

    if (!panel) return;

    panel.classList.toggle("signals-pro-panel--locked", !unlocked);

    renderSignalList(todayList, today, { showDetail: true });

    if (proExpand) proExpand.hidden = !unlocked;
    if (lockedEl) lockedEl.hidden = unlocked;

    if (unlocked) {
      renderSignalList(forecastList, data.forecast);
      renderSignalList(burnoutList, data.burnout);
      if (algoTip) algoTip.textContent = data.algoTip;
    } else {
      if (forecastList) forecastList.innerHTML = "";
      if (burnoutList) burnoutList.innerHTML = "";
      if (algoTip) algoTip.textContent = "";
    }

    persistTodaySignals(today);
    window.CrashoutSpikeAlert?.check?.();
    window.dispatchEvent(new CustomEvent("crashout:signals-refreshed"));
  }

  function persistTodaySignals(today) {
    try {
      const existing = loadProData();
      const next = { ...existing, today };
      if (window.CrashoutUserStore) {
        window.CrashoutUserStore.set(PRO_STORAGE_KEY, next);
      } else {
        localStorage.setItem(PRO_STORAGE_KEY, JSON.stringify(next));
      }
    } catch (_) {
      /* ignore */
    }
  }

  function showProPanel() {
    const panel = document.getElementById("signals-pro-panel");
    if (!panel) return;
    panel.hidden = false;
    renderProPanel();
  }

  function hideProPanel() {
    const panel = document.getElementById("signals-pro-panel");
    if (!panel) return;
    panel.hidden = true;
  }

  function handleStripClick(e) {
    const chip = e.target.closest(".world-signal-chip");
    if (!chip?.dataset.signalId) return;

    const signalId = chip.dataset.signalId;
    const isHigh =
      chip.dataset.pulse === "high" ||
      chip.classList.contains("world-signal-chip--high");

    if (isHigh && window.CrashoutSpikeAlert?.jumpToSignals) {
      window.CrashoutSpikeAlert.jumpToSignals(signalId);
      return;
    }

    focusSignal(signalId);
  }

  function init() {
    stripEl = document.getElementById("world-signals-track");
    if (!stripEl) return;
    stripEl.addEventListener("click", handleStripClick);
    renderStrip(null);
    window.addEventListener("crashout:upgrade-preview", renderProPanel);
  }

  window.CrashoutWorldSignals = {
    ITEMS: WORLD_SIGNAL_ITEMS,
    CATEGORIES: SIGNAL_CATEGORIES,
    sortByTone,
    scoreItem,
    renderStrip,
    focusSignal,
    renderProPanel,
    showProPanel,
    hideProPanel,
    loadProData,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
