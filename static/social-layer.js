/**
 * Neon Social Layer — follow + signal boost (upliftment only)
 */
(function () {
  const KEY = "crashout_social_follows";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const CREATORS = [
    { id: "calm_craft", name: "Calm Craft", blurb: "Soft redirects, steady clips." },
    { id: "momentum_lab", name: "Momentum Lab", blurb: "Weekly consistency experiments." },
    { id: "uplift_desk", name: "Uplift Desk", blurb: "Accountability without shame." },
    { id: "galaxy_notes", name: "Galaxy Notes", blurb: "Topic clusters made kind." },
  ];

  function loadFollows() {
    try {
      const rows = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(rows) ? rows : [];
    } catch (_) {
      return [];
    }
  }

  function saveFollows(rows) {
    try {
      localStorage.setItem(KEY, JSON.stringify(rows));
    } catch (_) {
      /* ignore */
    }
  }

  function mount() {
    const creatorsRoot = document.getElementById("social-creators-root");
    const signalsRoot = document.getElementById("social-signals-root");
    let follows = loadFollows();

    function paint() {
      if (creatorsRoot) {
        creatorsRoot.innerHTML = CREATORS.map((c) => {
          const on = follows.includes(c.id);
          return `
            <article class="holo-card social-card" data-id="${escapeHtml(c.id)}">
              <h3 class="neon-title">${escapeHtml(c.name)}</h3>
              <p class="expand-sub">${escapeHtml(c.blurb)}</p>
              <button type="button" class="launch-btn ${on ? "launch-btn--boost" : "launch-btn--ready"}" data-follow="${escapeHtml(c.id)}">
                ${escapeHtml(on ? uiLabel("social_following", "FOLLOWING") : uiLabel("social_follow", "FOLLOW"))}
              </button>
              <button type="button" class="launch-btn launch-btn--launch" data-boost="${escapeHtml(c.id)}">
                ${escapeHtml(uiLabel("social_signal_boost", "SIGNAL BOOST"))}
              </button>
            </article>`;
        }).join("");
      }
      if (signalsRoot) {
        const signals = [
          {
            title: uiLabel("social_signal_recovery", "Recovery support"),
            body: "Someone chose Reflect in Recovery Mode — send a quiet uplift.",
          },
          {
            title: uiLabel("social_signal_badge", "Creator achievement"),
            body: "A followed creator unlocked Consistency.",
          },
          {
            title: uiLabel("social_signal_launch", "Launch energy"),
            body: "A peer boosted a clip toward Launchpad.",
          },
        ];
        signalsRoot.innerHTML = signals
          .map(
            (s) => `
          <article class="holo-card notify-card">
            <h3 class="neon-title">${escapeHtml(s.title)}</h3>
            <p class="expand-sub">${escapeHtml(s.body)}</p>
          </article>`
          )
          .join("");
      }
    }

    creatorsRoot?.addEventListener("click", (ev) => {
      const followBtn = ev.target.closest("[data-follow]");
      const boostBtn = ev.target.closest("[data-boost]");
      if (followBtn) {
        const id = followBtn.getAttribute("data-follow");
        if (follows.includes(id)) follows = follows.filter((x) => x !== id);
        else follows.push(id);
        saveFollows(follows);
        paint();
      }
      if (boostBtn) {
        window.CrashoutNotifications?.toast?.(uiLabel("social_boosted", "Signal boost sent"));
        window.CrashoutCreatorBadges?.earn?.("community");
      }
    });

    paint();
  }

  window.CrashoutSocialLayer = { mount };
})();
