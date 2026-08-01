/**
 * Monetization lanes — GET /api/monetization/lanes
 * Neon Earnings Dashboard (cards + scoreboard meters)
 */
(function () {
  // Display-only scoreboard accents — API lanes stay the source of truth
  const LANE_SCOREBOARD = {
    ads: { amount: "LIVE", percent: 82, note: "Recovery-safe ad lane armed" },
    creator_payouts: { amount: "TRACK", percent: 64, note: "Payout path ready" },
    sponsorships: { amount: "SOON", percent: 28, note: "Brand-safe placements warming up" },
    premium_feed: { amount: "SOON", percent: 22, note: "Subscriber lane on deck" },
  };

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function scoreboardFor(lane) {
    const id = String(lane.id || "").toLowerCase();
    return (
      LANE_SCOREBOARD[id] || {
        amount: "—",
        percent: 40,
        note: lane.description || "Monetization lane",
      }
    );
  }

  function renderLaneCard(lane) {
    const board = scoreboardFor(lane);
    return `
      <article class="earn-card holo-card neon-card unified-card" data-lane-id="${escapeHtml(lane.id)}">
        <h2 class="earn-title neon-title">${escapeHtml(lane.title || lane.id)}</h2>
        <p class="earn-amount">${escapeHtml(board.amount)}</p>
        <p class="earn-desc">${escapeHtml(lane.description || "")}</p>
      </article>`;
  }

  function renderMeter(lane) {
    const board = scoreboardFor(lane);
    const pct = Math.max(0, Math.min(100, Number(board.percent) || 0));
    return `
      <article class="meter-card holo-card neon-card" data-meter-id="${escapeHtml(lane.id)}">
        <h3 class="meter-title">${escapeHtml(lane.title || lane.id)}</h3>
        <div class="meter-bar" style="--meter:${pct}">
          <div class="meter-fill" style="width:${pct}%"></div>
        </div>
        <p class="meter-meta">${pct}% · ${escapeHtml(board.note)}</p>
      </article>`;
  }

  async function load() {
    const res = await fetch("/api/monetization/lanes", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Lanes failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const metersRoot = document.getElementById("monetization-meters-root");
    const errEl = document.getElementById("monetization-lanes-error");
    if (!root) return;
    try {
      const data = await load();
      const items = Array.isArray(data.items) ? data.items : [];
      root.innerHTML = items.map(renderLaneCard).join("");
      if (metersRoot) {
        metersRoot.innerHTML = items.map(renderMeter).join("");
      }
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load lanes.";
      }
    }
  }

  window.CrashoutMonetizationLanes = { mount, load };
})();
