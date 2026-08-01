/**
 * Creator Home — Neon Welcome Console glow accents
 */
(function () {
  function bindGlow(root) {
    root.querySelectorAll(".home-btn, .home-card").forEach((el) => {
      el.addEventListener("mouseenter", () => {
        el.style.boxShadow = "0 0 20px #ff00ff, 0 0 40px #ff00ff";
      });
      el.addEventListener("mouseleave", () => {
        el.style.boxShadow = "";
      });
    });
  }

  function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    if (!root) return;
    root.setAttribute("data-version", "v16");
    bindGlow(root);
  }

  window.CrashoutCreatorHome = { mount };
})();
