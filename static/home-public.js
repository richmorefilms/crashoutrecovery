/**
 * Public landing — motion accents for showcase cards.
 */
(function () {
  function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    if (!root) return;
    const cards = root.querySelectorAll(".v16-showcase-card");
    cards.forEach((card, i) => {
      card.style.animationDelay = `${i * 60}ms`;
      card.classList.add("unified-card", "neon-card");
    });
  }

  window.CrashoutHomePublic = { mount };
})();
