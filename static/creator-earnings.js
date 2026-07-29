/**
 * Creator earnings — GET /api/creator/{id}/earnings + chart bars
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
    const main = document.querySelector(".monetization-page");
    const fromData = main?.getAttribute("data-creator-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("creator_id") || "";
  }

  function renderChart(total) {
    const chart = document.getElementById("creator-earnings-chart");
    if (!chart) return;
    const base = Math.max(0.01, Number(total) || 0.05);
    const bars = Array.from({ length: 14 }, (_, i) => {
      const h = 18 + ((Math.sin(i * 0.7) + 1) * 35) + (base * 10 * ((i % 5) + 1));
      return `<span class="v16-chart-bar" style="height:${Math.min(100, h)}%"></span>`;
    });
    chart.innerHTML = bars.join("");
  }

  async function load(creatorId) {
    const res = await fetch(`/api/creator/${encodeURIComponent(creatorId)}/earnings`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Earnings failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const errEl = document.getElementById("creator-earnings-error");
    if (!root) return;
    const creatorId = resolveCreatorId();
    if (!creatorId) {
      root.innerHTML = `<p class="creator-hub-note">Open with ?id=yourUserId to see earnings.</p>`;
      return;
    }
    try {
      const data = await load(creatorId);
      const item = (data.items && data.items[0]) || data.meta || {};
      root.innerHTML = `
        <article class="creator-hub-card unified-card">
          <div class="unified-card-body">
            <ul class="youtube-detail-stats">
              <li>Total earnings: $${escapeHtml(String(item.total_earnings ?? 0))}</li>
              <li>Clicks: ${escapeHtml(String(item.clicks ?? 0))}</li>
              <li>RPM: ${escapeHtml(String(item.rpm ?? 0))}</li>
              <li>Last payout: ${escapeHtml(String(item.last_payout || "—"))}</li>
            </ul>
          </div>
        </article>`;
      renderChart(item.total_earnings ?? 0);
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load earnings.";
      }
    }
  }

  window.CrashoutCreatorEarnings = { mount, load };
})();
