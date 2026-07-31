/**
 * YouTube search — GET /api/youtube/search?q=...
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "YouTube video");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const href = item.id ? `/youtube/video/${encodeURIComponent(item.id)}` : "#";
    const media = thumb
      ? `<img class="unified-card-thumb thumbnail neon-border" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;

    return `
      <article class="unified-card neon-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        <a class="unified-card-link" href="${href}">
          ${media}
          <div class="unified-card-body">
            <span class="platform-badge platform-badge--youtube">YouTube</span>
            <h3 class="unified-card-title title neon-title">${title}</h3>
            ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
          </div>
        </a>
      </article>`;
  }

  async function load(query) {
    const params = new URLSearchParams({ q: query });
    const res = await fetch(`/api/youtube/search?${params.toString()}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Search failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("youtube-search-empty");
    const errEl = document.getElementById("youtube-search-error");
    const input = document.getElementById("youtube-search-q");
    const form = document.getElementById("youtube-search-form");
    if (!root) return;

    async function runSearch(q) {
      if (errEl) errEl.hidden = true;
      if (!q) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      try {
        const data = await load(q);
        const items = Array.isArray(data.items) ? data.items : [];
        if (!items.length) {
          root.innerHTML = "";
          if (empty) empty.hidden = false;
          return;
        }
        if (empty) empty.hidden = true;
        root.innerHTML = items.map((item, i) => renderCard(item, i)).join("");
      } catch (err) {
        root.innerHTML = "";
        if (errEl) {
          errEl.hidden = false;
          errEl.textContent = err.message || "Search failed.";
        }
      }
    }

    form?.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const q = (input?.value || "").trim();
      const url = new URL(window.location.href);
      url.searchParams.set("q", q);
      window.history.replaceState({}, "", url);
      runSearch(q);
    });

    const initial = (input?.value || new URLSearchParams(window.location.search).get("q") || "").trim();
    if (initial) await runSearch(initial);
  }

  window.CrashoutYouTubeSearch = { mount, load, renderCard };
})();
