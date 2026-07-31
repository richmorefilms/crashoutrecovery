/**
 * Growth trends — GET /api/growth/{creator_id}/trends + chart
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function resolveCreatorId() {
    const main = document.querySelector(".feed-page--growth-trends");
    const fromData = main?.getAttribute("data-creator-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("creator_id") || "";
  }

  function renderDay(item) {
    return `
      <article class="unified-card neon-card" data-id="${escapeHtml(item.id)}">
        <div class="unified-card-body">
          <h3 class="unified-card-title title neon-title">${escapeHtml(item.date || "")}</h3>
          <p class="unified-card-channel">Views ${escapeHtml(String(item.views ?? 0))} · Likes ${escapeHtml(String(item.likes ?? 0))}</p>
          <p class="unified-card-score">Earnings ${escapeHtml(String(item.earnings ?? 0))} · Recs ${escapeHtml(String(item.recommendations_served ?? 0))}</p>
        </div>
      </article>`;
  }

  function renderChart(items) {
    const chart = document.getElementById("growth-trends-chart");
    if (!chart) return;
    const slice = items.slice(-14);
    const max = Math.max(...slice.map((d) => Number(d.views) || 0), 1);
    chart.innerHTML = slice
      .map((d) => {
        const h = Math.round(((Number(d.views) || 0) / max) * 100);
        return `<span class="v16-chart-bar" style="height:${Math.max(8, h)}%"></span>`;
      })
      .join("");
  }

  async function load(creatorId) {
    const res = await fetch(`/api/growth/${encodeURIComponent(creatorId)}/trends`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Growth trends failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("growth-trends-empty");
    const errEl = document.getElementById("growth-trends-error");
    if (!root) return;
    const creatorId = resolveCreatorId();
    if (!creatorId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=creatorId for growth trends.";
      }
      return;
    }
    try {
      const data = await load(creatorId);
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;
      renderChart(items);
      root.innerHTML = items.slice(-7).map(renderDay).join("");
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load growth trends.";
      }
    }
  }

  window.CrashoutGrowthTrends = { mount, load, resolveCreatorId };
})();
