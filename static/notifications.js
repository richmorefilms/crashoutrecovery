/**
 * Neon Notifications — creator alerts + toast + sidebar pulse
 */
(function () {
  const KEY = "crashout_notifications";
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
      localStorage.setItem(KEY, JSON.stringify(rows.slice(0, 40)));
    } catch (_) {
      /* ignore */
    }
  }

  function seedIfEmpty() {
    let rows = load();
    if (rows.length) return rows;
    rows = [
      {
        id: "n1",
        kind: "recommendations",
        title: uiLabel("recommendations", "Recommendations"),
        body: "Fresh hologram insights are ready.",
        at: Date.now(),
      },
      {
        id: "n2",
        kind: "topics",
        title: uiLabel("topic_clusters", "Topic Clusters"),
        body: "Momentum clusters shifted in your galaxy.",
        at: Date.now() - 3600000,
      },
      {
        id: "n3",
        kind: "growth",
        title: uiLabel("growth_score", "Growth Score"),
        body: "Your creator health meter updated.",
        at: Date.now() - 7200000,
      },
      {
        id: "n4",
        kind: "monetization",
        title: uiLabel("monetization_lanes", "Monetization"),
        body: "Earnings scoreboard lanes refreshed.",
        at: Date.now() - 10800000,
      },
      {
        id: "n5",
        kind: "youtube",
        title: uiLabel("youtube_tools", "YouTube Tools"),
        body: "Channel insights ready to analyze.",
        at: Date.now() - 14400000,
      },
    ];
    save(rows);
    return rows;
  }

  function push(note) {
    const rows = load();
    rows.unshift({
      id: `n_${Date.now()}`,
      kind: note.kind || "pulse",
      title: note.title || uiLabel("notifications", "Notifications"),
      body: note.body || "",
      at: Date.now(),
    });
    save(rows);
    updatePulse(true);
    return rows;
  }

  function toast(message) {
    let el = document.getElementById("neon-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "neon-toast";
      el.className = "neon-toast";
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 2600);
  }

  function updatePulse(on) {
    document.querySelectorAll(".nav-pulse").forEach((el) => {
      el.classList.toggle("nav-pulse--on", Boolean(on));
      el.hidden = !on;
    });
  }

  function renderList(root, rows) {
    if (!rows.length) {
      root.innerHTML = `<p class="creator-hub-note">${escapeHtml(uiLabel("notifications_empty", "No alerts yet."))}</p>`;
      return;
    }
    root.innerHTML = rows
      .map(
        (n) => `
      <article class="holo-card notify-card" data-kind="${escapeHtml(n.kind || "")}">
        <h3 class="neon-title">${escapeHtml(n.title || "")}</h3>
        <p class="expand-sub">${escapeHtml(n.body || "")}</p>
      </article>`
      )
      .join("");
  }

  function mount() {
    const root = document.getElementById("notifications-list-root");
    if (!root) return;
    let rows = seedIfEmpty();
    renderList(root, rows);
    updatePulse(rows.length > 0);

    document.getElementById("notifications-refresh")?.addEventListener("click", () => {
      rows = seedIfEmpty();
      renderList(root, rows);
      toast(uiLabel("notifications_refreshed", "Alerts refreshed"));
    });
    document.getElementById("notifications-clear")?.addEventListener("click", () => {
      save([]);
      rows = [];
      renderList(root, rows);
      updatePulse(false);
      toast(uiLabel("notifications_cleared", "Alerts cleared"));
    });
  }

  function initPulse() {
    const rows = load();
    updatePulse(rows.length > 0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPulse);
  } else {
    initPulse();
  }

  window.CrashoutNotifications = { mount, push, toast, seedIfEmpty };
})();
