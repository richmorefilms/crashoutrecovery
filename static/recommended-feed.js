/**
 * Recommended feed — GET /api/feed/all?recommended={user_id}
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

  function resolveUserId() {
    const main = document.querySelector(".feed-page--recommended");
    const fromData = main?.getAttribute("data-user-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    const q = params.get("id") || params.get("user_id") || params.get("recommended");
    if (q) return q;
    try {
      const raw = localStorage.getItem("crashout_auth_user");
      const user = raw ? JSON.parse(raw) : null;
      if (user?.id) return String(user.id);
    } catch (_) {
      /* ignore */
    }
    return "";
  }

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recommended clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const topics = Array.isArray(item.topics) ? item.topics.slice(0, 3).join(", ") : "";
    const platform = String(item.platform || "rec").toLowerCase();
    const media = thumb
      ? `<img class="unified-card-thumb thumbnail neon-border" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;
    const recScore =
      item.recommended_score != null
        ? Number(item.recommended_score).toFixed(1)
        : item.source === "collaborative"
          ? "cf"
          : "—";
    return `
      <article class="unified-card neon-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        ${media}
        <div class="unified-card-body">
          <div class="unified-card-badges">
            <span class="platform-badge platform-badge--${escapeHtml(platform)}">${escapeHtml(platform)}</span>
            <span class="score-badge score-badge--recommended">${escapeHtml(uiLabel("badge_recommended", "Recommended"))} ${escapeHtml(String(recScore))}</span>
            ${
              item.engagement_score != null
                ? `<span class="score-badge score-badge--engagement">${escapeHtml(uiLabel("badge_engagement", "Engagement"))} ${escapeHtml(String(Number(item.engagement_score).toFixed(1)))}</span>`
                : ""
            }
            ${item.is_ad ? `<span class="ad-badge">${escapeHtml(uiLabel("badge_ad", "Sponsored"))}</span>` : ""}
          </div>
          <h3 class="unified-card-title title neon-title">${title}</h3>
          ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
          ${topics ? `<p class="unified-card-score">${escapeHtml(topics)}</p>` : ""}
        </div>
      </article>`;
  }

  async function load(userId, maxResults) {
    const res = await fetch(
      `/api/feed/all?recommended=${encodeURIComponent(userId)}&max_results=${maxResults}`,
      { credentials: "same-origin" }
    );
    if (!res.ok) throw new Error(`Recommended feed failed (${res.status})`);
    return res.json();
  }

  async function appendPage(root, userId) {
    if (loading || exhausted) return;
    loading = true;
    const loadingEl = document.getElementById("recommended-feed-loading");
    if (loadingEl) loadingEl.hidden = false;
    try {
      const data = await load(userId, pageSize);
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
    const empty = document.getElementById("recommended-feed-empty");
    const errEl = document.getElementById("recommended-feed-error");
    const sentinel = document.getElementById("recommended-feed-sentinel");
    if (!root) return;
    const userId = resolveUserId();
    if (!userId) {
      root.innerHTML = "";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=yourUserId (or sign in) for recommendations.";
      }
      return;
    }
    seen = new Set();
    pageSize = 12;
    exhausted = false;
    root.innerHTML = "";
    try {
      await appendPage(root, userId);
      if (!root.children.length) {
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;
      if (sentinel && "IntersectionObserver" in window) {
        const io = new IntersectionObserver((entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            appendPage(root, userId).catch(() => {});
          }
        });
        io.observe(sentinel);
      }
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load recommended feed.";
      }
    }
  }

  window.CrashoutRecommendedFeed = { mount, load, resolveUserId };
})();
