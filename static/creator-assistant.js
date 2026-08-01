/**
 * Neon AI Assistant — Creator Copilot via /api/suggest + local templates
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

  const PRESETS = {
    idea: "Give me one uplifting creator clip idea I can film today.",
    script: "Draft a short calm script for a 20-second recovery redirect clip.",
    thumb: "Suggest a neon thumbnail prompt for a consistency tip video.",
    recover: "I feel close to a crashout. One small accountable next step.",
    earn: "Suggest one monetization lane move that stays creator-friendly.",
  };

  async function suggest(text) {
    const res = await fetch("/api/suggest", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, tone: "calm" }),
    });
    if (!res.ok) throw new Error(`Assistant failed (${res.status})`);
    return res.json();
  }

  function localFallback(kind, text) {
    const map = {
      idea: "Film one 15s clip: name the spike, then one reversible next move.",
      script: "Hook: “Pause.” Body: one breath. CTA: save the draft, don’t delete.",
      thumb: "Orbitron title on dark glass: “One small move.” Cyan ring, magenta glow.",
      recover: "Reset the tab. Drink water. Rewrite the post as a private note.",
      earn: "Check Ads lane readiness, then ship one Shorts CTA to Launchpad.",
    };
    return map[kind] || `Keep it upliftment-first: ${text.slice(0, 120)}`;
  }

  function mount() {
    const input = document.getElementById("assistant-input");
    const output = document.getElementById("assistant-output");
    const run = document.getElementById("assistant-run");
    let kind = "idea";

    document.querySelectorAll("[data-assist]").forEach((btn) => {
      btn.addEventListener("click", () => {
        kind = btn.getAttribute("data-assist") || "idea";
        if (input) input.value = PRESETS[kind] || "";
      });
    });

    run?.addEventListener("click", async () => {
      const text = (input?.value || "").trim() || PRESETS[kind];
      if (output) output.innerHTML = `<p class="expand-sub">${escapeHtml(uiLabel("assist_thinking", "Thinking…"))}</p>`;
      try {
        const data = await suggest(text);
        const suggestion =
          data.suggestion ||
          data.redirect ||
          data.message ||
          data.items?.[0]?.text ||
          localFallback(kind, text);
        const tone = data.tone || "calm";
        if (output) {
          output.innerHTML = `
            <article class="holo-card">
              <h3 class="neon-title">${escapeHtml(uiLabel("assist_result", "Copilot reply"))}</h3>
              <p class="expand-sub">${escapeHtml(String(suggestion))}</p>
              <p class="radar-strength">${escapeHtml(tone)}</p>
            </article>`;
        }
        window.CrashoutCreatorBadges?.earn?.("creativity");
      } catch (_) {
        if (output) {
          output.innerHTML = `
            <article class="holo-card">
              <h3 class="neon-title">${escapeHtml(uiLabel("assist_result", "Copilot reply"))}</h3>
              <p class="expand-sub">${escapeHtml(localFallback(kind, text))}</p>
            </article>`;
        }
      }
    });
  }

  window.CrashoutCreatorAssistant = { mount };
})();
