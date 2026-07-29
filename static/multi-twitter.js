/**
 * Multi-platform twitter — GET /api/multi/twitter
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

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recovery clip");
    const channel = escapeHtml(item.channel || "");
    return `
      <article class="unified-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        <div class="unified-card-placeholder" aria-hidden="true"></div>
        <div class="unified-card-body">
          <div class="unified-card-badges">
            <span class="platform-badge platform-badge--twitter">twitter</span>
            <span class="norm-badge">${escapeHtml(uiLabel("badge_normalized", "Normalized"))}</span>
          </div>
          <h3 class="unified-card-title">${title}</h3>
          ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
        </div>
      </article>`;
  }

  async function load() {
    const res = await fetch("/api/multi/twitter", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Twitter feed failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("multi-twitter-empty");
    const errEl = document.getElementById("multi-twitter-error");
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
      root.innerHTML = items.map((item, i) => renderCard(item, i)).join("");
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load Twitter.";
      }
    }
  }

  window.CrashoutMultiTwitter = { mount, load };
})();
