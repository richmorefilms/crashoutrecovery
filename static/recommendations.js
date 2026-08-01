/**
 * Recommendations explorer — GET /api/recommendations/all/{user_id}
 * Hologram Edition cards + platform filters
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  let activeFilter = "all";

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

  function scoreLabel(item) {
    if (item.recommended_score != null) {
      return `${Math.round(Number(item.recommended_score))}%`;
    }
    if (item.engagement_score != null) {
      return `${Number(item.engagement_score).toFixed(1)}`;
    }
    return "";
  }

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recommended clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const platform = String(item.platform || "rec").toLowerCase();
    const topics = Array.isArray(item.topics) ? item.topics.slice(0, 3).join(", ") : "";
    const score = scoreLabel(item);
    const media = thumb
      ? `<img class="unified-card-thumb thumbnail neon-border" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;
    return `
      <article
        class="holo-card unified-card neon-card"
        data-id="${escapeHtml(item.id)}"
        data-category="${escapeHtml(platform)}"
        data-type="${escapeHtml(platform)}"
        style="animation-delay:${rank * 40}ms"
      >
        <div class="holo-inner">
          ${media}
          <div class="unified-card-body">
            <div class="unified-card-badges">
              <span class="platform-badge">${escapeHtml(platform)}</span>
              <span class="score-badge score-badge--recommended">${escapeHtml(uiLabel("badge_recommended", "Recommended"))}</span>
            </div>
            <h3 class="unified-card-title holo-title title neon-title">${title}</h3>
            ${channel ? `<p class="unified-card-channel holo-desc">${channel}</p>` : ""}
            ${topics ? `<p class="unified-card-score holo-desc">${escapeHtml(topics)}</p>` : ""}
            <div class="holo-meta">
              <span>${escapeHtml(platform.toUpperCase())}</span>
              <span>${escapeHtml(score)}</span>
            </div>
          </div>
        </div>
      </article>`;
  }

  function applyFilter(root) {
    if (!root) return;
    root.querySelectorAll(".holo-card").forEach((card) => {
      const type = (card.dataset.category || card.dataset.type || "").toLowerCase();
      const show = activeFilter === "all" || type === activeFilter;
      card.hidden = !show;
      card.style.display = show ? "" : "none";
    });
  }

  function initFilters(root) {
    const buttons = document.querySelectorAll(".reco-filter-btn");
    if (!buttons.length) return;
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter || "all";
        applyFilter(root);
      });
    });
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
    activeFilter = "all";
    initFilters(root);
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
      applyFilter(root);
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load recommendations.";
      }
    }
  }

  window.CrashoutRecommendations = { mount, load };
})();
