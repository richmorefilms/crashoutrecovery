/**
 * TikTok Recovery Feed — fetch /api/tiktok/feed and render embed cards.
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
    const title = escapeHtml(item.title || "TikTok clip");
    const author = escapeHtml(item.author || "@tiktok");
    const tag = item.hashtag ? `#${escapeHtml(item.hashtag)}` : "";
    const share = item.share_url ? escapeHtml(item.share_url) : "";
    const embed = item.embed_url ? escapeHtml(item.embed_url) : "";
    const cover = item.cover_url ? escapeHtml(item.cover_url) : "";

    let media = "";
    if (embed) {
      media = `<div class="tiktok-embed-wrap">
        <blockquote class="tiktok-embed" cite="${share || embed}" data-video-id="${escapeHtml(item.video_id || "")}">
          <iframe src="${embed}" title="${title}" allowfullscreen loading="lazy" class="tiktok-embed-frame"></iframe>
        </blockquote>
      </div>`;
    } else if (cover) {
      media = `<a class="tiktok-cover-link" href="${share || "#"}" target="_blank" rel="noopener">
        <img src="${cover}" alt="" class="tiktok-cover">
      </a>`;
    } else {
      media = `<div class="tiktok-placeholder" aria-hidden="true"></div>`;
    }

    return `
      <article class="feed-item feed-item--tiktok" data-id="${escapeHtml(item.id)}" style="animation-delay:${rank * 40}ms">
        <div class="feed-item-content">
          <header class="feed-post-card-header">
            <span class="feed-community-avatar" aria-hidden="true">T</span>
            <div>
              <p class="feed-community-author">${author}</p>
              <p class="feed-community-meta">${tag || "TikTok"}</p>
            </div>
            <span class="feed-item-category">${escapeHtml(uiLabel("tiktok_recovery_feed", "TikTok"))}</span>
          </header>
          <h3 class="feed-item-title">${title}</h3>
          <p class="feed-item-post-text">${escapeHtml(item.description || "")}</p>
          ${media}
          <footer class="feed-item-cta-row">
            ${share ? `<a class="feed-cta" href="${share}" target="_blank" rel="noopener">Open on TikTok</a>` : ""}
            <button type="button" class="feed-cta feed-cta--ghost" data-tiktok-share
              data-caption="${escapeHtml(item.description || item.title || "")}"
              data-hashtags="${escapeHtml(item.hashtag || "recovery")}">
              ${escapeHtml(uiLabel("tiktok_share", "Share to TikTok"))}
            </button>
          </footer>
        </div>
      </article>`;
  }

  async function fetchFeed(hashtags) {
    const params = new URLSearchParams();
    if (hashtags) params.set("hashtag", hashtags);
    const res = await fetch(`/api/tiktok/feed?${params.toString()}`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Feed failed (${res.status})`);
    return res.json();
  }

  async function renderInto(el, options) {
    if (!el) return null;
    el.innerHTML = `<p class="tiktok-feed-loading">Loading ${uiLabel("tiktok_recovery_feed", "TikTok Recovery Feed")}…</p>`;
    try {
      const data = await fetchFeed(options?.hashtags);
      const items = data.items || [];
      el.innerHTML = items.map((item, i) => renderCard(item, i)).join("");
      // Re-run TikTok embed.js if present
      if (window.tiktokEmbed?.lib?.render) {
        try {
          window.tiktokEmbed.lib.render();
        } catch (_) {
          /* ignore */
        }
      }
      return data;
    } catch (err) {
      el.innerHTML = `<p class="tiktok-feed-error">${escapeHtml(err.message || "Could not load TikTok feed")}</p>`;
      return null;
    }
  }

  function mount(selector, options) {
    const el = typeof selector === "string" ? document.querySelector(selector) : selector;
    return renderInto(el, options);
  }

  window.CrashoutTikTokFeed = {
    fetchFeed,
    renderInto,
    mount,
    renderCard,
  };
})();
