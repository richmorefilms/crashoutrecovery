/**
 * Neon Recovery Mode — local accountability console (zero stigma)
 */
(function () {
  const KEY = "crashout_recovery_mode";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function loadState() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "{}") || {};
    } catch (_) {
      return {};
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (_) {
      /* ignore */
    }
  }

  const STORIES = [
    { title: "One pause, one win", body: "You chose the draft over the spiral." },
    { title: "Consistency over chaos", body: "Showing up small still counts." },
    { title: "Forward only", body: "Accountability without shame is power." },
  ];

  function mount() {
    const note = document.getElementById("recovery-checkin-note");
    const dial = document.getElementById("recovery-consistency-dial");
    const value = document.getElementById("recovery-consistency-value");
    const uplift = document.getElementById("recovery-uplift-root");
    const state = loadState();
    let score = Number(state.consistency) || 40;

    function paint() {
      score = Math.max(0, Math.min(100, score));
      if (dial) dial.style.setProperty("--score", String(score));
      if (value) value.textContent = String(score);
      saveState({ ...state, consistency: score, last: state.last || null });
    }

    document.querySelectorAll("[data-recovery-act]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const act = btn.getAttribute("data-recovery-act");
        if (act === "reset") score = Math.max(20, score - 5);
        if (act === "reflect") score = Math.min(100, score + 4);
        if (act === "rebuild") score = Math.min(100, score + 8);
        state.last = act;
        state.day = new Date().toISOString().slice(0, 10);
        if (note) {
          note.textContent =
            act === "reset"
              ? uiLabel("recovery_reset_done", "Reset noted. Soft landing.")
              : act === "reflect"
                ? uiLabel("recovery_reflect_done", "Reflection logged. Clear eyes.")
                : uiLabel("recovery_rebuild_done", "Rebuild move locked. Forward.");
        }
        paint();
        try {
          window.CrashoutCreatorBadges?.earn?.("recovery");
          window.CrashoutNotifications?.push?.({
            kind: "recovery",
            title: uiLabel("recovery_mode", "Recovery Mode"),
            body: note?.textContent || "",
          });
        } catch (_) {
          /* optional bridges */
        }
      });
    });

    if (uplift) {
      uplift.innerHTML = STORIES.map(
        (s) => `
        <article class="holo-card">
          <h3 class="neon-title">${escapeHtml(s.title)}</h3>
          <p class="expand-sub">${escapeHtml(s.body)}</p>
        </article>`
      ).join("");
    }
    paint();
  }

  window.CrashoutRecoveryMode = { mount };
})();
