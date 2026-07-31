/**
 * Topic clusters — GET /api/recommendations/topics
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderCluster(item) {
    const sampleRows = Array.isArray(item.items)
      ? item.items
          .slice(0, 3)
          .map((i) => i.title || i.id)
          .filter(Boolean)
          .map((title) => `<div>${escapeHtml(title)}</div>`)
          .join("")
      : "";
    return `
      <article class="v16-showcase-card topic-card neon-card unified-card" data-id="${escapeHtml(item.id || item.topic)}">
        <h3 class="neon-title title">${escapeHtml(item.topic || "topic")}</h3>
        <p class="muted">${escapeHtml(String(item.count ?? 0))} clips</p>
        <div class="content-block">${sampleRows}</div>
      </article>`;
  }

  async function load() {
    const res = await fetch("/api/recommendations/topics", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Topics failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("topic-clusters-empty");
    const errEl = document.getElementById("topic-clusters-error");
    if (!root) return;
    try {
      const data = await load();
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;
      root.innerHTML = items.map(renderCluster).join("");
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load clusters.";
      }
    }
  }

  window.CrashoutTopicClusters = { mount, load };
})();
