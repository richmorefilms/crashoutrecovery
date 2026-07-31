/**
 * Personalized feed — GET /api/feed/all?personalized={user_id}
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function resolveUserId() {
    const main = document.querySelector(".feed-page--personalized");
    const fromData = main?.getAttribute("data-user-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    const q = params.get("id") || params.get("user_id");
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
    const title = escapeHtml(item.title || "Recovery clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const score =
      item.engagement_score != null ? Number(item.engagement_score).toFixed(1) : "—";
    const boost =
      item.personalization_boost != null && Number(item.personalization_boost) > 0
        ? ` (+${Number(item.personalization_boost).toFixed(0)})`
        : "";
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
          <p class="unified-card-score">Score ${escapeHtml(String(score))}${escapeHtml(boost)}</p>
        </div>
      </article>`;
  }

  async function load(userId) {
    const res = await fetch(
      `/api/feed/all?personalized=${encodeURIComponent(userId)}`,
      { credentials: "same-origin" }
    );
    if (!res.ok) throw new Error(`Personalized feed failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("personalized-feed-empty");
    const errEl = document.getElementById("personalized-feed-error");
    if (!root) return;
    const userId = resolveUserId();
    if (!userId) {
      root.innerHTML = "";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=yourUserId (or sign in) for personalization.";
      }
      return;
    }
    try {
      const data = await load(userId);
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
        errEl.textContent = err.message || "Could not load personalized feed.";
      }
    }
  }

  window.CrashoutPersonalizedFeed = { mount, load, resolveUserId };
})();
