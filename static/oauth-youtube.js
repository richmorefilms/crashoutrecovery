/**
 * YouTube OAuth frontend — login prep + callback status.
 * Callback page calls GET /api/oauth/youtube/callback?code=&state=
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function prepareLogin() {
    const btn = document.getElementById("oauth-youtube-login-btn");
    if (!btn) return;
    const params = new URLSearchParams(window.location.search);
    let state = params.get("state");
    if (!state) {
      try {
        const raw = localStorage.getItem("crashout_auth_user");
        const user = raw ? JSON.parse(raw) : null;
        if (user?.id) state = String(user.id);
      } catch (_) {
        /* ignore */
      }
    }
    if (state) {
      const url = new URL(btn.href, window.location.origin);
      url.searchParams.set("state", state);
      btn.href = url.pathname + url.search;
    }
  }

  async function handleCallback() {
    const statusEl = document.getElementById("oauth-youtube-status");
    const errEl = document.getElementById("oauth-youtube-error");
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state") || "";
    const oauthError = params.get("error");

    if (oauthError) {
      if (statusEl) statusEl.textContent = "Connection cancelled.";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = oauthError;
      }
      return;
    }

    if (!code) {
      if (statusEl) {
        statusEl.textContent = uiLabel("youtube_linked", "YouTube account linked");
      }
      return;
    }

    if (statusEl) statusEl.textContent = "Linking YouTube…";
    try {
      const qs = new URLSearchParams({ code });
      if (state) qs.set("state", state);
      const res = await fetch(`/api/oauth/youtube/callback?${qs.toString()}`, {
        credentials: "same-origin",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) {
        const msg =
          data?.detail?.message ||
          data?.detail ||
          data?.reason ||
          `Link failed (${res.status})`;
        throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
      }
      if (statusEl) {
        statusEl.textContent = uiLabel("youtube_linked", "YouTube account linked");
      }
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (statusEl) statusEl.textContent = "Could not link YouTube.";
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "OAuth error";
      }
    }
  }

  window.CrashoutYouTubeOAuth = { prepareLogin, handleCallback };
})();
