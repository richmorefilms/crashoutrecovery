/**
 * Neon Developer API Explorer
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

  const ENDPOINTS = [
    { id: "signals", path: "/api/public/feed/signals", labelKey: "api_ep_signals" },
    { id: "topics", path: "/api/public/topics", labelKey: "api_ep_topics" },
    { id: "momentum", path: "/api/public/momentum?creator_id=1", labelKey: "api_ep_momentum" },
    { id: "vault", path: "/api/public/vault/meta", labelKey: "api_ep_vault" },
  ];

  async function mount() {
    const root = document.getElementById("api-explorer-root");
    const out = document.getElementById("api-explorer-out");
    if (!root) return;
    root.innerHTML = ENDPOINTS.map(
      (ep) => `
      <article class="holo-card">
        <h3 class="neon-title">${escapeHtml(uiLabel(ep.labelKey, ep.id))}</h3>
        <p class="expand-sub"><code>${escapeHtml(ep.path)}</code></p>
        <button type="button" class="launch-btn launch-btn--ready" data-api="${escapeHtml(ep.path)}">${escapeHtml(uiLabel("api_try", "TRY"))}</button>
      </article>`
    ).join("");

    root.addEventListener("click", async (ev) => {
      const btn = ev.target.closest("[data-api]");
      if (!btn || !out) return;
      const path = btn.getAttribute("data-api");
      out.textContent = uiLabel("assist_thinking", "Thinking…");
      try {
        const res = await fetch(path, { credentials: "same-origin" });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = String(err?.message || err);
      }
    });
  }

  window.CrashoutDeveloperApi = { mount };
})();
