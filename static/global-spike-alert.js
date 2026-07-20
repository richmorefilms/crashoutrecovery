/**
 * Global Spike Alert — pulse strip flash + Signals lane jump on high spikes.
 * Reads crashout_world_signals.today (fallback: live World Signals items).
 * UI scaffolding only; no backend.
 */
(function () {
  const STORAGE_KEY = "crashout_world_signals";
  const FLASH_MS = 1500;

  function getTier() {
    return (
      window.CrashoutMonetization?.getTier?.() ||
      window.CrashoutMonetization?.activeTier?.() ||
      "basic"
    );
  }

  function isProUser() {
    return (
      getTier() === "pro" ||
      window.CrashoutMonetization?.isFeatureUnlocked?.("signals_dashboard") === true
    );
  }

  function itemIsHigh(item) {
    if (!item) return false;
    if (typeof item === "string") {
      return item.toLowerCase().includes("high");
    }
    if (item.pulse === "high") return true;
    const text = `${item.text || ""} ${item.chip || ""} ${item.headline || ""}`.toLowerCase();
    return text.includes("high");
  }

  function loadTodaySignals() {
    try {
      const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (raw?.today?.length) return raw.today;
    } catch (_) {
      /* ignore */
    }

    const items = window.CrashoutWorldSignals?.ITEMS || [];
    const categories = window.CrashoutWorldSignals?.CATEGORIES || {};
    return items.map((item) => ({
      id: item.id,
      pulse: item.pulse,
      chip: item.chip,
      text: `${item.chip} — ${categories[item.category] || item.category}`,
      headline: item.headline,
    }));
  }

  function hasHighAlert(signals) {
    return (signals || []).some(itemIsHigh);
  }

  function retriggerAnimation(el, className) {
    if (!el) return;
    el.classList.remove(className);
    void el.offsetWidth;
    el.classList.add(className);
  }

  function applyFlash() {
    const strip = document.getElementById("world-signals-track");
    const bar = document.getElementById("world-signals-bar");

    if (strip) {
      strip.classList.add("pulse-alert-global");
      retriggerAnimation(strip, "pulse-alert-global");
    }
    if (bar) {
      bar.classList.add("pulse-alert-global");
      retriggerAnimation(bar, "pulse-alert-global");
    }

    document.querySelectorAll(".world-signal-chip").forEach((chip) => {
      const pulse = chip.dataset.pulse;
      const isHigh =
        pulse === "high" || chip.classList.contains("world-signal-chip--high");
      if (isHigh) {
        chip.classList.add("pulse-alert");
        retriggerAnimation(chip, "pulse-alert");
      }
    });
  }

  function clearFlash() {
    document.getElementById("world-signals-track")?.classList.remove("pulse-alert-global");
    document.getElementById("world-signals-bar")?.classList.remove("pulse-alert-global");
    document.querySelectorAll(".world-signal-chip.pulse-alert").forEach((chip) => {
      chip.classList.remove("pulse-alert");
    });
  }

  let lastHighActive = false;

  function emitSpikeAlert(source) {
    window.dispatchEvent(
      new CustomEvent("crashout:spike-alert", { detail: { source: source || "world" } })
    );
  }

  function check() {
    const today = loadTodaySignals();
    const active = hasHighAlert(today);
    if (active) {
      applyFlash();
      if (!lastHighActive) emitSpikeAlert("check");
    } else {
      clearFlash();
    }
    lastHighActive = active;
    return active;
  }

  function flashRow(el) {
    if (!el) return;
    el.classList.add("signal-row-alert");
    retriggerAnimation(el, "signal-row-alert");
    window.setTimeout(() => el.classList.remove("signal-row-alert"), FLASH_MS);
  }

  function highlightRow(signalId) {
    const row = document.querySelector(
      `#signals-today-list .signal-row[data-signal-id="${signalId}"]`
    );
    if (row) {
      row.scrollIntoView({ behavior: "smooth", block: "nearest" });
      flashRow(row);
    }

    if (isProUser()) {
      document.querySelectorAll("#signals-forecast-list .signal-row").forEach((li) => {
        const text = (li.textContent || "").toLowerCase();
        if (text.includes("high") || text.includes("spike") || text.includes("surge")) {
          flashRow(li);
        }
      });
    }
  }

  function jumpToSignals(signalId) {
    window.CrashoutTabbedFeed?.switchLane("signals");
    window.CrashoutTabbedFeed?.highlightLane("signals");
    emitSpikeAlert("jump");

    window.setTimeout(() => {
      window.CrashoutWorldSignals?.showProPanel?.();
      window.CrashoutWorldSignals?.renderProPanel?.();
      highlightRow(signalId);

      const row = document.querySelector(
        `#signals-today-list .signal-row[data-signal-id="${signalId}"]`
      );
      if (!row) {
        const card = document.querySelector(`[data-id="${signalId}"]`);
        if (card) {
          card.classList.add("feed-item--highlight");
          card.scrollIntoView({ behavior: "smooth", block: "nearest" });
          window.setTimeout(() => card.classList.remove("feed-item--highlight"), FLASH_MS);
        }
      }
    }, 140);
  }

  function init() {
    check();
    window.addEventListener("crashout:signals-refreshed", check);
    window.addEventListener("crashout:upgrade-preview", check);
  }

  window.CrashoutSpikeAlert = {
    check,
    applyFlash,
    clearFlash,
    highlightRow,
    jumpToSignals,
    itemIsHigh,
    loadTodaySignals,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
