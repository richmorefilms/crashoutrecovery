/**
 * Topic graph — GET /api/recommendations/graph
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderNode(item) {
    const neighbors = item.neighbors || {};
    const chips = Object.entries(neighbors)
      .slice(0, 8)
      .map(
        ([name, strength]) =>
          `<span class="topic-edge-chip">${escapeHtml(name)} · ${escapeHtml(String(strength))}</span>`
      )
      .join("");
    return `
      <article class="topic-graph-node" data-id="${escapeHtml(item.id)}">
        <h3>${escapeHtml(item.id)}</h3>
        <div class="topic-graph-edges">${chips || "<span class='creator-hub-meta'>No edges</span>"}</div>
      </article>`;
  }

  async function load() {
    const res = await fetch("/api/recommendations/graph", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Graph failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("topic-graph-empty");
    const errEl = document.getElementById("topic-graph-error");
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
      root.innerHTML = items.map(renderNode).join("");
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load graph.";
      }
    }
  }

  window.CrashoutTopicGraph = { mount, load };
})();
