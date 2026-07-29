/**
 * Ad inventory — GET /api/monetization/ads + POST click
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
    const params = new URLSearchParams(window.location.search);
    const q = params.get("creator_id") || params.get("id");
    if (q) return q;
    try {
      const raw = localStorage.getItem("crashout_auth_user");
      const user = raw ? JSON.parse(raw) : null;
      if (user?.id) return String(user.id);
    } catch (_) {
      /* ignore */
    }
    return "";
  }

  async function load() {
    const res = await fetch("/api/monetization/ads", { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Ads failed (${res.status})`);
    return res.json();
  }

  async function recordClick(adId, creatorId) {
    const qs = creatorId ? `?creator_id=${encodeURIComponent(creatorId)}` : "";
    const res = await fetch(`/api/monetization/ads/click/${encodeURIComponent(adId)}${qs}`, {
      method: "POST",
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `Click failed (${res.status})`);
    }
    return data;
  }

  function renderCard(ad) {
    const title = escapeHtml(ad.title || "Ad");
    const image = ad.image ? escapeHtml(ad.image) : "";
    const cta = ad.cta ? escapeHtml(ad.cta) : "#";
    const payout = ad.payout_per_click != null ? Number(ad.payout_per_click).toFixed(2) : "0.00";
    const media = image
      ? `<img class="unified-card-thumb" src="${image}" alt="" loading="lazy">`
      : `<div class="unified-card-placeholder" aria-hidden="true"></div>`;
    return `
      <article class="unified-card" data-ad-id="${escapeHtml(String(ad.id))}">
        ${media}
        <div class="unified-card-body">
          <span class="platform-badge">Ad</span>
          <h3 class="unified-card-title">${title}</h3>
          <p class="unified-card-score">$${payout} / click</p>
          <button type="button" class="feed-cta" data-ad-click="${escapeHtml(String(ad.id))}">
            Open / earn
          </button>
          ${ad.cta ? `<a class="feed-cta feed-cta--ghost" href="${cta}" target="_blank" rel="noopener">Visit</a>` : ""}
        </div>
      </article>`;
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const errEl = document.getElementById("monetization-ads-error");
    const statusEl = document.getElementById("monetization-ads-status");
    if (!root) return;
    const creatorId = resolveCreatorId();

    try {
      const data = await load();
      const items = Array.isArray(data.items) ? data.items : [];
      root.innerHTML = items.map(renderCard).join("");
      root.addEventListener("click", async (ev) => {
        const btn = ev.target.closest("[data-ad-click]");
        if (!btn) return;
        const adId = btn.getAttribute("data-ad-click");
        if (!creatorId) {
          if (statusEl) {
            statusEl.hidden = false;
            statusEl.textContent = "Sign in or open with ?id=yourUserId to earn on clicks.";
          }
          return;
        }
        try {
          const result = await recordClick(adId, creatorId);
          if (statusEl) {
            statusEl.hidden = false;
            statusEl.textContent = result.earnings_updated
              ? "Click recorded — earnings updated."
              : "Click recorded.";
          }
        } catch (err) {
          if (errEl) {
            errEl.hidden = false;
            errEl.textContent = err.message || "Click failed.";
          }
        }
      });
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load ads.";
      }
    }
  }

  window.CrashoutMonetizationAds = { mount, load, recordClick };
})();
