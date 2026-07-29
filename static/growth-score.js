/**
 * Growth score dial — GET /api/growth/{creator_id}/score
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
    const main = document.querySelector(".feed-page--growth-score");
    const fromData = main?.getAttribute("data-creator-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("creator_id") || "";
  }

  async function load(creatorId) {
    const res = await fetch(`/api/growth/${encodeURIComponent(creatorId)}/score`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Growth score failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("growth-score-empty");
    const errEl = document.getElementById("growth-score-error");
    if (!root) return;
    const creatorId = resolveCreatorId();
    if (!creatorId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=creatorId for growth score.";
      }
      return;
    }
    try {
      const data = await load(creatorId);
      const item = (data.items || [])[0];
      if (!item) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;
      const score = Number(item.growth_score ?? data.meta?.growth_score ?? 0);
      const comps = item.components || {};
      root.innerHTML = `
        <section class="console-panel">
          <div class="v16-dial" style="--score:${Math.max(0, Math.min(100, score))}">
            <div class="v16-dial-inner">
              <span class="v16-dial-value">${escapeHtml(String(score))}</span>
              <span class="v16-dial-label">Score</span>
            </div>
          </div>
        </section>
        <section class="console-panel">
          <h3>Components</h3>
          <ul class="youtube-detail-stats">
            <li>History: ${escapeHtml(String(comps.history ?? "—"))}</li>
            <li>Earnings: ${escapeHtml(String(comps.earnings ?? "—"))}</li>
            <li>Engagement: ${escapeHtml(String(comps.engagement ?? "—"))}</li>
            <li>Recommendations: ${escapeHtml(String(comps.recommendations ?? "—"))}</li>
          </ul>
          <p class="creator-hub-meta">Creator ${escapeHtml(String(item.creator_id || creatorId))}</p>
        </section>`;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load growth score.";
      }
    }
  }

  window.CrashoutGrowthScore = { mount, load, resolveCreatorId };
})();
