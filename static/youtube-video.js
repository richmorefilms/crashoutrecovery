/**
 * YouTube video detail — GET /api/youtube/video/{video_id}
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
    const title = escapeHtml(item.title || "YouTube video");
    const desc = escapeHtml(item.description || "");
    const channel = escapeHtml(item.channel || "");
    const published = escapeHtml(item.published_at || "");
    const thumb = escapeHtml(thumbUrl(item.thumbnails));
    const stats = item.statistics || {};
    const views = stats.view_count != null ? Number(stats.view_count) : "—";
    const likes = stats.like_count != null ? Number(stats.like_count) : "—";
    const comments = stats.comment_count != null ? Number(stats.comment_count) : "—";

    return `
      <article class="youtube-detail-card">
        ${thumb ? `<img class="youtube-detail-thumb" src="${thumb}" alt="">` : ""}
        <h2 class="youtube-detail-title">${title}</h2>
        <p class="youtube-detail-channel">${channel}</p>
        ${published ? `<p class="youtube-detail-meta">${published}</p>` : ""}
        <ul class="youtube-detail-stats">
          <li>Views: ${escapeHtml(String(views))}</li>
          <li>Likes: ${escapeHtml(String(likes))}</li>
          <li>Comments: ${escapeHtml(String(comments))}</li>
        </ul>
        ${desc ? `<p class="youtube-detail-desc">${desc}</p>` : ""}
      </article>`;
  }

  async function load(videoId) {
    const res = await fetch(`/api/youtube/video/${encodeURIComponent(videoId)}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Video failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const errEl = document.getElementById("youtube-video-error");
    if (!root) return;
    const videoId = root.getAttribute("data-video-id") || "";
    if (!videoId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Missing video id.";
      }
      return;
    }
    try {
      const data = await load(videoId);
      const item = (data.items && data.items[0]) || null;
      if (!item) throw new Error("Video not found");
      root.innerHTML = renderDetail(item);
    } catch (err) {
      root.innerHTML = "";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load video.";
      }
    }
  }

  window.CrashoutYouTubeVideo = { mount, load, renderDetail };
})();
