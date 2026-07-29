/**
 * Unified feed — GET /api/feed/all (infinite scroll via max_results)
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

  function renderCard(item, rank) {
    const title = escapeHtml(item.title || "Recovery clip");
    const channel = escapeHtml(item.channel || "");
    const thumb = item.thumbnail ? escapeHtml(item.thumbnail) : "";
    const platform = String(item.platform || "unknown").toLowerCase();
    let href = "#";
    if (platform === "youtube" && item.id) {
      href = `/youtube/video/${encodeURIComponent(item.id)}`;
    } else if (platform === "tiktok") {
      href = "/feed/tiktok";
    }
    const media = thumb
      ? `<img class="unified-card-thumb" src="${thumb}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;

    return `
      <article class="unified-card" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        <a class="unified-card-link" href="${href}">
          ${media}
          <div class="unified-card-body">
            ${platformBadge(platform)}
            ${scoreBadges(item)}
            <h3 class="unified-card-title">${title}</h3>
            ${channel ? `<p class="unified-card-channel">${channel}</p>` : ""}
          </div>
        </a>
      </article>`;
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
      root.innerHTML = "";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load feed.";
      }
    }
  }

  window.CrashoutFeedAll = { mount, load, renderCard };
})();
