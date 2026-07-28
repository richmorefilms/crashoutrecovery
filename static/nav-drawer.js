/**
 * Responsive nav drawer — toggle shell + re-bind TikTok OAuth links.
 */
(function () {
  const DRAWER_ID = "app-nav-drawer";
  const TOGGLE_ID = "app-nav-toggle";
  const BACKDROP_ID = "app-nav-drawer-backdrop";
  const CLOSE_ID = "app-nav-drawer-close";

  let open = false;

  function els() {
    return {
      drawer: document.getElementById(DRAWER_ID),
      toggle: document.getElementById(TOGGLE_ID),
      backdrop: document.getElementById(BACKDROP_ID),
      closeBtn: document.getElementById(CLOSE_ID),
    };
  }

  function rebindTikTokOAuth() {
    const { drawer } = els();
    if (!drawer || !window.CrashoutTikTokAuth?.bindLinks) return;
    // Avoid stacking duplicate click handlers on repeated open()
    if (drawer.dataset.tiktokOauthBound === "1") return;
    window.CrashoutTikTokAuth.bindLinks(drawer);
    drawer.dataset.tiktokOauthBound = "1";
  }

  function setOpen(next) {
    const { drawer, toggle, backdrop } = els();
    if (!drawer || !toggle) return;
    open = Boolean(next);
    drawer.hidden = !open;
    drawer.setAttribute("aria-hidden", open ? "false" : "true");
    drawer.classList.toggle("app-nav-drawer--open", open);
    if (backdrop) {
      backdrop.hidden = !open;
      backdrop.classList.toggle("app-nav-drawer-backdrop--open", open);
    }
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("app-nav-drawer-open", open);
    if (open) {
      rebindTikTokOAuth();
      drawer.querySelector("a, button")?.focus?.();
    } else {
      toggle.focus?.();
    }
  }

  function toggleDrawer() {
    setOpen(!open);
  }

  function closeDrawer() {
    setOpen(false);
  }

  function onDocClick(ev) {
    const t = ev.target;
    if (!(t instanceof Element)) return;

    if (t.closest?.("[data-nav-open-ops]")) {
      closeDrawer();
      document.getElementById("ops-help-open")?.click();
      return;
    }
    if (t.closest?.("[data-nav-open-auth]")) {
      closeDrawer();
      if (window.CrashoutAuth?.openModal) {
        window.CrashoutAuth.openModal("login");
      } else {
        document.getElementById("auth-open-btn")?.click();
      }
    }
  }

  function init() {
    const { drawer, toggle, backdrop, closeBtn } = els();
    if (!drawer || !toggle) return;

    toggle.addEventListener("click", toggleDrawer);
    closeBtn?.addEventListener("click", closeDrawer);
    backdrop?.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && open) closeDrawer();
    });
    document.addEventListener("click", onDocClick);
    // Initial bind for any data-tiktok-oauth already in drawer
    rebindTikTokOAuth();
  }

  document.addEventListener("DOMContentLoaded", init);

  window.CrashoutNavDrawer = {
    open: () => setOpen(true),
    close: closeDrawer,
    toggle: toggleDrawer,
    rebindTikTokOAuth,
  };
})();
