/**
 * Neon Clip Studio Pro — multi-clip timeline + AI caption assist
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

  const CLIPS = [
    { id: "a", labelKey: "studio_clip_hook", len: 4 },
    { id: "b", labelKey: "studio_clip_body", len: 10 },
    { id: "c", labelKey: "studio_clip_cta", len: 6 },
  ];

  async function aiCaption(seed) {
    try {
      const res = await fetch("/api/suggest", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: seed || "Write a short neon caption for a recovery clip.",
          tone: "calm",
        }),
      });
      if (!res.ok) throw new Error("fail");
      const data = await res.json();
      return data.suggestion || data.redirect || data.message || seed;
    } catch (_) {
      return "One small move. Save the draft. Keep going.";
    }
  }

  function mount() {
    const track = document.getElementById("studio-pro-track");
    const caption = document.getElementById("pro-caption");
    const thumb = document.getElementById("pro-thumb");
    const preview = document.getElementById("pro-preview");
    const aiBtn = document.getElementById("pro-caption-ai");
    const boost = document.getElementById("pro-boost");

    if (track) {
      track.innerHTML = CLIPS.map((c) => {
        const label = uiLabel(c.labelKey, c.id);
        return `
        <button type="button" class="pro-clip" data-clip="${escapeHtml(c.id)}" style="flex:${c.len}">
          ${escapeHtml(label)} · ${c.len}s
        </button>`;
      }).join("");
    }

    function sync() {
      if (!preview) return;
      preview.dataset.frame = thumb?.value || "neon";
      preview.innerHTML = `
        <p class="studio-player-label">${escapeHtml(caption?.value || uiLabel("clip_preview", "Neon preview"))}</p>
        <p class="studio-player-meta">${escapeHtml(thumb?.value || "cyan")}</p>`;
    }

    track?.addEventListener("click", (ev) => {
      const clip = ev.target.closest("[data-clip]");
      if (!clip) return;
      track.querySelectorAll(".pro-clip").forEach((el) => el.classList.remove("is-active"));
      clip.classList.add("is-active");
      sync();
    });
    caption?.addEventListener("input", sync);
    thumb?.addEventListener("change", sync);
    aiBtn?.addEventListener("click", async () => {
      aiBtn.textContent = uiLabel("assist_thinking", "Thinking…");
      const text = await aiCaption(caption?.value);
      if (caption) caption.value = String(text).slice(0, 160);
      aiBtn.textContent = uiLabel("studio_caption_ai", "GENERATE CAPTION");
      sync();
    });
    boost?.addEventListener("click", () => {
      window.CrashoutNotifications?.toast?.(uiLabel("clip_boosted", "CLIP BOOSTED"));
      window.CrashoutCreatorBadges?.earn?.("creativity");
    });
    sync();
  }

  window.CrashoutClipStudioPro = { mount };
})();
