/**
 * Neon Clip Studio — local hologram editing console
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
    { id: "clip_1", title: "One small move", lane: "youtube" },
    { id: "clip_2", title: "Pause before post", lane: "tiktok" },
    { id: "clip_3", title: "Forward momentum", lane: "youtube" },
  ];

  function renderClips(root) {
    root.innerHTML = CLIPS.map(
      (c) => `
      <article class="holo-card studio-clip-card" data-clip-id="${escapeHtml(c.id)}">
        <h3 class="neon-title">${escapeHtml(c.title)}</h3>
        <p class="expand-sub">${escapeHtml(c.lane.toUpperCase())} ${escapeHtml(uiLabel("clip_export", "export lane"))}</p>
        <button type="button" class="launch-btn launch-btn--ready studio-export-btn" data-lane="${escapeHtml(c.lane)}">
          ${escapeHtml(uiLabel("clip_boost", "BOOST CLIP"))}
        </button>
      </article>`
    ).join("");
  }

  function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    if (!root) return;
    const clipsRoot = document.getElementById("studio-clips-root");
    const player = document.getElementById("studio-player");
    const caption = document.getElementById("studio-caption");
    const trim = document.getElementById("studio-trim");
    const thumb = document.getElementById("studio-thumb");
    const boost = document.getElementById("studio-boost");

    if (clipsRoot) renderClips(clipsRoot);

    function syncPreview() {
      if (!player) return;
      const seconds = trim?.value || "15";
      const text = caption?.value || uiLabel("clip_preview", "Neon preview");
      const frame = thumb?.value || "neon";
      player.dataset.frame = frame;
      player.innerHTML = `
        <p class="studio-player-label">${escapeHtml(text)}</p>
        <p class="studio-player-meta">${escapeHtml(seconds)}s · ${escapeHtml(frame)}</p>`;
    }

    trim?.addEventListener("input", syncPreview);
    caption?.addEventListener("input", syncPreview);
    thumb?.addEventListener("change", syncPreview);
    boost?.addEventListener("click", () => {
      boost.classList.add("is-glowing");
      boost.textContent = uiLabel("clip_boosted", "CLIP BOOSTED");
      setTimeout(() => {
        boost.classList.remove("is-glowing");
        boost.textContent = uiLabel("clip_boost", "BOOST CLIP");
      }, 1600);
      try {
        window.CrashoutNotifications?.toast?.(uiLabel("clip_boosted", "CLIP BOOSTED"));
      } catch (_) {
        /* optional */
      }
    });
    clipsRoot?.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".studio-export-btn");
      if (!btn) return;
      const lane = btn.getAttribute("data-lane");
      if (lane === "youtube") window.location.href = "/oauth/youtube";
      else if (lane === "tiktok") window.location.href = "/auth/tiktok/login";
    });
    syncPreview();
  }

  window.CrashoutClipStudio = { mount };
})();
