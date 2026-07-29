/**
 * YouTube channel detail — GET /api/youtube/channel/{channel_id}
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function thumbUrl(thumbs) {
    if (!thumbs || typeof thumbs !== "object") return "";
    return thumbs.high || thumbs.medium || thumbs.default || "";
  }

  function renderDetail(item) {
    const title = escapeHtml(item.title || "YouTube channel");
    const desc = escapeHtml(item.description || "");
    const thumb = escapeHtml(thumbUrl(item.thumbnails));
    const stats = item.statistics || {};
    const subs = stats.subscriber_count != null ? Number(stats.subscriber_count) : "—";
    const videos = stats.video_count != null ? Number(stats.video_count) : "—";
    const views = stats.view_count != null ? Number(stats.view_count) : "—";

    return `
      <article class="youtube-detail-card">
        ${thumb ? `<img class="youtube-detail-thumb youtube-detail-thumb--channel" src="${thumb}" alt="">` : ""}
        <h2 class="youtube-detail-title">${title}</h2>
        <ul class="youtube-detail-stats">
          <li>Subscribers: ${escapeHtml(String(subs))}</li>
          <li>Videos: ${escapeHtml(String(videos))}</li>
          <li>Views: ${escapeHtml(String(views))}</li>
        </ul>
        ${desc ? `<p class="youtube-detail-desc">${desc}</p>` : ""}
      </article>`;
  }

  async function load(channelId) {
    const res = await fetch(`/api/youtube/channel/${encodeURIComponent(channelId)}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Channel failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const errEl = document.getElementById("youtube-channel-error");
    if (!root) return;
    const channelId = root.getAttribute("data-channel-id") || "";
    if (!channelId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Missing channel id.";
      }
      return;
    }
    try {
      const data = await load(channelId);
      const item = (data.items && data.items[0]) || null;
      if (!item) throw new Error("Channel not found");
      root.innerHTML = renderDetail(item);
    } catch (err) {
      root.innerHTML = "";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load channel.";
      }
    }
  }

  window.CrashoutYouTubeChannel = { mount, load, renderDetail };
})();
