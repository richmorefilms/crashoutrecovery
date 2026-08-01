/**
 * Neon suite — touch glow for hologram cards on small screens.
 */
(function () {
  function bindTouchGlow() {
    if (!window.matchMedia("(max-width: 768px)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const cards = document.querySelectorAll(
      ".holo-card, .planet-card, .dash-card, .home-card, .earn-card, .meter-card, .stat-panel, .idea-card"
    );

    cards.forEach((card) => {
      card.addEventListener(
        "touchstart",
        () => {
          card.style.boxShadow = "0 0 20px #00eaff, 0 0 40px #ff00ff";
        },
        { passive: true }
      );
      card.addEventListener(
        "touchend",
        () => {
          card.style.boxShadow = "";
        },
        { passive: true }
      );
      card.addEventListener(
        "touchcancel",
        () => {
          card.style.boxShadow = "";
        },
        { passive: true }
      );
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindTouchGlow);
  } else {
    bindTouchGlow();
  }

  window.CrashoutNeonMobile = { bindTouchGlow };
})();
