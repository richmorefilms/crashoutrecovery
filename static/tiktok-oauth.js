/**
 * TikTok OAuth start — attach Bearer so Login Kit links to the Crashout user.
 */
(function () {
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
        `TikTok login unavailable (${res.status})`;
      throw new Error(msg);
    }
    if (!data.authorize_url) throw new Error("No authorize_url from server");
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

  window.CrashoutTikTokOAuth = { startOAuth, bindLinks };
})();
