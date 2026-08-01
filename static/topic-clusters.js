/**
 * Topic clusters — GET /api/recommendations/topics
 * Neon Hologram “Creator Galaxy” planet cards
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
    const slug = escapeHtml(item.topic || item.id || "cluster");
    const title = escapeHtml(item.display_name || item.topic || "Topic");
    const desc = escapeHtml(
      item.description || `${item.count ?? 0} clips in this creator galaxy lane`
    );
    const sampleRows = Array.isArray(item.items)
      ? item.items
          .slice(0, 3)
          .map((i) => i.title || i.id)
          .filter(Boolean)
          .map((t) => `<div>${escapeHtml(t)}</div>`)
          .join("")
      : "";
    return `
      <article
        class="planet-card holo-card topic-card neon-card unified-card v16-showcase-card"
        data-cluster="${slug}"
        data-id="${escapeHtml(item.id || item.topic)}"
      >
        <div class="planet-ring" aria-hidden="true"></div>
        <div class="planet-core" aria-hidden="true"></div>
        <h2 class="planet-title neon-title title">${title}</h2>
        <p class="planet-desc">${desc}</p>
        <p class="planet-count muted">${escapeHtml(String(item.count ?? 0))} clips</p>
        <div class="content-block planet-samples">${sampleRows}</div>
      </article>`;
  }

  function bindPlanetGlow(root) {
    root.querySelectorAll(".planet-card").forEach((card) => {
      card.addEventListener("mouseenter", () => {
        card.style.boxShadow = "0 0 20px #00eaff, 0 0 40px #00eaff";
      });
      card.addEventListener("mouseleave", () => {
        card.style.boxShadow = "";
      });
    });
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
      bindPlanetGlow(root);
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load clusters.";
      }
    }
  }

  window.CrashoutTopicClusters = { mount, load };
})();
