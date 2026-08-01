/**
 * Neon Creator Economy Engine — lanes + projections (no gambling vibes)
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function resolveCreatorId() {
    const main = document.querySelector("#economy-root");
    return (
      main?.getAttribute("data-creator-id") ||
      new URLSearchParams(window.location.search).get("id") ||
      "1"
    );
  }

  function projectRows(earningsTotal, laneCount) {
    const base = Math.max(0.5, Number(earningsTotal) || 0.8);
    return [
      {
        id: "yt",
        title: "YouTube",
        note: "Long-form + Shorts steady lane",
        value: (base * 1.4).toFixed(2),
        potential: 72,
      },
      {
        id: "shorts",
        title: "Shorts",
        note: "Clip velocity without pressure",
        value: (base * 1.1).toFixed(2),
        potential: 68,
      },
      {
        id: "tiktok",
        title: "TikTok",
        note: "Discovery lane, calm CTAs",
        value: (base * 0.95).toFixed(2),
        potential: 64,
      },
      {
        id: "ads",
        title: "Ads",
        note: "Recovery-safe placements",
        value: (base * (0.7 + laneCount * 0.05)).toFixed(2),
        potential: 58,
      },
    ];
  }

  async function mount() {
    const lanesRoot = document.getElementById("economy-lanes-root");
    const projRoot = document.getElementById("economy-projections-root");
    const meter = document.getElementById("economy-boost-meter");
    const meterVal = document.getElementById("economy-boost-value");
    const errEl = document.getElementById("economy-error");
    const creatorId = resolveCreatorId();
    try {
      const [lanesRes, earnRes] = await Promise.all([
        fetch("/api/monetization/lanes", { credentials: "same-origin" }),
        fetch(`/api/monetization/creator/${encodeURIComponent(creatorId)}/earnings`, {
          credentials: "same-origin",
        }).catch(() => null),
      ]);
      if (!lanesRes.ok) throw new Error(`Economy lanes failed (${lanesRes.status})`);
      const lanes = await lanesRes.json();
      let earningsTotal = 0;
      if (earnRes && earnRes.ok) {
        const earn = await earnRes.json();
        earningsTotal = Number(earn.items?.[0]?.total_earnings || earn.meta?.total || 0);
      }
      const items = Array.isArray(lanes.items) ? lanes.items : [];
      if (lanesRoot) {
        lanesRoot.innerHTML = items
          .map((lane, i) => {
            const score = Math.max(30, 85 - i * 12);
            return `
            <article class="holo-card economy-lane-card">
              <h3 class="neon-title">${escapeHtml(lane.title || lane.id)}</h3>
              <p class="expand-sub">${escapeHtml(lane.description || "")}</p>
              <div class="stat-meter" style="--stat:${score}"><div class="stat-meter-fill"></div></div>
              <p class="radar-strength">${score}% ${escapeHtml(uiLabel("economy_optimizer", "lane optimizer"))}</p>
            </article>`;
          })
          .join("");
      }
      const projections = projectRows(earningsTotal, items.length);
      const boost = Math.round(
        projections.reduce((s, p) => s + p.potential, 0) / Math.max(1, projections.length)
      );
      if (meter) meter.style.setProperty("--stat", String(boost));
      if (meterVal) meterVal.textContent = `${boost}%`;
      if (projRoot) {
        projRoot.innerHTML = projections
          .map(
            (p) => `
          <article class="holo-card">
            <h3 class="neon-title">${escapeHtml(p.title)}</h3>
            <p class="earn-amount">~$${escapeHtml(p.value)}</p>
            <p class="expand-sub">${escapeHtml(p.note)}</p>
            <div class="stat-meter" style="--stat:${p.potential}"><div class="stat-meter-fill"></div></div>
          </article>`
          )
          .join("");
      }
      if (errEl) errEl.hidden = true;
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Economy engine offline.";
      }
    }
  }

  window.CrashoutCreatorEconomy = { mount };
})();
