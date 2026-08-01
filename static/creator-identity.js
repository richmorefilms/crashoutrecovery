/**
 * Neon Creator Identity — local profile hologram
 */
(function () {
  const KEY = "crashout_creator_identity";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

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

  function streakDays() {
    try {
      const recovery = JSON.parse(localStorage.getItem("crashout_recovery") || "{}");
      return Number(recovery.streak_days || recovery.streak || 0) || 0;
    } catch (_) {
      return 0;
    }
  }

  function badgeCount() {
    try {
      return Object.keys(JSON.parse(localStorage.getItem("crashout_creator_badges") || "{}")).length;
    } catch (_) {
      return 0;
    }
  }

  function mount() {
    const nameEl = document.getElementById("identity-name");
    const bioEl = document.getElementById("identity-bio");
    const linksEl = document.getElementById("identity-links");
    const saveBtn = document.getElementById("identity-save");
    const levelDial = document.getElementById("identity-level-dial");
    const levelVal = document.getElementById("identity-level-value");
    const streakVal = document.getElementById("identity-streak-value");
    const data = load();

    if (nameEl) nameEl.value = data.name || "";
    if (bioEl) bioEl.value = data.bio || "";
    if (linksEl) linksEl.value = data.links || "";

    const streak = streakDays();
    const badges = badgeCount();
    const level = Math.max(1, Math.min(99, 1 + badges + Math.floor(streak / 3)));
    const pct = Math.min(100, level * 8);
    if (levelDial) levelDial.style.setProperty("--score", String(pct));
    if (levelVal) levelVal.textContent = String(level);
    if (streakVal) streakVal.textContent = String(streak);

    saveBtn?.addEventListener("click", () => {
      save({
        name: nameEl?.value?.trim() || "",
        bio: bioEl?.value?.trim() || "",
        links: linksEl?.value?.trim() || "",
        updated: Date.now(),
      });
      window.CrashoutNotifications?.toast?.(uiLabel("identity_saved", "Identity saved"));
      window.CrashoutCreatorBadges?.earn?.("community");
    });
  }

  window.CrashoutCreatorIdentity = { mount };
})();
