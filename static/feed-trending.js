/**
 * Trending feed — GET /api/feed/trending (infinite scroll via max_results)
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  let pageSize = 12;
  let loading = false;
  let exhausted = false;
  let seen = new Set();

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function platformBadge(platform) {
    const p = String(platform || "unknown").toLowerCase();
    return `<span class="platform-badge platform-badge--${escapeHtml(p)}">${escapeHtml(p)}</span>`;
  }

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recovery clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const score =
      item.engagement_score != null ? Number(item.engagement_score).toFixed(1) : null;
    const media = thumb
      ? `<img class="unified-card-thumb thumbnail neon-border" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;
    const badges = [
      platformBadge(item.platform),
      score
        ? `<span class="score-badge score-badge--engagement">${escapeHtml(uiLabel("badge_engagement", "Engagement"))} ${escapeHtml(score)}</span>`
        : "",
      item.is_ad || item.platform === "ad"
        ? `<span class="ad-badge">${escapeHtml(uiLabel("badge_ad", "Sponsored"))}</span>`
        : "",
    ]
      .filter(Boolean)
      .join("");
    return `
      <article class="unified-card neon-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        ${media}
        <div class="unified-card-body">
          <div class="unified-card-badges">${badges}</div>
          <h3 class="unified-card-title title neon-title">${title}</h3>
          ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
        </div>
      </article>`;
  }

  async function load(maxResults) {
    const res = await fetch(`/api/feed/trending?max_results=${maxResults}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Trending failed (${res.status})`);
    return res.json();
  }

  async function appendPage(root) {
    if (loading || exhausted) return;
    loading = true;
    const loadingEl = document.getElementById("feed-trending-loading");
    if (loadingEl) loadingEl.hidden = false;
    try {
      const data = await load(pageSize);
      const items = Array.isArray(data.items) ? data.items : [];
      const fresh = items.filter((it) => {
        const id = String(it.id || "");
        if (!id || seen.has(id)) return false;
        seen.add(id);
        return true;
      });
      if (!fresh.length) {
        exhausted = true;
        return;
      }
      const start = root.children.length;
      root.insertAdjacentHTML(
        "beforeend",
        fresh.map((item, i) => renderCard(item, start + i)).join("")
      );
      if (items.length < pageSize) exhausted = true;
      else pageSize = Math.min(50, pageSize + 12);
    } finally {
      loading = false;
      if (loadingEl) loadingEl.hidden = true;
    }
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("feed-trending-empty");
    const errEl = document.getElementById("feed-trending-error");
    const sentinel = document.getElementById("feed-trending-sentinel");
    if (!root) return;
    seen = new Set();
    pageSize = 12;
    exhausted = false;
    root.innerHTML = "";
    try {
      await appendPage(root);
      if (!root.children.length) {
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (sentinel && "IntersectionObserver" in window) {
        const io = new IntersectionObserver((entries) => {
          if (entries.some((e) => e.isIntersecting)) appendPage(root).catch(() => {});
        });
        io.observe(sentinel);
      }
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load trending.";
      }
    }
  }

  window.CrashoutFeedTrending = { mount, load };
})();
