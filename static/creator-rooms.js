/**
 * Neon Creator Rooms — group spaces + upliftment chat rails
 */
(function () {
  const KEY = "crashout_creator_rooms";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const ROOMS = [
    { id: "uplift_circle", name: "Uplift Circle", momentum: 74, challenge: "Consistency week", vault: "Shared drafts" },
    { id: "launch_lab", name: "Launch Lab", momentum: 68, challenge: "Publish 3 clips", vault: "Launch folder" },
    { id: "calm_crew", name: "Calm Crew", momentum: 81, challenge: "Recovery check-ins", vault: "Reflect notes" },
  ];

  function loadChat() {
    try {
      const rows = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(rows) ? rows : [];
    } catch (_) {
      return [];
    }
  }

  function saveChat(rows) {
    try {
      localStorage.setItem(KEY, JSON.stringify(rows.slice(0, 30)));
    } catch (_) {}
  }

  function mount() {
    const grid = document.getElementById("rooms-grid-root");
    const rail = document.getElementById("room-chat-rail");
    let chat = loadChat();
    if (!chat.length) {
      chat = [
        { text: uiLabel("room_seed_1", "Welcome — upliftment only in this room."), at: Date.now() - 10000 },
        { text: uiLabel("room_seed_2", "Shared challenge board is open."), at: Date.now() - 5000 },
      ];
      saveChat(chat);
    }

    if (grid) {
      grid.innerHTML = ROOMS.map(
        (r) => `
        <article class="holo-card">
          <h3 class="neon-title">${escapeHtml(r.name)}</h3>
          <div class="v16-dial dial-core-meter" style="--score:${r.momentum}">
            <div class="v16-dial-inner dial-core">
              <span class="v16-dial-value">${r.momentum}</span>
              <span class="v16-dial-label">${escapeHtml(uiLabel("room_momentum", "Momentum"))}</span>
            </div>
          </div>
          <p class="expand-sub">${escapeHtml(r.challenge)}</p>
          <p class="expand-sub">${escapeHtml(r.vault)}</p>
          <a class="launch-btn launch-btn--ready" href="/challenges">${escapeHtml(uiLabel("creator_challenges", "Challenges"))}</a>
        </article>`
      ).join("");
    }

    function paintChat() {
      if (!rail) return;
      rail.innerHTML = chat
        .map(
          (c) => `
        <article class="holo-card notify-card">
          <p class="expand-sub">${escapeHtml(c.text)}</p>
        </article>`
        )
        .join("");
    }

    document.querySelectorAll("[data-chat]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const kind = btn.getAttribute("data-chat");
        const text =
          kind === "support"
            ? uiLabel("room_chat_support_msg", "Sending quiet support — you got this.")
            : uiLabel("room_chat_uplift_msg", "Uplift pulse shared with the room.");
        chat.unshift({ text, at: Date.now() });
        saveChat(chat);
        paintChat();
        window.CrashoutCreatorBadges?.earn?.("community");
      });
    });

    paintChat();
  }

  window.CrashoutCreatorRooms = { mount };
})();
