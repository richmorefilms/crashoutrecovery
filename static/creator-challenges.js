/**
 * Neon Creator Challenges — weekly missions
 */
(function () {
  const KEY = "crashout_creator_challenges";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const MISSIONS = [
    { id: "publish_3", titleKey: "challenge_publish", fallback: "Publish 3 clips", target: 3, href: "/publish" },
    { id: "explore_2", titleKey: "challenge_clusters", fallback: "Explore 2 clusters", target: 2, href: "/topics" },
    { id: "boost_1", titleKey: "challenge_opportunity", fallback: "Boost 1 opportunity", target: 1, href: "/topics/radar" },
    { id: "streak", titleKey: "challenge_streak", fallback: "Maintain consistency streak", target: 5, href: "/recovery/mode" },
  ];

  function weekId() {
    const d = new Date();
    const onejan = new Date(d.getFullYear(), 0, 1);
    const week = Math.ceil(((d - onejan) / 86400000 + onejan.getDay() + 1) / 7);
    return `${d.getFullYear()}-W${week}`;
  }

  function load() {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY) || "{}") || {};
      if (raw.week !== weekId()) return { week: weekId(), progress: {} };
      return raw;
    } catch (_) {
      return { week: weekId(), progress: {} };
    }
  }

  function save(data) {
    try {
      localStorage.setItem(KEY, JSON.stringify(data));
    } catch (_) {
      /* ignore */
    }
  }

  function mount() {
    const root = document.getElementById("challenges-list-root");
    if (!root) return;
    let state = load();
    save(state);

    function paint() {
      root.innerHTML = MISSIONS.map((m) => {
        const current = Number(state.progress[m.id] || 0);
        const pct = Math.min(100, Math.round((current / m.target) * 100));
        const done = current >= m.target;
        return `
          <article class="holo-card challenge-card ${done ? "challenge-card--done" : ""}" data-id="${escapeHtml(m.id)}">
            <h3 class="neon-title">${escapeHtml(uiLabel(m.titleKey, m.fallback))}</h3>
            <div class="stat-meter" style="--stat:${pct}"><div class="stat-meter-fill"></div></div>
            <p class="expand-sub">${current} / ${m.target}</p>
            <div class="home-actions">
              <button type="button" class="home-btn" data-tick="${escapeHtml(m.id)}">${escapeHtml(uiLabel("challenge_tick", "LOG PROGRESS"))}</button>
              <a class="home-btn" href="${escapeHtml(m.href)}">${escapeHtml(uiLabel("challenge_go", "GO"))}</a>
            </div>
          </article>`;
      }).join("");
    }

    root.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-tick]");
      if (!btn) return;
      const id = btn.getAttribute("data-tick");
      const mission = MISSIONS.find((m) => m.id === id);
      if (!mission) return;
      const next = Math.min(mission.target, Number(state.progress[id] || 0) + 1);
      state.progress[id] = next;
      save(state);
      if (next >= mission.target) {
        window.CrashoutCreatorBadges?.earn?.("growth");
        window.CrashoutNotifications?.toast?.(uiLabel("challenge_complete", "Mission complete"));
      }
      paint();
    });

    paint();
  }

  window.CrashoutCreatorChallenges = { mount };
})();
