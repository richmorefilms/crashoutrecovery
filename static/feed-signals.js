/**
 * Neon Creator Feed 2.0 — cross-platform signals
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function localExtras() {
    const extras = [];
    try {
      const vault = JSON.parse(localStorage.getItem("crashout_creator_vault") || "[]");
      if (Array.isArray(vault) && vault[0]) {
        extras.push({
          kind: "vault",
          title: uiLabel("sig_local_vault", "Vault upload"),
          body: vault[0].title || "Draft saved",
          strength: 60,
        });
      }
    } catch (_) {}
    try {
      const identity = JSON.parse(localStorage.getItem("crashout_creator_identity") || "{}");
      if (identity.name) {
        extras.push({
          kind: "identity",
          title: uiLabel("sig_local_identity", "Identity update"),
          body: identity.name,
          strength: 55,
        });
      }
    } catch (_) {}
    try {
      const challenges = JSON.parse(localStorage.getItem("crashout_creator_challenges") || "{}");
      const progress = challenges.progress || {};
      const done = Object.values(progress).some((n) => Number(n) > 0);
      if (done) {
        extras.push({
          kind: "challenge",
          title: uiLabel("sig_local_challenge", "Challenge progress"),
          body: uiLabel("challenge_tick", "LOG PROGRESS"),
          strength: 62,
        });
      }
    } catch (_) {}
    return extras;
  }

  function setPulse(on) {
    document.querySelectorAll(".creator-pulse").forEach((el) => {
      el.hidden = !on;
      el.classList.toggle("nav-pulse--on", Boolean(on));
    });
  }

  async function mount() {
    const list = document.getElementById("feed-signals-list");
    const meter = document.getElementById("signal-strength-meter");
    const meterVal = document.getElementById("signal-strength-value");
    const errEl = document.getElementById("feed-signals-error");
    try {
      const res = await fetch("/api/public/feed/signals", { credentials: "same-origin" });
      if (!res.ok) throw new Error(`Signals failed (${res.status})`);
      const data = await res.json();
      const items = [...(data.items || []), ...localExtras()];
      const avg = Math.round(
        items.reduce((s, i) => s + Number(i.strength || 50), 0) / Math.max(1, items.length)
      );
      if (meter) meter.style.setProperty("--stat", String(avg));
      if (meterVal) meterVal.textContent = `${avg}%`;
      if (list) {
        list.innerHTML = items
          .map(
            (i) => `
          <article class="holo-card notify-card">
            <h3 class="neon-title">${escapeHtml(i.title || i.kind || "Signal")}</h3>
            <p class="expand-sub">${escapeHtml(i.body || i.kind || "")}</p>
            <p class="radar-strength">${escapeHtml(String(i.strength || "—"))}% ${escapeHtml(uiLabel("signal_strength", "Signal Strength"))}</p>
          </article>`
          )
          .join("");
      }
      setPulse(items.length > 0);
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Signals offline.";
      }
    }
  }

  function initPulse() {
    setPulse(true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPulse);
  } else {
    initPulse();
  }

  window.CrashoutFeedSignals = { mount };
})();
