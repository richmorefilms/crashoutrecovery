/**
 * Creator hub — channels, analytics, growth dial, opportunities.
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function resolveCreatorId() {
    const main = document.querySelector(".creator-hub-page");
    const fromData = main?.getAttribute("data-creator-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get("id") || params.get("creator_id") || "";
    if (fromQuery) return fromQuery;
    try {
      const raw = localStorage.getItem("crashout_auth_user");
      const user = raw ? JSON.parse(raw) : null;
      if (user?.id) return String(user.id);
    } catch (_) {
      /* ignore */
    }
    return "";
  }

  function showConnect(show) {
    const el = document.getElementById("creator-hub-connect");
    if (el) el.hidden = !show;
  }

  function renderChannels(data) {
    const root = document.getElementById("creator-channels-root");
    if (!root) return;
    if (!data.ok || data.reason === "not_linked") {
      root.innerHTML = `<p class="creator-hub-note">No linked channels yet.</p>`;
      showConnect(true);
      return;
    }
    showConnect(false);
    const items = Array.isArray(data.items) ? data.items : [];
    if (!items.length) {
      root.innerHTML = `<p class="creator-hub-note">No channels returned.</p>`;
      return;
    }
    root.innerHTML = items
      .map((ch) => {
        const title = escapeHtml(ch.title || "Channel");
        const id = escapeHtml(ch.id || "");
        const href = ch.id ? `/youtube/channel/${encodeURIComponent(ch.id)}` : "#";
        return `<article class="creator-hub-card unified-card neon-card">
          <div class="unified-card-body">
            <span class="platform-badge platform-badge--youtube">YouTube</span>
            <h3 class="unified-card-title title neon-title"><a href="${href}">${title}</a></h3>
            <p class="creator-hub-meta">${id}</p>
          </div>
        </article>`;
      })
      .join("");
  }

  function renderAnalytics(data) {
    const root = document.getElementById("creator-analytics-root");
    if (!root) return;
    if (!data.ok || data.reason === "not_linked") {
      root.innerHTML = `<p class="creator-hub-note">Analytics unlock after Connect YouTube.</p>`;
      return;
    }
    const item = (data.items && data.items[0]) || {};
    root.innerHTML = `
      <article class="creator-hub-card unified-card neon-card">
        <ul class="youtube-detail-stats">
          <li>Views: ${escapeHtml(String(item.views ?? 0))}</li>
          <li>Watch time (min): ${escapeHtml(String(item.watch_time_minutes ?? 0))}</li>
          <li>Subscribers gained: ${escapeHtml(String(item.subscribers_gained ?? 0))}</li>
          <li>Mode: ${escapeHtml(String(item.mode || data.meta?.mode || "placeholder"))}</li>
        </ul>
      </article>`;
  }

  function renderGrowth(data) {
    const dial = document.getElementById("creator-growth-dial");
    const value = document.getElementById("creator-growth-value");
    const score = Number(data?.meta?.growth_score ?? data?.items?.[0]?.growth_score ?? 0);
    if (dial) dial.style.setProperty("--score", String(Math.max(0, Math.min(100, score))));
    if (value) value.textContent = Number.isFinite(score) ? String(score) : "—";
  }

  function renderOpportunities(data) {
    const root = document.getElementById("creator-opportunities-root");
    if (!root) return;
    const items = Array.isArray(data.items) ? data.items.slice(0, 3) : [];
    if (!items.length) {
      root.innerHTML = `<p class="creator-hub-note">No opportunities yet.</p>`;
      return;
    }
    root.innerHTML = items
      .map((item) => {
        const values = Array.isArray(item.values)
          ? item.values
              .map((v) => (typeof v === "string" ? v : v.topic || v.platform || ""))
              .filter(Boolean)
              .slice(0, 3)
              .join(", ")
          : "";
        return `<article class="creator-hub-card unified-card neon-card">
          <h3 class="title neon-title">${escapeHtml(item.title || item.kind || "Opportunity")}</h3>
          <p class="creator-hub-meta">${escapeHtml(values)}</p>
        </article>`;
      })
      .join("");
  }

  function bindQuickActions() {
    document.querySelectorAll(".qa-btn").forEach((btn) => {
      btn.addEventListener("mouseenter", () => {
        btn.style.boxShadow = "0 0 20px #ff00ff, 0 0 40px #ff00ff";
      });
      btn.addEventListener("mouseleave", () => {
        btn.style.boxShadow = "";
      });
    });
  }

  async function mount() {
    bindQuickActions();
    const errEl = document.getElementById("creator-hub-error");
    const creatorId = resolveCreatorId();
    if (!creatorId) {
      showConnect(true);
      const ch = document.getElementById("creator-channels-root");
      const an = document.getElementById("creator-analytics-root");
      if (ch) {
        ch.innerHTML = `<p class="creator-hub-note">Sign in or open with ?id=yourUserId</p>`;
      }
      if (an) an.innerHTML = "";
      return;
    }

    try {
      const [chRes, anRes, gRes, oRes] = await Promise.all([
        fetch(`/api/creator/${encodeURIComponent(creatorId)}/channels`, {
          credentials: "same-origin",
        }),
        fetch(`/api/creator/${encodeURIComponent(creatorId)}/analytics`, {
          credentials: "same-origin",
        }),
        fetch(`/api/growth/${encodeURIComponent(creatorId)}/score`, {
          credentials: "same-origin",
        }),
        fetch(`/api/growth/${encodeURIComponent(creatorId)}/opportunities`, {
          credentials: "same-origin",
        }),
      ]);
      renderChannels(await chRes.json());
      renderAnalytics(await anRes.json());
      if (gRes.ok) renderGrowth(await gRes.json());
      if (oRes.ok) renderOpportunities(await oRes.json());
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Dashboard failed to load.";
      }
    }
  }

  window.CrashoutCreatorHub = { mount, resolveCreatorId };
})();
