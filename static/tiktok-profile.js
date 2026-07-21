/**
 * Profile page — show Crashout + linked TikTok avatar/username.
 */
(function () {
  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value || "";
  }

  async function loadTikTokProfile() {
    const token = window.CrashoutAuth?.token?.();
    const status = document.getElementById("profile-status");
    const params = new URLSearchParams(window.location.search);
    if (params.get("msg") && status) {
      status.hidden = false;
      status.textContent = params.get("msg");
      status.classList.toggle("auth-status--error", params.get("tiktok") === "0");
    }

    const profile = window.CrashoutAuth?.user?.();
    if (profile?.username) {
      setText("profile-username", `@${profile.username}`);
      setText("profile-email", profile.email || "");
    } else {
      setText("profile-username", "Not signed in");
      setText("profile-email", "");
    }

    if (!token) return;

    try {
      const res = await fetch("/api/tiktok/me", {
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await res.json().catch(() => ({}));
      const block = document.getElementById("profile-tiktok");
      if (!res.ok || !data.connected || !data.tiktok) {
        if (block) block.hidden = true;
        return;
      }
      if (block) block.hidden = false;
      setText("profile-tiktok-name", data.tiktok.username || data.tiktok.display_name || "TikTok");
      setText(
        "profile-tiktok-id",
        data.tiktok.tiktok_user_id ? `id ${data.tiktok.tiktok_user_id}` : ""
      );
      const badge = document.getElementById("profile-tiktok-badge");
      if (badge) badge.hidden = false;
      const connectBtn = document.getElementById("profile-tiktok-connect");
      if (connectBtn) connectBtn.hidden = true;
      const img = document.getElementById("profile-tiktok-avatar");
      if (img && data.tiktok.avatar_url) {
        img.src = data.tiktok.avatar_url;
        img.hidden = false;
        img.alt = data.tiktok.username || data.tiktok.display_name || "TikTok avatar";
      }
    } catch (_) {
      /* ignore */
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadTikTokProfile();
    window.addEventListener("crashout:auth-changed", loadTikTokProfile);
  });

  window.CrashoutTikTokProfile = { loadTikTokProfile };
})();
