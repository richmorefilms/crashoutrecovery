/**
 * Growth opportunities — GET /api/growth/{creator_id}/opportunities
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
    const main = document.querySelector(".feed-page--growth-opportunities");
    const fromData = main?.getAttribute("data-creator-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("creator_id") || "";
  }

  function renderOpp(item) {
    const values = Array.isArray(item.values)
      ? item.values
          .map((v) => (typeof v === "string" ? v : v.topic || v.platform || JSON.stringify(v)))
          .slice(0, 4)
          .join(", ")
      : "";
    return `
      <article class="v16-showcase-card neon-card unified-card" data-id="${escapeHtml(item.id)}">
        <h3 class="neon-title title">${escapeHtml(item.title || item.kind || "Opportunity")}</h3>
        <p class="muted">${escapeHtml(values)}</p>
      </article>`;
  }

  async function load(creatorId) {
    const res = await fetch(
      `/api/growth/${encodeURIComponent(creatorId)}/opportunities`,
      { credentials: "same-origin" }
    );
    if (!res.ok) throw new Error(`Opportunities failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("growth-opportunities-empty");
    const errEl = document.getElementById("growth-opportunities-error");
    if (!root) return;
    const creatorId = resolveCreatorId();
    if (!creatorId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=creatorId for opportunities.";
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
      root.innerHTML = items.map(renderOpp).join("");
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load opportunities.";
      }
    }
  }

  window.CrashoutGrowthOpportunities = { mount, load, resolveCreatorId };
})();
