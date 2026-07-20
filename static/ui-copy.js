/**
 * User-facing copy — labels + tooltips from UI_COPY.json.
 * Do not use for localStorage keys or module identifiers.
 */
(function () {
  const FALLBACK = {
    pulse_strip: {
      label: "Signal bar",
      tooltip: "Shows the current world mood. Tap to jump to Signals.",
    },
    composer: {
      label: "Draft box",
      tooltip: "Type your thought here and get vibe suggestions.",
    },
    seed: {
      label: "Draft idea",
      tooltip: "A safe, reversible version of your post.",
    },
    tone_pills: {
      label: "Tone buttons",
      tooltip: "Choose the vibe: calm, funny, direct, strategic.",
    },
    momentum_cta: {
      label: "Suggested next step",
      tooltip: "The app’s recommended action after reading your tone.",
    },
    recovery_streak: {
      label: "Win streak",
      tooltip: "Your count of consecutive days making safe moves.",
    },
    momentum_score: {
      label: "Progress meter",
      tooltip: "Shows how steady your habits are (0–100).",
    },
    bad_decision_predictor: {
      label: "Risk check",
      tooltip: "Warns if your draft looks risky and suggests a safer move.",
    },
    signals_pro: {
      label: "World trends",
      tooltip: "Today’s signals plus forecasts and burnout clusters (Pro).",
    },
    marketplace_packs: {
      label: "Add-on tools",
      tooltip: "Extra tone styles, CTA buttons, and draft templates.",
    },
    premium_tiers: {
      label: "Unlock levels",
      tooltip: "Free vs. paid features (Basic, Plus, Creator, Pro).",
    },
    global_spike_alert: {
      label: "World flash",
      tooltip: "Flashes when the world mood spikes high.",
    },
    auth: {
      label: "Account",
      tooltip: "Sign in to sync draft ideas and unlock levels across sessions.",
    },
    auth_login: {
      label: "Log in",
      tooltip: "Sign in with your username or email.",
    },
    auth_register: {
      label: "Create account",
      tooltip: "Register with a username, email, and password.",
    },
    auth_logout: {
      label: "Log out",
      tooltip: "Sign out and clear this device’s session token.",
    },
  };

  let copy = { ...FALLBACK };

  function readEmbedded() {
    const el = document.getElementById("ui-copy-data");
    if (!el?.textContent?.trim()) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (_) {
      return null;
    }
  }

  function merge(data) {
    if (!data || typeof data !== "object") return;
    Object.keys(data).forEach((key) => {
      const entry = data[key];
      if (!entry || typeof entry !== "object") return;
      copy[key] = {
        label: entry.label || FALLBACK[key]?.label || key,
        tooltip: entry.tooltip || FALLBACK[key]?.tooltip || "",
      };
    });
  }

  function get(key, field) {
    const entry = copy[key] || FALLBACK[key];
    if (!entry) return field === "tooltip" ? "" : key;
    if (field === "tooltip") return entry.tooltip || "";
    return entry.label || key;
  }

  function label(key) {
    return get(key, "label");
  }

  function tooltip(key) {
    return get(key, "tooltip");
  }

  /** Lowercase label for mid-sentence use */
  function labelLower(key) {
    const text = label(key);
    if (!text) return text;
    return text.charAt(0).toLowerCase() + text.slice(1);
  }

  function applyDom(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-ui-copy]").forEach((el) => {
      const key = el.getAttribute("data-ui-copy");
      const field = el.getAttribute("data-ui-field") || "label";
      const attr = el.getAttribute("data-ui-attr");
      const value = get(key, field);
      if (!value) return;
      if (attr) {
        el.setAttribute(attr, value);
      } else {
        el.textContent = value;
      }
    });
  }

  function init() {
    merge(readEmbedded());
    applyDom();
  }

  window.CrashoutUICopy = {
    get,
    label,
    labelLower,
    tooltip,
    applyDom,
    all: () => ({ ...copy }),
    reload: (data) => {
      merge(data);
      applyDom();
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
