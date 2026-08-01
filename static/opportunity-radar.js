/**
 * Neon Opportunity Radar — GET /api/recommendations/topics
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function strength(count) {
    const n = Number(count) || 0;
    return Math.max(18, Math.min(100, Math.round(28 + n * 8)));
  }

  function renderCard(item) {
    const title = escapeHtml(item.display_name || item.topic || "Topic");
    const pct = strength(item.count);
    return `
      <article class="holo-card radar-card" style="--opp:${pct}" data-topic="${escapeHtml(item.topic || "")}">
        <div class="radar-card-ring" aria-hidden="true"></div>
        <h3 class="neon-title">${title}</h3>
        <p class="expand-sub">${escapeHtml(item.description || `${item.count || 0} signals`)}</p>
        <p class="radar-strength">${pct}% ${escapeHtml(uiLabel("radar_opportunity", "opportunity"))}</p>
        <a class="launch-btn launch-btn--launch" href="/publish">${escapeHtml(uiLabel("radar_add_launchpad", "Add to Launchpad"))}</a>
      </article>`;
  }

  async function mount() {
    const root = document.getElementById("radar-results-root");
    const status = document.getElementById("radar-status");
    const errEl = document.getElementById("radar-error");
    if (!root) return;
    try {
      const res = await fetch("/api/recommendations/topics", { credentials: "same-origin" });
      if (!res.ok) throw new Error(`Radar failed (${res.status})`);
      const data = await res.json();
      const items = (Array.isArray(data.items) ? data.items : []).slice(0, 8);
      root.innerHTML = items.map(renderCard).join("");
      if (status) status.textContent = uiLabel("radar_ready", "Scan complete — rising lanes locked");
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Radar offline.";
      }
    }
  }

  window.CrashoutOpportunityRadar = { mount };
})();
