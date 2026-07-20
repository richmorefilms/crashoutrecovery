/**
 * Creator Mode dashboard — seeds, tone trends, spikes, streak, last safe move.
 * Reads crashout_recovery + crashout_seeds; gates on Creator Mode tier.
 */
(function () {
  const SEEDS_KEY = "crashout_seeds";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  const SPIKE_HEIGHT = {
    low: 0.35,
    steady: 0.55,
    rising: 0.75,
    hot: 1,
  };

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function isUnlocked() {
    return window.CrashoutMonetization?.isFeatureUnlocked?.("creator_dashboard") === true;
  }

  function loadRecovery() {
    return window.CrashoutRecoveryStreak?.load?.() || {
      streak: 0,
      history: [],
      tones: [],
      wins: 0,
      lastSafeMove: null,
      lastSafeAt: null,
    };
  }

  function loadSeeds() {
    try {
      return JSON.parse(localStorage.getItem(SEEDS_KEY) || "[]");
    } catch (_) {
      return [];
    }
  }

  function formatWhen(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function renderToneDots(tones, locked) {
    const slots = Array.from({ length: 7 }, (_, i) => tones[i] || null);

    return slots
      .map((entry, i) => {
        if (!entry) {
          return `<span class="creator-tone-dot creator-tone-dot--empty" data-index="${i}" aria-hidden="true"></span>`;
        }
        const tone = entry.tone || entry;
        const label = locked ? "Locked" : tone;
        return `<span class="creator-tone-dot creator-tone-dot--${tone}${locked ? " creator-tone-dot--locked" : ""}" title="${escapeHtml(label)}" data-index="${i}" aria-label="${escapeHtml(label)} tone"></span>`;
      })
      .join("");
  }

  function renderSpikeBars(history, locked) {
    const slots = Array.from({ length: 7 }, (_, i) => history[i] || null);

    return slots
      .map((entry, i) => {
        if (!entry) {
          return `<div class="creator-spike-bar creator-spike-bar--empty" data-index="${i}" style="--spike-height:0.12"></div>`;
        }
        const level = entry.level || entry;
        const height = SPIKE_HEIGHT[level] || 0.35;
        return `<div class="creator-spike-bar creator-spike-bar--${level}${locked ? " creator-spike-bar--locked" : ""}" data-index="${i}" style="--spike-height:${height}" title="${locked ? "Unlock Creator Mode" : level}"></div>`;
      })
      .join("");
  }

  function renderSeeds(seeds, locked) {
    const list = document.getElementById("creator-seed-list");
    const empty = document.getElementById("creator-seeds-empty");
    if (!list) return;

    if (!seeds.length) {
      list.innerHTML = "";
      if (empty) empty.hidden = false;
      return;
    }

    if (empty) empty.hidden = true;

    list.innerHTML = seeds
      .map((item) => {
        const seed = typeof item === "string" ? item : item.seed;
        const when = typeof item === "object" ? formatWhen(item.savedAt) : "";
        const text = locked
          ? `${uiLabel("seed", "Draft idea")} saved — unlock to read`
          : escapeHtml(seed);
        return `
          <li class="creator-seed-item${locked ? " creator-seed-item--locked" : ""}">
            <p class="creator-seed-text">${text}</p>
            ${when && !locked ? `<span class="creator-seed-time">${escapeHtml(when)}</span>` : ""}
          </li>`;
      })
      .join("");
  }

  function render() {
    const dash = document.getElementById("creator-dashboard");
    if (!dash) return;

    const data = loadRecovery();
    const seeds = loadSeeds();
    const unlocked = isUnlocked();
    const locked = !unlocked;

    dash.classList.toggle("creator-dashboard--locked", locked);

    const lockedEl = document.getElementById("creator-dashboard-locked");
    const bodyEl = document.getElementById("creator-dashboard-body");
    if (lockedEl) lockedEl.hidden = unlocked;
    if (bodyEl) bodyEl.classList.toggle("creator-dashboard-body--dimmed", locked);

    const streakEl = document.getElementById("creator-streak-count");
    const winsEl = document.getElementById("creator-wins-count");
    const toneEl = document.getElementById("creator-tone-dots");
    const spikeEl = document.getElementById("creator-spike-bars");
    const lastSafeEl = document.getElementById("creator-last-safe-move");
    const lastSafeTimeEl = document.getElementById("creator-last-safe-time");

    if (streakEl) streakEl.textContent = String(data.streak || 0);
    if (winsEl) winsEl.textContent = `${data.wins || 0} win${data.wins === 1 ? "" : "s"}`;

    if (toneEl) toneEl.innerHTML = renderToneDots(data.tones || [], locked);
    if (spikeEl) spikeEl.innerHTML = renderSpikeBars(data.history || [], locked);

    renderSeeds(seeds, locked);

    if (lastSafeEl) {
      if (!data.lastSafeMove) {
        lastSafeEl.textContent = "None yet.";
      } else if (locked) {
        lastSafeEl.textContent = "Safe move recorded — unlock Creator Mode to view.";
      } else {
        lastSafeEl.textContent = data.lastSafeMove;
      }
    }

    if (lastSafeTimeEl) {
      const when = formatWhen(data.lastSafeAt);
      if (when && !locked) {
        lastSafeTimeEl.hidden = false;
        lastSafeTimeEl.textContent = when;
      } else {
        lastSafeTimeEl.hidden = true;
        lastSafeTimeEl.textContent = "";
      }
    }

    window.CrashoutMomentumScore?.render?.();
  }

  function show() {
    const dash = document.getElementById("creator-dashboard");
    if (!dash) return;
    dash.hidden = false;
    render();
  }

  function hide() {
    const dash = document.getElementById("creator-dashboard");
    if (!dash) return;
    dash.hidden = true;
  }

  function init() {
    window.addEventListener("crashout:recovery-win", render);
    window.addEventListener("crashout:recovery-spike", render);
    window.addEventListener("crashout:predictor-updated", render);
    window.addEventListener("crashout:upgrade-preview", render);
  }

  window.CrashoutCreatorDashboard = {
    render,
    show,
    hide,
    isUnlocked,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
