/**
 * Growth score dial — GET /api/growth/{creator_id}/score
 * Neon Hologram Stat Console
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

  async function load(creatorId) {
    const res = await fetch(`/api/growth/${encodeURIComponent(creatorId)}/score`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Growth score failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("growth-score-empty");
    const errEl = document.getElementById("growth-score-error");
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
      const data = await load(creatorId);
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
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load growth score.";
      }
    }
  }

  window.CrashoutGrowthScore = { mount, load, resolveCreatorId };
})();
