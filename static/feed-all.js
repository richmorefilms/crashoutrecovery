/**
 * Unified feed — GET /api/feed/all (infinite scroll + hologram filters)
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  let pageSize = 12;
  let loading = false;
  let exhausted = false;
  let seen = new Set();
  let activeFilter = "all";

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function platformBadge(platform) {
    const p = String(platform || "unknown").toLowerCase();
    const label =
      p === "youtube"
        ? uiLabel("platform_youtube", "YouTube")
        : p === "tiktok"
          ? uiLabel("platform_tiktok", "TikTok")
          : escapeHtml(p);
    return `<span class="platform-badge platform-badge--${escapeHtml(p)}">${escapeHtml(label)}</span>`;
  }

  function scoreBadges(item) {
    const bits = [];
    if (item.engagement_score != null) {
      bits.push(
        `<span class="score-badge score-badge--engagement">${escapeHtml(uiLabel("badge_engagement", "Engagement"))} ${escapeHtml(String(Number(item.engagement_score).toFixed(1)))}</span>`
      );
    }
    if (item.recommended_score != null || item.source === "collaborative") {
      const score =
        item.recommended_score != null
          ? Number(item.recommended_score).toFixed(1)
          : "rec";
      bits.push(
        `<span class="score-badge score-badge--recommended">${escapeHtml(uiLabel("badge_recommended", "Recommended"))} ${escapeHtml(String(score))}</span>`
      );
    }
    if (item.platform === "ad" || item.is_ad || item.type === "ad") {
      bits.push(
        `<span class="ad-badge">${escapeHtml(uiLabel("badge_ad", "Sponsored"))}</span>`
      );
    }
    return bits.length ? `<div class="unified-card-badges">${bits.join("")}</div>` : "";
  }

  function isTrending(item) {
    if (item.engagement_score != null && Number(item.engagement_score) >= 5) return true;
    if (item.recommended_score != null && Number(item.recommended_score) >= 5) return true;
    return false;
  }

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recovery clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const platform = String(item.platform || "unknown").toLowerCase();
    const trending = isTrending(item) ? "1" : "0";
    let href = "#";
    if (platform === "youtube" && item.id) {
      href = `/youtube/video/${encodeURIComponent(item.id)}`;
    } else if (platform === "tiktok") {
      href = "/feed/tiktok";
    }
    const media = thumb
      ? `<img class="unified-card-thumb thumbnail neon-border" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;

    return `
      <article
        class="holo-card unified-card neon-card"
        data-id="${escapeHtml(item.id)}"
        data-type="${escapeHtml(platform)}"
        data-trending="${trending}"
        style="animation-delay:${rank * 40}ms"
      >
        <a class="unified-card-link holo-inner" href="${href}">
          ${media}
          <div class="unified-card-body">
            ${platformBadge(platform)}
            ${scoreBadges(item)}
            <h3 class="unified-card-title holo-title title neon-title">${title}</h3>
            ${channel ? `<p class="unified-card-channel holo-desc">${channel}</p>` : ""}
            <div class="holo-meta">
              <span>${escapeHtml(platform.toUpperCase())}</span>
              <span></span>
            </div>
          </div>
        </a>
      </article>`;
  }

  function applyFilter(root) {
    if (!root) return;
    const cards = root.querySelectorAll(".holo-card");
    cards.forEach((card) => {
      const type = (card.dataset.type || "").toLowerCase();
      const trending = card.dataset.trending === "1";
      let show = true;
      if (activeFilter === "trending") show = trending;
      else if (activeFilter !== "all") show = type === activeFilter;
      card.hidden = !show;
      card.style.display = show ? "" : "none";
    });
  }

  function initFilters(root) {
    const buttons = document.querySelectorAll(".feed-filters .filter-btn");
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

  async function load(maxResults) {
    const res = await fetch(`/api/feed/all?max_results=${maxResults}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Feed failed (${res.status})`);
    return res.json();
  }

  async function appendPage(root) {
    if (loading || exhausted) return;
    loading = true;
    const loadingEl = document.getElementById("feed-all-loading");
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
      applyFilter(root);
      if (items.length < pageSize) exhausted = true;
      else pageSize = Math.min(50, pageSize + 12);
    } finally {
      loading = false;
      if (loadingEl) loadingEl.hidden = true;
    }
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("feed-all-empty");
    const errEl = document.getElementById("feed-all-error");
    const sentinel = document.getElementById("feed-all-sentinel");
    if (!root) return;
    if (errEl) errEl.hidden = true;
    seen = new Set();
    pageSize = 12;
    exhausted = false;
    activeFilter = "all";
    root.innerHTML = "";
    initFilters(root);
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
      root.innerHTML = "";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load feed.";
      }
    }
  }

  window.CrashoutFeedAll = { mount, load, renderCard };
})();
