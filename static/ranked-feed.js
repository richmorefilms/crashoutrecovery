/**
 * Ranked feed — GET /api/feed/all?ranked=true
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
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const score =
      item.engagement_score != null ? Number(item.engagement_score).toFixed(1) : "—";
    const platform = String(item.platform || "unknown").toLowerCase();
    const media = thumb
      ? `<img class="unified-card-thumb thumbnail neon-border" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;
    return `
      <article class="unified-card neon-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        ${media}
        <div class="unified-card-body">
          <span class="platform-badge platform-badge--${escapeHtml(platform)}">${escapeHtml(platform)}</span>
          <h3 class="unified-card-title title neon-title">${title}</h3>
          ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
          <p class="unified-card-score">Score ${escapeHtml(String(score))}</p>
        </div>
      </article>`;
  }

  async function load() {
    const res = await fetch("/api/feed/all?ranked=true", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Ranked feed failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("ranked-feed-empty");
    const errEl = document.getElementById("ranked-feed-error");
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
      root.innerHTML = items.map((item, i) => renderCard(item, i)).join("");
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load ranked feed.";
      }
    }
  }

  window.CrashoutRankedFeed = { mount, load };
})();
