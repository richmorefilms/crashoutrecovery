/**
 * TikTok Login Kit — OAuth start for web + Capacitor/RN.
 * Prefer this module name (tiktok-auth.js); CrashoutTikTokOAuth remains as alias.
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  async function startOAuth(opts = {}) {
    const params = new URLSearchParams({ format: "json" });
    if (opts.mobile) params.set("mobile", "1");
    if (opts.redirect_uri) params.set("redirect_uri", opts.redirect_uri);

    const headers = { Accept: "application/json" };
    const token = window.CrashoutAuth?.token?.();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`/auth/tiktok/login?${params.toString()}`, {
      headers,
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg =
        data?.detail?.message ||
        (typeof data?.detail === "string" ? data.detail : null) ||
        data?.message ||
        `${uiLabel("tiktok_login", "Sign in with TikTok")} unavailable (${res.status})`;
      throw new Error(msg);
    }
    if (!data.authorize_url) throw new Error("No authorize_url from server");

    // Capacitor Browser plugin (optional)
    if (opts.mobile && window.Capacitor?.Plugins?.Browser) {
      try {
        await window.Capacitor.Plugins.Browser.open({ url: data.authorize_url });
        return data;
      } catch (_) {
        /* fall through */
      }
    }

    window.location.href = data.authorize_url;
    return data;
  }

  function bindLinks(root) {
    (root || document).addEventListener("click", (ev) => {
      const link = ev.target.closest?.("[data-tiktok-oauth]");
      if (!link) return;
      ev.preventDefault();
      const mobile = link.getAttribute("data-mobile") === "1";
      startOAuth({ mobile }).catch((err) => {
        window.alert(err.message || "TikTok login is not configured yet.");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => bindLinks(document));

  const api = { startOAuth, bindLinks };
  window.CrashoutTikTokAuth = api;
  window.CrashoutTikTokOAuth = api;
})();
