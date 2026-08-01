/**
 * Publish readiness — Neon Launchpad Edition (CrashoutRecovery v16).
 */
(function () {
  function bindLaunchPulse(root) {
    root.querySelectorAll(".launch-btn, .idea-card").forEach((el) => {
      el.addEventListener("mouseenter", () => {
        el.classList.add("is-glowing");
      });
      el.addEventListener("mouseleave", () => {
        el.classList.remove("is-glowing");
      });
    });
  }

  function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    if (!root) return;
    root.setAttribute("data-version", "v16");
    root.classList.add("launchpad-armed");

    const items = root.querySelectorAll(".publish-checklist li");
    items.forEach((li, i) => {
      li.style.animationDelay = `${i * 50}ms`;
      li.classList.add("unified-card", "neon-card", "checklist-chip");
    });

    bindLaunchPulse(root);
  }

  window.CrashoutPublish = { mount };
})();
