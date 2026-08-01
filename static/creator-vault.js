/**
 * Neon Creator Vault — local cloud shell (PWA-friendly)
 */
(function () {
  const KEY = "crashout_creator_vault";
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
    } catch (_) {
      /* ignore */
    }
  }

  function mount() {
    const root = document.getElementById("vault-files-root");
    const title = document.getElementById("vault-title");
    const type = document.getElementById("vault-type");
    const notes = document.getElementById("vault-notes");
    const add = document.getElementById("vault-add");
    if (!root) return;
    let rows = load();

    function paint() {
      if (!rows.length) {
        root.innerHTML = `<p class="creator-hub-note">${escapeHtml(uiLabel("vault_empty", "Vault is empty — add a draft."))}</p>`;
        return;
      }
      root.innerHTML = rows
        .map(
          (f) => `
        <article class="holo-card vault-card" data-id="${escapeHtml(f.id)}">
          <h3 class="neon-title">${escapeHtml(f.title)}</h3>
          <p class="expand-sub">${escapeHtml((f.type || "draft").toUpperCase())}</p>
          <p class="expand-sub">${escapeHtml(f.notes || "")}</p>
          <button type="button" class="home-btn" data-remove="${escapeHtml(f.id)}">${escapeHtml(uiLabel("vault_remove", "REMOVE"))}</button>
        </article>`
        )
        .join("");
    }

    add?.addEventListener("click", () => {
      const t = (title?.value || "").trim() || uiLabel("vault_untitled", "Untitled draft");
      rows.unshift({
        id: `v_${Date.now()}`,
        title: t,
        type: type?.value || "draft",
        notes: notes?.value?.trim() || "",
        at: Date.now(),
      });
      save(rows);
      if (title) title.value = "";
      if (notes) notes.value = "";
      paint();
      window.CrashoutNotifications?.toast?.(uiLabel("vault_saved", "Saved to vault"));
      window.CrashoutCreatorChallenges?.mount?.(); // no-op if not on page
    });

    root.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-remove]");
      if (!btn) return;
      const id = btn.getAttribute("data-remove");
      rows = rows.filter((r) => r.id !== id);
      save(rows);
      paint();
    });

    paint();
  }

  window.CrashoutCreatorVault = { mount };
})();
