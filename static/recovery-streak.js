/**
 * Recovery streak + spike history — localStorage retention engine.
 * Pro unlocks full spike history graph + tone trend via CrashoutMonetization.
 */
(function () {
  const STORAGE_KEY = "crashout_recovery";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiLower = (key, fallback) => window.CrashoutUICopy?.labelLower?.(key) || fallback;

  const TONE_COLORS = {
    humorous: "humorous",
    direct: "direct",
    strategic: "strategic",
    calm: "calm",
    universal: "universal",
  };

  const SPIKE_HEIGHT = {
    low: 0.35,
    steady: 0.55,
    rising: 0.75,
    hot: 1,
  };

  const defaultData = () => ({
    streak: 0,
    lastWinDate: null,
    history: [],
    tones: [],
    wins: 0,
    lastSafeMove: null,
    lastSafeAt: null,
  });

  function todayKey() {
    return new Date().toISOString().slice(0, 10);
  }

  function load() {
    try {
      if (window.CrashoutUserStore) {
        const stored = window.CrashoutUserStore.get(STORAGE_KEY);
        if (stored && typeof stored === "object") return { ...defaultData(), ...stored };
      }
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultData();
      return { ...defaultData(), ...JSON.parse(raw) };
    } catch (_) {
      return defaultData();
    }
  }

  function save(data) {
    try {
      if (window.CrashoutUserStore) {
        window.CrashoutUserStore.set(STORAGE_KEY, data);
        return true;
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      return true;
    } catch (_) {
      return false;
    }
  }

  function isProUnlocked() {
    return (
      window.CrashoutMonetization?.isFeatureUnlocked?.("recovery_streaks") === true &&
      window.CrashoutMonetization?.isFeatureUnlocked?.("spike_history") === true
    );
  }

  function toneToSpikeLevel(tone) {
    switch (tone) {
      case "direct":
        return "hot";
      case "humorous":
      case "strategic":
        return "rising";
      case "calm":
        return "steady";
      default:
        return "low";
    }
  }

  function recordWin(reason) {
    const data = load();
    const today = todayKey();

    data.wins += 1;

    if (data.lastWinDate !== today) {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayKey = yesterday.toISOString().slice(0, 10);

      if (data.lastWinDate === yesterdayKey) {
        data.streak += 1;
      } else if (!data.lastWinDate) {
        data.streak = 1;
      } else {
        data.streak = 1;
      }

      data.lastWinDate = today;
    }

    save(data);
    render();
    showToast(
      reason === "safe_move"
        ? `Safe move taken — ${uiLower("recovery_streak", "win streak")} holds.`
        : data.lastWinDate === today && data.wins > 1
          ? "Draft saved — streak holds."
          : `Draft saved — ${uiLower("recovery_streak", "win streak")} +1`
    );

    window.dispatchEvent(
      new CustomEvent("crashout:recovery-win", { detail: { reason, streak: data.streak } })
    );

    return data;
  }

  function bumpStreak(reason = "draft_saved") {
    return recordWin(reason);
  }

  function addSpike(level, tone) {
    const data = load();
    const entry = {
      level: level || "low",
      tone: tone || "universal",
      at: new Date().toISOString(),
    };

    data.history.push(entry);
    if (data.history.length > 7) data.history = data.history.slice(-7);

    data.tones.push({ tone: entry.tone, at: entry.at });
    if (data.tones.length > 7) data.tones = data.tones.slice(-7);

    save(data);
    render();

    window.dispatchEvent(
      new CustomEvent("crashout:recovery-spike", { detail: { entry, history: data.history } })
    );

    return data;
  }

  function trackFromPipeline({ tone, spikeLevel }) {
    const level = spikeLevel || toneToSpikeLevel(tone);
    return addSpike(level, tone);
  }

  function showToast(message) {
    let toast = document.getElementById("recovery-toast");
    if (!toast) {
      toast = document.createElement("p");
      toast.id = "recovery-toast";
      toast.className = "recovery-toast";
      toast.setAttribute("role", "status");
      document.querySelector(".feed-shell")?.appendChild(toast);
    }

    toast.hidden = false;
    toast.textContent = message;
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      toast.hidden = true;
    }, 2800);
  }

  function renderToneTrend(tones, locked) {
    const slots = Array.from({ length: 7 }, (_, i) => tones[i] || null);

    return `
      <div class="recovery-tone-trend" aria-label="Tone trend last 7 inputs">
        <span class="recovery-trend-label">Tone trend</span>
        <div class="recovery-tone-dots">
          ${slots
            .map((entry, i) => {
              if (!entry) {
                return `<span class="recovery-tone-dot recovery-tone-dot--empty" data-index="${i}" aria-hidden="true"></span>`;
              }
              const tone = entry.tone || "universal";
              const label = locked ? "?" : tone;
              return `<span class="recovery-tone-dot recovery-tone-dot--${TONE_COLORS[tone] || "universal"}${locked ? " recovery-tone-dot--locked" : ""}" title="${label}" data-index="${i}" aria-label="${locked ? "Locked tone" : `${tone} tone`}"></span>`;
            })
            .join("")}
        </div>
      </div>`;
  }

  function renderSpikeBars(history, locked) {
    const slots = Array.from({ length: 7 }, (_, i) => history[i] || null);

    return slots
      .map((entry, i) => {
        if (!entry) {
          return `<div class="spike-bar spike-bar--empty" data-index="${i}" style="--spike-height:0.12"></div>`;
        }

        const level = entry.level || "low";
        const height = SPIKE_HEIGHT[level] || 0.35;
        const lockedClass = locked ? " spike-bar--locked" : "";

        return `<div class="spike-bar spike-bar--${level}${lockedClass}" data-index="${i}" style="--spike-height:${height}" title="${locked ? "Pro unlock" : level}"></div>`;
      })
      .join("");
  }

  function render() {
    const card = document.getElementById("recovery-week-card");
    const streakEl = document.getElementById("recovery-streak-count");
    const graphEl = document.getElementById("spike-history-graph");
    const trendEl = document.getElementById("recovery-tone-trend-slot");
    const noteEl = document.getElementById("recovery-week-note");

    if (!card) return;

    const data = load();
    const pro = isProUnlocked();
    const postsActive = document
      .getElementById("feed-lane-panel")
      ?.classList.contains("feed-lane-panel--posts");

    if (!postsActive) {
      card.hidden = true;
      return;
    }

    card.hidden = false;
    card.classList.toggle("recovery-week-card--locked", !pro);

    if (streakEl) streakEl.textContent = String(data.streak);

    if (graphEl) {
      graphEl.innerHTML = renderSpikeBars(data.history, !pro);
      graphEl.setAttribute("aria-label", pro ? "Spike history last 7 inputs" : "Spike history locked");
    }

    if (trendEl) {
      trendEl.innerHTML = renderToneTrend(data.tones, !pro);
    }

    if (noteEl) {
      noteEl.textContent = pro
        ? `Drafts saved, safe moves taken, and tone shifts build your ${uiLower("recovery_streak", "win streak")}.`
        : `Your ${uiLower("recovery_streak", "win streak")} is live. Unlock Pro for full spike history + tone trend.`;
    }

    const upgradeSlot = document.getElementById("recovery-week-upgrade");
    if (upgradeSlot) {
      upgradeSlot.hidden = pro;
      upgradeSlot.innerHTML = pro
        ? ""
        : `<button type="button" class="recovery-week-upgrade-btn" data-monetization-action="upgrade" data-tier="pro">Unlock spike history</button>`;
    }
  }

  function showInPostsLane(show) {
    const card = document.getElementById("recovery-week-card");
    if (!card) return;

    if (!show) {
      card.hidden = true;
      return;
    }

    render();
  }

  function setLastSafeMove(text) {
    const data = load();
    data.lastSafeMove = text || null;
    data.lastSafeAt = text ? new Date().toISOString() : null;
    save(data);
    render();
    window.CrashoutCreatorDashboard?.render?.();
    window.dispatchEvent(new CustomEvent("crashout:recovery-updated", { detail: { lastSafeMove: text } }));
    return data;
  }

  function refresh() {
    render();
  }

  function init() {
    window.addEventListener("crashout:predictor-updated", (e) => {
      const analysis = e.detail?.analysis;
      if (!analysis) return;
      trackFromPipeline({ tone: analysis.tone, spikeLevel: analysis.spikeLevel });
    });

    window.addEventListener("crashout:upgrade-preview", refresh);
    window.addEventListener("crashout:recovery-spike", () => {
      if (document.getElementById("feed-lane-panel")?.classList.contains("feed-lane-panel--posts")) {
        render();
      }
    });

    render();
  }

  window.CrashoutRecoveryStreak = {
    load,
    save,
    bumpStreak,
    addSpike,
    trackFromPipeline,
    recordWin,
    setLastSafeMove,
    render,
    refresh,
    showInPostsLane,
    showToast,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
