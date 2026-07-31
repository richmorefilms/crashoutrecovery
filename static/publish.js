/**
 * Publish readiness — CrashoutRecovery v16 checklist accents.
 */
(function () {
  function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    if (!root) return;
    root.setAttribute("data-version", "v16");
    const items = root.querySelectorAll(".publish-checklist li");
    items.forEach((li, i) => {
      li.style.animationDelay = `${i * 50}ms`;
      li.classList.add("unified-card", "neon-card");
    });
  }

  window.CrashoutPublish = { mount };
})();
