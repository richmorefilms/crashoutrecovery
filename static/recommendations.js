/**
 * Recommendations explorer — GET /api/recommendations/all/{user_id}
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

  function resolveUserId() {
    const main = document.querySelector(".feed-page--recommendations");
    const fromData = main?.getAttribute("data-user-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("user_id") || "";
  }

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recommended clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const topics = Array.isArray(item.topics) ? item.topics.slice(0, 3).join(", ") : "";
    const media = thumb
      ? `<img class="unified-card-thumb" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;
    return `
      <article class="unified-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        ${media}
        <div class="unified-card-body">
          <div class="unified-card-badges">
            <span class="platform-badge">${escapeHtml(item.platform || "rec")}</span>
            <span class="score-badge score-badge--recommended">${escapeHtml(uiLabel("badge_recommended", "Recommended"))}</span>
          </div>
          <h3 class="unified-card-title">${title}</h3>
          ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
          ${topics ? `<p class="unified-card-score">${escapeHtml(topics)}</p>` : ""}
        </div>
      </article>`;
  }

  async function load(userId) {
    const res = await fetch(`/api/recommendations/all/${encodeURIComponent(userId)}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Recommendations failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("recommendations-empty");
    const errEl = document.getElementById("recommendations-error");
    if (!root) return;
    const userId = resolveUserId();
    if (!userId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=yourUserId for recommendations.";
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
        errEl.textContent = err.message || "Could not load recommendations.";
      }
    }
  }

  window.CrashoutRecommendations = { mount, load };
})();
