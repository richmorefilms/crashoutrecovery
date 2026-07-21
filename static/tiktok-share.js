/**
 * TikTok Share Kit bridge — POST /api/tiktok/share then open intent / share sheet.
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  async function requestShare({ video_url, caption, hashtags, title } = {}) {
    const res = await fetch("/api/tiktok/share", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify({
        video_url: video_url || null,
        caption: caption || "",
        hashtags: hashtags || ["recovery", "crashoutrecovery"],
        title: title || uiLabel("tiktok_share", "Share to TikTok"),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data?.detail?.message || data?.message || `Share failed (${res.status})`);
    }
    return data;
  }

  async function copyText(text) {
    if (!text) return false;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_) {
      /* fall through */
    }
    return false;
  }

  async function openShare(payload) {
    const share = payload.share || {};
    const webShare = share.web_share || {};
    const text = payload.caption || webShare.text || "";

    await copyText(share.clipboard_text || text);

    // Capacitor Share plugin (if present)
    if (window.Capacitor?.Plugins?.Share) {
      try {
        await window.Capacitor.Plugins.Share.share({
          title: webShare.title || "TikTok",
          text,
          url: webShare.url || payload.video_url || undefined,
          dialogTitle: uiLabel("tiktok_share", "Share to TikTok"),
        });
        return { mode: "capacitor", payload };
      } catch (_) {
        /* continue */
      }
    }

    // Web Share API (mobile browsers)
    if (navigator.share) {
      try {
        await navigator.share({
          title: webShare.title || "TikTok",
          text,
          url: webShare.url || payload.video_url || undefined,
        });
        return { mode: "web_share", payload };
      } catch (err) {
        if (err && err.name === "AbortError") return { mode: "cancelled", payload };
      }
    }

    // Deep link / upload fallback
    const openUrl =
      (payload.mobile && payload.mobile.open_url) ||
      share.mobile_intent ||
      share.web_upload_url ||
      "https://www.tiktok.com/upload?lang=en";
    window.open(openUrl, "_blank", "noopener");
    return { mode: "redirect", payload };
  }

  async function share(opts) {
    const payload = await requestShare(opts);
    return openShare(payload);
  }

  function bindDelegates(root) {
    const el = root || document;
    el.addEventListener("click", (ev) => {
      const btn = ev.target.closest?.("[data-tiktok-share]");
      if (!btn) return;
      ev.preventDefault();
      const caption = btn.getAttribute("data-caption") || "";
      const hashtags = (btn.getAttribute("data-hashtags") || "recovery")
        .split(/[\s,]+/)
        .filter(Boolean);
      const videoUrl = btn.getAttribute("data-video-url") || undefined;
      btn.disabled = true;
      share({ caption, hashtags, video_url: videoUrl })
        .catch((err) => {
          window.alert(err.message || "Could not share to TikTok");
        })
        .finally(() => {
          btn.disabled = false;
        });
    });
  }

  document.addEventListener("DOMContentLoaded", () => bindDelegates(document));

  window.CrashoutTikTokShare = {
    requestShare,
    openShare,
    share,
    bindDelegates,
  };
})();
