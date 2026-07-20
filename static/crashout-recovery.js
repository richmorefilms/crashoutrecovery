/**
 * Crashout Recovery — tone switcher + modal
 * Usage:
 *   showCrashout("calm")
 *   showCrashout("direct", { mode: "modal" })
 *   showCrashout("humorous", { target: "#my-container" })
 */
(function (global) {
  const VALID_TONES = ["universal", "calm", "humorous", "direct", "strategic"];
  const DEFAULT_TONE = "universal";

  let overlayEl = null;

  function normalizeTone(tone) {
    const key = (tone || DEFAULT_TONE).toLowerCase().trim();
    return VALID_TONES.includes(key) ? key : DEFAULT_TONE;
  }

  async function fetchFragment(tone) {
    const res = await fetch(`/crashout?tone=${encodeURIComponent(tone)}`);
    if (!res.ok) throw new Error(`Failed to load tone: ${tone}`);
    return res.text();
  }

  function ensureOverlay() {
    if (overlayEl) return overlayEl;

    overlayEl = document.createElement("div");
    overlayEl.className = "crashout-overlay";
    overlayEl.setAttribute("role", "dialog");
    overlayEl.setAttribute("aria-modal", "true");
    overlayEl.setAttribute("aria-label", "Crashout Recovery");
    overlayEl.innerHTML = `
      <div class="crashout-sheet">
        <div class="crashout-sheet-header">
          <button type="button" class="crashout-sheet-close" aria-label="Close">&times;</button>
        </div>
        <div class="crashout-sheet-body"></div>
      </div>
    `;

    overlayEl.querySelector(".crashout-sheet-close").addEventListener("click", closeModal);
    overlayEl.addEventListener("click", (e) => {
      if (e.target === overlayEl) closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlayEl.classList.contains("open")) closeModal();
    });

    document.body.appendChild(overlayEl);
    return overlayEl;
  }

  function openModal(html) {
    const overlay = ensureOverlay();
    overlay.querySelector(".crashout-sheet-body").innerHTML = html;
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    if (!overlayEl) return;
    overlayEl.classList.remove("open");
    document.body.style.overflow = "";
  }

  async function showCrashout(tone, options = {}) {
    const selected = normalizeTone(tone);
    const html = await fetchFragment(selected);

    if (options.mode === "modal") {
      openModal(html);
      return selected;
    }

    const target =
      typeof options.target === "string"
        ? document.querySelector(options.target)
        : options.target || document.getElementById("crashout-container");

    if (target) {
      target.innerHTML = html;
    }

    if (options.onLoad) options.onLoad(selected, html);
    return selected;
  }

  global.CrashoutRecovery = {
    show: showCrashout,
    close: closeModal,
    tones: VALID_TONES,
    defaultTone: DEFAULT_TONE,
  };

  global.showCrashout = showCrashout;
})(window);
