/**
 * Monetization lanes — GET /api/monetization/lanes
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function load() {
    const res = await fetch("/api/monetization/lanes", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Lanes failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const errEl = document.getElementById("monetization-lanes-error");
    if (!root) return;
    try {
      const data = await load();
      const items = Array.isArray(data.items) ? data.items : [];
      root.innerHTML = items
        .map(
          (lane) => `
        <article class="creator-hub-card" data-lane-id="${escapeHtml(lane.id)}">
          <h3>${escapeHtml(lane.title || lane.id)}</h3>
          <p class="creator-hub-meta">${escapeHtml(lane.description || "")}</p>
        </article>`
        )
        .join("");
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
