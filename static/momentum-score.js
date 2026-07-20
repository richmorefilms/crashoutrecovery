/**
 * Momentum Score — heuristic recovery momentum (0–100).
 * Reads recovery history, saved drafts, and world signals.
 * UI scaffolding only; localStorage-backed.
 */
(function () {
  const SEEDS_KEY = "crashout_seeds";

  function getTier() {
    return (
      window.CrashoutMonetization?.getTier?.() ||
      window.CrashoutMonetization?.activeTier?.() ||
      "basic"
    );
  }

  function loadRecovery() {
    return (
      window.CrashoutRecoveryStreak?.load?.() || {
        streak: 0,
        history: [],
        tones: [],
        wins: 0,
        lastSafeMove: null,
        lastSafeAt: null,
      }
    );
  }

  function loadSeedCount() {
    try {
      const seeds = JSON.parse(localStorage.getItem(SEEDS_KEY) || "[]");
      return Array.isArray(seeds) ? seeds.length : 0;
    } catch (_) {
      return 0;
    }
  }

  function hasHighSignalToday() {
    const items = window.CrashoutWorldSignals?.ITEMS || [];
    return items.some((item) => item.pulse === "high");
  }

  function scoreSpikeStability(history) {
    let total = 0;
    (history || []).forEach((entry) => {
      const level = entry.level || entry;
      switch (level) {
        case "low":
          total += 2;
          break;
        case "rising":
          total -= 1;
          break;
        case "hot":
          total -= 3;
          break;
        default:
          break;
      }
    });
    return total;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function compute() {
    const recovery = loadRecovery();
    let score = 0;

    score += Math.min((recovery.streak || 0) * 4, 40);

    if (recovery.lastSafeMove) {
      score += 20;
    }

    score += Math.min(loadSeedCount() * 2, 20);

    score += scoreSpikeStability(recovery.history);

    if (getTier() === "pro" && !hasHighSignalToday()) {
      score += 10;
    }

    return clamp(Math.round(score), 0, 100);
  }

  function levelFor(score) {
    if (score >= 70) return "high";
    if (score >= 40) return "medium";
    return "low";
  }

  function describe(score) {
    const level = levelFor(score);

    if (level === "high") {
      return "Your progress is strong — creator habits are stabilizing.";
    }
    if (level === "medium") {
      return "Your progress is building — stay consistent.";
    }
    return "Your progress is low — keep taking safe moves.";
  }

  function render() {
    const scoreEl = document.getElementById("creator-momentum-score");
    const descEl = document.getElementById("creator-momentum-desc");
    if (!scoreEl || !descEl) return;

    const score = compute();
    const level = levelFor(score);

    scoreEl.textContent = String(score);
    scoreEl.className = `momentum-score ${level}`;
    descEl.textContent = describe(score);
    descEl.className = `momentum-desc ${level}`;
  }

  function init() {
    render();
    window.addEventListener("crashout:recovery-win", render);
    window.addEventListener("crashout:recovery-spike", render);
    window.addEventListener("crashout:upgrade-preview", render);
  }

  window.CrashoutMomentumScore = {
    compute,
    describe,
    levelFor,
    render,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
