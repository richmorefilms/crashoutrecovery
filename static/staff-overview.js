/**
 * Staff overview — GET /api/staff/overview + health chart / panels
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function authHeaders() {
    try {
      const token = localStorage.getItem("crashout_access_token");
      if (token) return { Authorization: `Bearer ${token}` };
    } catch (_) {
      /* ignore */
    }
    return {};
  }

  function renderChart(item) {
    const chart = document.getElementById("staff-health-chart");
    if (!chart) return;
    const vals = [
      item.total_creators || 1,
      item.total_items || 1,
      item.total_ads_served || 1,
      item.recommendation_volume || 1,
      item.ranking_latency_ms || 1,
      item.active_flags || 1,
    ];
    const max = Math.max(...vals, 1);
    chart.innerHTML = vals
      .map((v) => `<span class="v16-chart-bar" style="height:${Math.round((v / max) * 100)}%"></span>`)
      .join("");
  }

  async function load() {
    const res = await fetch("/api/staff/overview", {
      credentials: "same-origin",
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`Staff overview failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("staff-overview-empty");
    const errEl = document.getElementById("staff-overview-error");
    const fraud = document.getElementById("staff-fraud-panel");
    const rate = document.getElementById("staff-rate-panel");
    if (!root) return;
    try {
      const data = await load();
      const item = (data.items || [])[0] || data.meta || {};
      if (!item || !Object.keys(item).length) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;
      root.innerHTML = `
        <article class="unified-card">
          <div class="unified-card-body">
            <h3 class="unified-card-title">Platform health</h3>
            <p class="unified-card-channel">Creators ${escapeHtml(String(item.total_creators ?? 0))} · Items ${escapeHtml(String(item.total_items ?? 0))}</p>
            <p class="unified-card-score">Ads ${escapeHtml(String(item.total_ads_served ?? 0))} · Recs ${escapeHtml(String(item.recommendation_volume ?? 0))} · Latency ${escapeHtml(String(item.ranking_latency_ms ?? "—"))}ms</p>
          </div>
        </article>`;
      renderChart(item);
      if (fraud) {
        fraud.innerHTML = `<p class="creator-hub-meta">Active flags: ${escapeHtml(String(item.active_flags ?? 0))}. Fraud signals stored in fraud_signals (v15).</p>`;
      }
      if (rate) {
        rate.innerHTML = `<p class="creator-hub-meta">Endpoint rate limits: 120 / 60s window via endpoint_rate_limits.</p>`;
      }
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load staff overview (staff login required).";
      }
    }
  }

  window.CrashoutStaffOverview = { mount, load };
})();
