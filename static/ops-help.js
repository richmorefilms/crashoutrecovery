/**
 * Help / Ops panel — modes, options, how-to walkthrough.
 * Links into tabs, composer, monetization scaffolding.
 */
(function () {
  let modalEl;
  let lastFocusEl = null;

  function getModal() {
    return modalEl || (modalEl = document.getElementById("ops-help-modal"));
  }

  function showSection(sectionId) {
    document.querySelectorAll(".ops-help-nav-btn").forEach((btn) => {
      const on = btn.dataset.opsSection === sectionId;
      btn.classList.toggle("ops-help-nav-btn--active", on);
    });

    document.querySelectorAll("[data-ops-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.opsPanel !== sectionId;
    });
  }

  function open(sectionId) {
    const modal = getModal();
    if (!modal) return;

    lastFocusEl = document.activeElement;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("ops-help-open");
    showSection(sectionId || "overview");
    window.CrashoutVideos?.fillHelpShelves?.();

    window.setTimeout(() => {
      modal.querySelector(".ops-help-nav-btn--active")?.focus();
    }, 80);
  }

  function close() {
    const modal = getModal();
    if (!modal) return;

    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("ops-help-open");

    if (lastFocusEl && typeof lastFocusEl.focus === "function") {
      lastFocusEl.focus();
    } else {
      document.getElementById("ops-help-open")?.focus();
    }
  }

  function resetDemoData() {
    try {
      localStorage.removeItem("crashout_recovery");
      localStorage.removeItem("crashout_seeds");
      localStorage.removeItem("crashout_market_packs");
      localStorage.removeItem("crashout_world_signals");
    } catch (_) {
      /* ignore */
    }
    window.location.reload();
  }

  function runAction(action, el) {
    if (action === "section") {
      showSection(el.dataset.opsSection || "overview");
      return;
    }

    if (action === "lane") {
      const lane = el.dataset.lane;
      close();
      window.setTimeout(() => {
        window.CrashoutTabbedFeed?.switchLane?.(lane);
      }, 60);
      return;
    }

    if (action === "compose") {
      close();
      window.setTimeout(() => {
        window.CrashoutComposerModal?.open?.();
      }, 60);
      return;
    }

    if (action === "tier") {
      const tier = el.dataset.tier || "basic";
      window.CrashoutMonetization?.setTier?.(tier);
      return;
    }

    if (action === "upgrade") {
      close();
      window.setTimeout(() => {
        window.CrashoutMonetization?.openUpgrade?.(el.dataset.tier || "creator");
      }, 60);
      return;
    }

    if (action === "reset-demo") {
      if (
        window.confirm(
          "Reset this browser's recovery, draft, and signal caches, then reload? Account data may sync back if you remain logged in."
        )
      ) {
        resetDemoData();
      }
    }
  }

  function handleClick(e) {
    if (e.target.closest("#ops-help-open")) {
      e.preventDefault();
      open("modes");
      return;
    }

    if (e.target.closest("[data-close-ops-help]")) {
      e.preventDefault();
      close();
      return;
    }

    const nav = e.target.closest("[data-ops-section]");
    if (nav) {
      e.preventDefault();
      showSection(nav.dataset.opsSection);
      return;
    }

    const actionBtn = e.target.closest("[data-ops-action]");
    if (actionBtn) {
      e.preventDefault();
      runAction(actionBtn.dataset.opsAction, actionBtn);
    }
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && document.body.classList.contains("ops-help-open")) {
      e.preventDefault();
      close();
    }
  }

  function init() {
    modalEl = document.getElementById("ops-help-modal");
    document.body.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeydown);

    if (window.location.hash === "#ops" || window.location.hash === "#help") {
      open("overview");
    }
  }

  window.CrashoutOpsHelp = {
    open,
    close,
    showSection,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
