/**
 * Neon Recovery Journal — daily hologram reflections + vault sync
 */
(function () {
  const KEY = "crashout_recovery_journal";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function load() {
    try {
      const rows = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(rows) ? rows : [];
    } catch (_) {
      return [];
    }
  }

  function save(rows) {
    try {
      localStorage.setItem(KEY, JSON.stringify(rows.slice(0, 60)));
    } catch (_) {}
  }

  function streak(rows) {
    const days = new Set(rows.map((r) => r.day));
    let n = 0;
    const d = new Date();
    for (;;) {
      const key = d.toISOString().slice(0, 10);
      if (!days.has(key)) break;
      n += 1;
      d.setDate(d.getDate() - 1);
    }
    return n;
  }

  function syncVault(entry) {
    try {
      const vault = JSON.parse(localStorage.getItem("crashout_creator_vault") || "[]");
      const rows = Array.isArray(vault) ? vault : [];
      rows.unshift({
        id: `journal_${entry.id}`,
        title: `Journal ${entry.day}`,
        type: "draft",
        notes: entry.text.slice(0, 280),
        at: Date.now(),
      });
      localStorage.setItem("crashout_creator_vault", JSON.stringify(rows.slice(0, 60)));
    } catch (_) {}
  }

  function mount() {
    const mood = document.getElementById("journal-mood");
    const dial = document.getElementById("journal-mood-dial");
    const moodVal = document.getElementById("journal-mood-value");
    const entry = document.getElementById("journal-entry");
    const saveBtn = document.getElementById("journal-save");
    const list = document.getElementById("journal-list-root");
    const streakEl = document.getElementById("journal-streak");
    let rows = load();

    function paintMood() {
      const v = Number(mood?.value || 55);
      if (dial) dial.style.setProperty("--score", String(v));
      if (moodVal) moodVal.textContent = String(v);
    }

    function paintList() {
      if (streakEl) {
        streakEl.textContent = `${uiLabel("journal_streak", "Streak Keeper")} · ${streak(rows)}d`;
      }
      if (!list) return;
      if (!rows.length) {
        list.innerHTML = `<p class="creator-hub-note">${escapeHtml(uiLabel("journal_empty", "No entries yet."))}</p>`;
        return;
      }
      list.innerHTML = rows
        .map(
          (r) => `
        <article class="holo-card notify-card">
          <h3 class="neon-title">${escapeHtml(r.day)} · ${escapeHtml(String(r.mood))}</h3>
          <p class="expand-sub">${escapeHtml(r.text)}</p>
        </article>`
        )
        .join("");
    }

    mood?.addEventListener("input", paintMood);
    saveBtn?.addEventListener("click", () => {
      const text = (entry?.value || "").trim();
      if (!text) return;
      const row = {
        id: String(Date.now()),
        day: new Date().toISOString().slice(0, 10),
        mood: Number(mood?.value || 55),
        text,
      };
      rows.unshift(row);
      save(rows);
      syncVault(row);
      if (entry) entry.value = "";
      paintList();
      window.CrashoutNotifications?.toast?.(uiLabel("journal_saved", "Journal saved"));
      window.CrashoutCreatorBadges?.earn?.("recovery");
    });

    paintMood();
    paintList();
  }

  window.CrashoutRecoveryJournal = { mount };
})();
