/**
 * Crashout Recovery PWA — register SW + neon install prompt.
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiTip = (key, fallback) => window.CrashoutUICopy?.tooltip?.(key) || fallback;

  let deferredPrompt = null;

  function ensureUi() {
    if (document.getElementById("pwa-install-root")) return;

    const root = document.createElement("div");
    root.id = "pwa-install-root";
    root.className = "pwa-install-root";
    root.innerHTML = `
      <button type="button" class="pwa-install-fab neon-btn" id="pwa-install-open" hidden>
        ${escapeHtml(uiLabel("pwa_install", "Install Crashout Recovery"))}
      </button>
      <div class="pwa-install-modal" id="pwa-install-modal" hidden role="dialog" aria-modal="true" aria-labelledby="pwa-install-title">
        <div class="pwa-install-card holo-card">
          <h2 id="pwa-install-title" class="pwa-install-title">${escapeHtml(uiLabel("pwa_install", "Install Crashout Recovery"))}</h2>
          <p class="pwa-install-copy">${escapeHtml(uiTip("pwa_install", "Add Crashout Recovery to your home screen for a full-screen neon creator app."))}</p>
          <div class="pwa-install-actions">
            <button type="button" class="home-btn" id="pwa-install-confirm">${escapeHtml(uiLabel("pwa_install_confirm", "INSTALL"))}</button>
            <button type="button" class="home-btn" id="pwa-install-dismiss">${escapeHtml(uiLabel("pwa_install_dismiss", "LATER"))}</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(root);

    const openBtn = document.getElementById("pwa-install-open");
    const modal = document.getElementById("pwa-install-modal");
    const confirmBtn = document.getElementById("pwa-install-confirm");
    const dismissBtn = document.getElementById("pwa-install-dismiss");

    openBtn?.addEventListener("click", () => {
      if (modal) modal.hidden = false;
    });
    dismissBtn?.addEventListener("click", () => {
      if (modal) modal.hidden = true;
      try {
        localStorage.setItem("crashout_pwa_dismissed", "1");
      } catch (_) {
        /* ignore */
      }
      if (openBtn) openBtn.hidden = true;
    });
    confirmBtn?.addEventListener("click", async () => {
      if (!deferredPrompt) {
        if (modal) modal.hidden = true;
        return;
      }
      deferredPrompt.prompt();
      try {
        await deferredPrompt.userChoice;
      } catch (_) {
        /* ignore */
      }
      deferredPrompt = null;
      if (modal) modal.hidden = true;
      if (openBtn) openBtn.hidden = true;
    });
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showInstallFab() {
    try {
      if (localStorage.getItem("crashout_pwa_dismissed") === "1") return;
    } catch (_) {
      /* ignore */
    }
    if (window.matchMedia("(display-mode: standalone)").matches) return;
    if (window.navigator.standalone === true) return;
    const openBtn = document.getElementById("pwa-install-open");
    if (openBtn) openBtn.hidden = false;
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* offline or unsupported — ignore */
    });
  }

  function init() {
    ensureUi();
    registerServiceWorker();

    window.addEventListener("beforeinstallprompt", (ev) => {
      ev.preventDefault();
      deferredPrompt = ev;
      showInstallFab();
    });

    window.addEventListener("appinstalled", () => {
      deferredPrompt = null;
      const openBtn = document.getElementById("pwa-install-open");
      const modal = document.getElementById("pwa-install-modal");
      if (openBtn) openBtn.hidden = true;
      if (modal) modal.hidden = true;
    });

    // iOS / browsers without beforeinstallprompt — still show soft tip occasionally
    const isIos =
      /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
    if (isIos && window.navigator.standalone !== true) {
      showInstallFab();
      const confirmBtn = document.getElementById("pwa-install-confirm");
      if (confirmBtn) {
        confirmBtn.addEventListener(
          "click",
          () => {
            const copy = document.querySelector(".pwa-install-copy");
            if (copy) {
              copy.textContent = uiTip(
                "pwa_ios_hint",
                "On iPhone: Share → Add to Home Screen."
              );
            }
          },
          { once: true }
        );
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.CrashoutPwa = { init, registerServiceWorker };
})();
