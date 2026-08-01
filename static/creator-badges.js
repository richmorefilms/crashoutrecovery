/**
 * Neon Creator Badges — local achievement shelf
 */
(function () {
  const KEY = "crashout_creator_badges";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const CATALOG = [
    { id: "consistency", icon: "📅", labelKey: "badge_consistency", fallback: "Consistency" },
    { id: "growth", icon: "📈", labelKey: "badge_growth", fallback: "Growth" },
    { id: "creativity", icon: "✨", labelKey: "badge_creativity", fallback: "Creativity" },
    { id: "recovery", icon: "🛡️", labelKey: "badge_recovery", fallback: "Recovery" },
    { id: "community", icon: "🤝", labelKey: "badge_community", fallback: "Community" },
  ];

  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "{}") || {};
    } catch (_) {
      return {};
    }
  }

  function save(data) {
    try {
      localStorage.setItem(KEY, JSON.stringify(data));
    } catch (_) {
      /* ignore */
    }
  }

  function earn(id) {
    const data = load();
    const today = new Date().toISOString().slice(0, 10);
    if (!data[id]) data[id] = { earned: true, at: today };
    data[id].last = today;
    save(data);
    return data;
  }

  function mount() {
    const root = document.getElementById("badges-shelf-root");
    const earnedToday = document.getElementById("badges-earned-today");
    if (!root) return;
    // Seed soft progress so shelf never feels empty
    const data = load();
    if (!Object.keys(data).length) {
      earn("consistency");
      earn("community");
    }
    const today = new Date().toISOString().slice(0, 10);
    let anyToday = false;
    root.innerHTML = CATALOG.map((b) => {
      const row = data[b.id];
      const unlocked = Boolean(row?.earned);
      if (row?.last === today || row?.at === today) anyToday = true;
      return `
        <article class="holo-card badge-card ${unlocked ? "badge-card--earned" : "badge-card--locked"}" data-badge="${escapeHtml(b.id)}">
          <span class="badge-icon" aria-hidden="true">${b.icon}</span>
          <h3 class="neon-title">${escapeHtml(uiLabel(b.labelKey, b.fallback))}</h3>
          <p class="expand-sub">${unlocked ? escapeHtml(uiLabel("badge_unlocked", "Unlocked")) : escapeHtml(uiLabel("badge_locked", "Keep going"))}</p>
        </article>`;
    }).join("");
    if (earnedToday) earnedToday.hidden = !anyToday;
  }

  window.CrashoutCreatorBadges = { mount, earn };
})();
