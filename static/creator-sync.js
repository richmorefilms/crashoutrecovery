/**
 * Neon Creator Sync — cross-device local state export/import/merge
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  const KEYS = [
    "crashout_creator_identity",
    "crashout_creator_vault",
    "crashout_creator_challenges",
    "crashout_social_follows",
    "crashout_creator_badges",
    "crashout_notifications",
    "crashout_recovery_mode",
    "crashout_recovery_journal",
    "crashout_creator_rooms",
  ];

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function snapshot() {
    const data = { version: 1, exported_at: new Date().toISOString(), keys: {} };
    KEYS.forEach((k) => {
      try {
        const raw = localStorage.getItem(k);
        if (raw != null) data.keys[k] = JSON.parse(raw);
      } catch (_) {
        data.keys[k] = null;
      }
    });
    return data;
  }

  function setStatus(text, ok) {
    const chip = document.getElementById("sync-status-chip");
    if (!chip) return;
    chip.textContent = text;
    chip.classList.toggle("timeline-chip--peak", Boolean(ok));
    chip.classList.toggle("timeline-chip--streak", !ok);
  }

  function mergePayload(incoming) {
    const keys = incoming?.keys || {};
    Object.keys(keys).forEach((k) => {
      if (!KEYS.includes(k)) return;
      try {
        const existingRaw = localStorage.getItem(k);
        const incomingVal = keys[k];
        if (incomingVal == null) return;
        if (!existingRaw) {
          localStorage.setItem(k, JSON.stringify(incomingVal));
          return;
        }
        const existing = JSON.parse(existingRaw);
        if (Array.isArray(existing) && Array.isArray(incomingVal)) {
          const merged = [...incomingVal, ...existing];
          const seen = new Set();
          const out = [];
          merged.forEach((row) => {
            const id = row && row.id != null ? String(row.id) : JSON.stringify(row);
            if (seen.has(id)) return;
            seen.add(id);
            out.push(row);
          });
          localStorage.setItem(k, JSON.stringify(out.slice(0, 80)));
        } else if (existing && typeof existing === "object" && !Array.isArray(existing)) {
          localStorage.setItem(k, JSON.stringify({ ...existing, ...incomingVal }));
        } else {
          localStorage.setItem(k, JSON.stringify(incomingVal));
        }
      } catch (_) {}
    });
  }

  function mount() {
    const payload = document.getElementById("sync-payload");
    const keysRoot = document.getElementById("sync-keys-root");
    const snap = snapshot();
    if (payload) payload.value = JSON.stringify(snap, null, 2);
    if (keysRoot) {
      keysRoot.innerHTML = KEYS.map((k) => {
        let present = false;
        try {
          present = localStorage.getItem(k) != null;
        } catch (_) {}
        return `<article class="holo-card"><h3 class="neon-title">${escapeHtml(k.replace("crashout_", ""))}</h3><p class="expand-sub">${present ? uiLabel("sync_ready", "ready") : uiLabel("sync_empty", "empty")}</p></article>`;
      }).join("");
    }
    setStatus(uiLabel("sync_idle", "Sync idle"), true);

    document.getElementById("sync-export")?.addEventListener("click", () => {
      const next = snapshot();
      if (payload) payload.value = JSON.stringify(next, null, 2);
      setStatus(uiLabel("sync_exported", "Exported"), true);
      window.CrashoutNotifications?.toast?.(uiLabel("sync_exported", "Exported"));
    });

    document.getElementById("sync-import")?.addEventListener("click", () => {
      try {
        const parsed = JSON.parse(payload?.value || "{}");
        Object.keys(parsed.keys || {}).forEach((k) => {
          if (!KEYS.includes(k)) return;
          localStorage.setItem(k, JSON.stringify(parsed.keys[k]));
        });
        setStatus(uiLabel("sync_imported", "Imported"), true);
        window.CrashoutNotifications?.toast?.(uiLabel("sync_imported", "Imported"));
      } catch (_) {
        setStatus(uiLabel("sync_error", "Invalid sync payload"), false);
      }
    });

    document.getElementById("sync-merge")?.addEventListener("click", () => {
      try {
        const parsed = JSON.parse(payload?.value || "{}");
        mergePayload(parsed);
        setStatus(uiLabel("sync_merged", "Merged offline changes"), true);
        window.CrashoutNotifications?.toast?.(uiLabel("sync_merged", "Merged offline changes"));
      } catch (_) {
        setStatus(uiLabel("sync_error", "Invalid sync payload"), false);
      }
    });
  }

  window.CrashoutCreatorSync = { mount, snapshot, mergePayload };
})();
