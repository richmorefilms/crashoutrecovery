/**
 * TikTok Upload / Publish — POST multipart /api/tiktok/upload
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function authHeaders() {
    const token = window.CrashoutAuth?.token?.();
    const headers = { Accept: "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }

  async function uploadFile(file, options = {}) {
    if (!file) throw new Error("Choose a video file first");
    if (!window.CrashoutAuth?.isLoggedIn?.()) {
      window.CrashoutAuth?.openModal?.("login");
      throw new Error("Log in and connect TikTok to publish");
    }

    const form = new FormData();
    form.append("video", file, file.name || "video.mp4");
    form.append("title", options.title || "Crashout Recovery");
    form.append("privacy_level", options.privacy_level || "SELF_ONLY");
    form.append("disable_comment", String(Boolean(options.disable_comment)));
    form.append("disable_duet", String(Boolean(options.disable_duet)));
    form.append("disable_stitch", String(Boolean(options.disable_stitch)));

    const res = await fetch("/api/tiktok/upload", {
      method: "POST",
      headers: authHeaders(),
      body: form,
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg =
        data?.detail?.message ||
        (typeof data?.detail === "string" ? data.detail : null) ||
        data?.message ||
        `Upload failed (${res.status})`;
      throw new Error(msg);
    }
    return data;
  }

  function mountCreatorControls(container) {
    const root =
      typeof container === "string" ? document.querySelector(container) : container;
    if (!root || root.dataset.tiktokUploadMounted) return;
    root.dataset.tiktokUploadMounted = "1";

    const wrap = document.createElement("section");
    wrap.className = "creator-block creator-tiktok-block";
    wrap.innerHTML = `
      <h3 class="creator-block-title" data-ui-copy="tiktok_publish">${uiLabel(
        "tiktok_publish",
        "Publish to TikTok"
      )}</h3>
      <p class="creator-tiktok-note">Uploads as private (SELF_ONLY) by default. Connect TikTok first.</p>
      <input type="file" id="tiktok-upload-file" accept="video/*" class="creator-tiktok-file" />
      <input type="text" id="tiktok-upload-title" class="creator-tiktok-title" maxlength="150"
        placeholder="Caption / title" />
      <div class="creator-tiktok-actions">
        <button type="button" class="creator-locked-btn" id="tiktok-upload-btn" data-ui-copy="tiktok_publish">
          ${uiLabel("tiktok_publish", "Publish to TikTok")}
        </button>
        <a class="feed-cta feed-cta--ghost" href="/auth/tiktok/login">${uiLabel(
          "tiktok_connect",
          "Connect TikTok"
        )}</a>
      </div>
      <p id="tiktok-upload-status" class="creator-empty-note" hidden></p>
    `;
    root.appendChild(wrap);

    const statusEl = wrap.querySelector("#tiktok-upload-status");
    const btn = wrap.querySelector("#tiktok-upload-btn");
    btn?.addEventListener("click", async () => {
      const fileInput = wrap.querySelector("#tiktok-upload-file");
      const titleInput = wrap.querySelector("#tiktok-upload-title");
      const file = fileInput?.files?.[0];
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.textContent = "Uploading…";
      }
      btn.disabled = true;
      try {
        const result = await uploadFile(file, {
          title: titleInput?.value || "Crashout Recovery",
          privacy_level: "SELF_ONLY",
        });
        if (statusEl) {
          statusEl.textContent = `Published · status ${result.status || "ok"}${
            result.video_id ? ` · id ${result.video_id}` : ""
          }${result.publish_id ? ` · publish ${result.publish_id}` : ""}`;
        }
      } catch (err) {
        if (statusEl) statusEl.textContent = err.message || "Upload failed";
      } finally {
        btn.disabled = false;
      }
    });
  }

  window.CrashoutTikTokUpload = {
    uploadFile,
    mountCreatorControls,
  };
})();
