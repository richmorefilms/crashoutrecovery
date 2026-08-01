/**
 * Growth score dial — GET /api/growth/{creator_id}/score
 * Neon Hologram Stat Console + Momentum Timeline
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiTip = (key, fallback) => window.CrashoutUICopy?.tooltip?.(key) || fallback;

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function resolveCreatorId() {
    const main = document.querySelector(".feed-page--growth-score");
    const fromData = main?.getAttribute("data-creator-id") || "";
    if (fromData) return fromData;
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("creator_id") || "";
  }

  function clampPct(value, max) {
    const n = Number(value);
    if (!Number.isFinite(n) || max <= 0) return 0;
    return Math.max(0, Math.min(100, Math.round((n / max) * 100)));
  }

  function statPanel(opts) {
    const pct = clampPct(opts.value, opts.max);
    return `
      <article class="stat-panel holo-card neon-card unified-card" data-stat="${escapeHtml(opts.key)}">
        <div class="stat-ring" aria-hidden="true"></div>
        <h3 class="stat-title">${escapeHtml(opts.label)}</h3>
        <div class="stat-meter" style="--stat:${pct}">
          <div class="stat-meter-fill"></div>
        </div>
        <p class="stat-value">${escapeHtml(String(opts.value ?? "—"))}<span class="stat-max"> / ${escapeHtml(String(opts.max))}</span></p>
        <p class="stat-desc">${escapeHtml(opts.desc)}</p>
      </article>`;
  }

  function momentumSeries(days) {
    return (days || []).map((d) => {
      const views = Number(d.views) || 0;
      const likes = Number(d.likes) || 0;
      const comments = Number(d.comments) || 0;
      const earnings = Number(d.earnings) || 0;
      const recs = Number(d.recommendations_served) || 0;
      const score = views * 0.4 + likes * 1.2 + comments * 2.5 + earnings * 40 + recs * 3;
      return { date: d.date, score };
    });
  }

  function renderTimelineChart(series) {
    if (!series.length) {
      return `<p class="creator-hub-note">${escapeHtml(uiTip("growth_timeline_empty", "No momentum history yet."))}</p>`;
    }
    const w = 640;
    const h = 180;
    const pad = 16;
    const max = Math.max(...series.map((s) => s.score), 1);
    const pts = series.map((s, i) => {
      const x = pad + (i / Math.max(1, series.length - 1)) * (w - pad * 2);
      const y = h - pad - (s.score / max) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const polyline = pts.join(" ");
    const area = `${pad},${h - pad} ${polyline} ${w - pad},${h - pad}`;
    return `
      <svg class="timeline-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${escapeHtml(uiLabel("growth_timeline", "Momentum timeline"))}">
        <defs>
          <linearGradient id="momentumStroke" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#00eaff"/>
            <stop offset="100%" stop-color="#ff00ff"/>
          </linearGradient>
          <linearGradient id="momentumFill" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="rgba(0,234,255,0.35)"/>
            <stop offset="100%" stop-color="rgba(255,0,255,0.05)"/>
          </linearGradient>
        </defs>
        <polygon points="${area}" fill="url(#momentumFill)"></polygon>
        <polyline points="${polyline}" fill="none" stroke="url(#momentumStroke)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
      </svg>
      <div class="timeline-summary">
        <span>${escapeHtml(uiLabel("growth_timeline_daily", "Daily momentum"))}</span>
        <span>${escapeHtml(uiLabel("growth_timeline_weekly", "Weekly consistency"))}</span>
        <span>${escapeHtml(uiLabel("growth_timeline_monthly", "Monthly growth arcs"))}</span>
      </div>`;
  }

  function renderChips(series) {
    if (!series.length) return "";
    const sorted = [...series].sort((a, b) => b.score - a.score);
    const peaks = sorted.slice(0, 3);
    let streak = 0;
    let best = 0;
    const avg = series.reduce((s, x) => s + x.score, 0) / series.length;
    series.forEach((s) => {
      if (s.score >= avg * 0.85) {
        streak += 1;
        best = Math.max(best, streak);
      } else streak = 0;
    });
    const peakChips = peaks
      .map(
        (p) =>
          `<span class="timeline-chip timeline-chip--peak">${escapeHtml(uiLabel("growth_peak", "Momentum Peak"))} · ${escapeHtml((p.date || "").slice(5))}</span>`
      )
      .join("");
    return `
      ${peakChips}
      <span class="timeline-chip timeline-chip--streak">${escapeHtml(uiLabel("growth_streak", "Consistency Streak"))} · ${best}d</span>`;
  }

  async function load(creatorId) {
    const res = await fetch(`/api/growth/${encodeURIComponent(creatorId)}/score`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Growth score failed (${res.status})`);
    return res.json();
  }

  async function loadTrends(creatorId) {
    const res = await fetch(`/api/growth/${encodeURIComponent(creatorId)}/trends`, {
      credentials: "same-origin",
    });
    if (!res.ok) return null;
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("growth-score-empty");
    const errEl = document.getElementById("growth-score-error");
    const timelineRoot = document.getElementById("growth-timeline-root");
    const chipsRoot = document.getElementById("growth-timeline-chips");
    if (!root) return;
    const creatorId = resolveCreatorId();
    if (!creatorId) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Open with ?id=creatorId for growth score.";
      }
      return;
    }
    try {
      const [data, trends] = await Promise.all([load(creatorId), loadTrends(creatorId)]);
      const item = (data.items || [])[0];
      if (!item) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;

      const score = Number(item.growth_score ?? data.meta?.growth_score ?? 0);
      const comps = item.components || {};
      const scoreClamped = Math.max(0, Math.min(100, score));

      root.innerHTML = `
        <section class="score-hero console-panel unified-card neon-card holo-card">
          <div class="score-dial-ring" aria-hidden="true"></div>
          <div class="v16-dial score-dial" style="--score:${scoreClamped}">
            <div class="v16-dial-inner">
              <span class="v16-dial-value">${escapeHtml(String(score))}</span>
              <span class="v16-dial-label">${escapeHtml(uiLabel("growth_score", "Score"))}</span>
            </div>
          </div>
          <p class="score-hero-meta">Creator ${escapeHtml(String(item.creator_id || creatorId))}</p>
        </section>

        <section class="stat-grid" aria-label="Growth components">
          ${statPanel({
            key: "engagement",
            label: uiLabel("growth_stat_engagement", "Engagement"),
            value: comps.engagement,
            max: 30,
            desc: uiTip("growth_stat_engagement", "Views, likes, comments, and ad signals."),
          })}
          ${statPanel({
            key: "consistency",
            label: uiLabel("growth_stat_consistency", "Consistency"),
            value: comps.history,
            max: 30,
            desc: uiTip("growth_stat_consistency", "History and publishing rhythm."),
          })}
          ${statPanel({
            key: "topic_strength",
            label: uiLabel("growth_stat_topic_strength", "Topic Strength"),
            value: comps.recommendations,
            max: 15,
            desc: uiTip("growth_stat_topic_strength", "Recommendation coverage across topics."),
          })}
          ${statPanel({
            key: "audience_growth",
            label: uiLabel("growth_stat_audience", "Audience Growth"),
            value: comps.earnings,
            max: 25,
            desc: uiTip("growth_stat_audience", "Earnings proxy for audience value."),
          })}
          ${statPanel({
            key: "momentum",
            label: uiLabel("growth_stat_momentum", "Momentum"),
            value: score,
            max: 100,
            desc: uiTip("growth_stat_momentum", "Overall creator health meter."),
          })}
        </section>`;

      const series = momentumSeries(trends?.items || []);
      if (timelineRoot) timelineRoot.innerHTML = renderTimelineChart(series);
      if (chipsRoot) chipsRoot.innerHTML = renderChips(series);
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load growth score.";
      }
    }
  }

  window.CrashoutGrowthScore = { mount, load, resolveCreatorId };
})();
