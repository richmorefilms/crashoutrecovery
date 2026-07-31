/**
 * Monetization foundation — lane-native placements, premium gates, sponsored cards.
 * UI scaffolding only; no payment processing. Wire to IAP/subscriptions later.
 */
(function () {
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiLower = (key, fallback) => window.CrashoutUICopy?.labelLower?.(key) || fallback;

  const TIERS = {
    basic: { id: "basic", label: "Basic", price: "Free" },
    plus: { id: "plus", label: "Plus", price: "$4.99/mo" },
    creator: { id: "creator", label: "Creator Mode", price: "$9.99/mo" },
    pro: { id: "pro", label: "Recovery Pro", price: "$14.99/mo" },
  };

  /** Simulated tier — replace with server / store receipt check */
  let activeTier = "basic";

  function premiumFeatures() {
    return [
      { id: "tone_deep", label: "Deeper tone analysis", tier: "plus" },
      { id: "cta_coach", label: "Advanced action coaching", tier: "plus" },
      { id: "predictor", label: uiLabel("bad_decision_predictor", "Risk check"), tier: "creator" },
      { id: "algo_plan", label: "Algorithm dip recovery plan", tier: "creator" },
      {
        id: "seed_optimizer",
        label: `${uiLabel("seed", "Draft idea")} optimizer`,
        tier: "creator",
      },
      { id: "creator_dashboard", label: "Creator Mode dashboard", tier: "creator" },
      { id: "signals_dashboard", label: uiLabel("signals_pro", "World trends"), tier: "pro" },
      { id: "spike_history", label: "Your spike history", tier: "pro" },
      { id: "recovery_streaks", label: `${uiLabel("recovery_streak", "Win streak")}s`, tier: "pro" },
    ];
  }

  const LANE_SPONSORED = {
    drama: {
      type: "breakdown",
      sponsor: "Clarity Journal",
      label: "Sponsored breakdown",
      headline: "How one creator avoided a public meltdown",
      summary: "Burnout recovery + journaling routine — draft first, post second.",
      cta: "Learn the turnaround",
      ctaKey: "draft_dont_delete",
      tone: "calm",
    },
    moments: {
      type: "micro_ad",
      sponsor: "Turnaround Shorts",
      label: "Sponsored moment",
      title: "5s: breathe before you post",
      description: "Micro-ad — pause spike, save the draft idea.",
      duration: "0:05",
      creator: "Sponsored",
      cta: "Watch & draft",
      ctaKey: "seed_post",
      tone: "calm",
    },
    headlines: {
      type: "insight",
      sponsor: "Creator Wire",
      label: "Sponsored insight",
      headline: "Trend: draft-folder saves beat live meltdowns this week",
      summary: "Sponsored trend breakdown for creators riding algo dips.",
      source: "Sponsored · Creator Wire",
      ctaKey: "test_variable",
      tone: "strategic",
    },
    signals: {
      type: "premium_signal",
      sponsor: "Recovery Pro",
      label: "Premium signal",
      chip: "Burnout alert 🔒",
      headline: "Creator burnout cluster — 72h forecast",
      summary: `${uiLabel("signals_pro", "World trends")} preview: predictive spike map for your niche.`,
      region: "Pro dashboard",
      ctaKey: "seed_post",
      tone: "calm",
      premium: true,
    },
    posts: {
      type: "minimal",
      sponsor: "Recovery Desk",
      label: "Sponsored",
      author: "@drafttools",
      meta: "Sponsored · recovery",
      text: "A small pause can turn a spike into a safer draft.",
      ctaKey: "micro_thread",
      tone: "universal",
      deep: true,
    },
  };

  const COMPOSER_UPSELLS = [
    { id: "tone_coach", label: "Deeper rewrite guidance", tier: "plus" },
    { id: "cta_coach", label: "Contextual recovery actions", tier: "plus" },
    { id: "seed_optimizer", label: "Draft idea optimizer", tier: "creator" },
    { id: "momentum_boost", label: "Progress boosters", tier: "pro" },
  ];

  const SPONSORED_CTA = {
    label: "Sponsored micro-action",
    text: "Draft, don't delete — sponsored recovery tip from Clarity Journal.",
    sponsor: "Clarity Journal",
    ctaKey: "draft_dont_delete",
  };

  function isPremium(tierRequired) {
    const order = ["basic", "plus", "creator", "pro"];
    return order.indexOf(activeTier) >= order.indexOf(tierRequired);
  }

  function isFeatureUnlocked(featureId) {
    const feat = premiumFeatures().find((f) => f.id === featureId);
    return feat ? isPremium(feat.tier) : false;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function sponsoredBadge(label) {
    return `<span class="monetization-badge monetization-badge--sponsored">${escapeHtml(label)}</span>`;
  }

  function premiumBadge() {
    return `<span class="monetization-badge monetization-badge--premium">Premium</span>`;
  }

  function renderSponsoredDrama(item, rank) {
    return `
      <article class="feed-item feed-item--sponsored feed-item--headline unified-card neon-card" data-sponsored="true" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          ${sponsoredBadge(item.label)}
          <p class="sponsored-by">by ${escapeHtml(item.sponsor)}</p>
          <h4 class="feed-item-headline">${escapeHtml(item.headline)}</h4>
          <p class="feed-item-summary">${escapeHtml(item.summary)}</p>
          <footer class="feed-item-cta-footer">
            <p class="feed-item-cta-text">${escapeHtml(item.cta)}</p>
            <button type="button" class="feed-action feed-action--sponsored" data-monetization-action="sponsored-cta" data-cta-key="${item.ctaKey}">Learn more</button>
            <button type="button" class="feed-action feed-action--upgrade" data-monetization-action="upgrade" data-tier="creator">Unlock Creator Mode</button>
          </footer>
        </div>
      </article>`;
  }

  function renderSponsoredMoment(item, rank) {
    return `
      <article class="feed-item feed-item--sponsored feed-item--video unified-card neon-card" data-sponsored="true" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-media" data-tone="${item.tone}">
          <span class="feed-item-duration">${escapeHtml(item.duration)}</span>
          <span class="feed-item-play" aria-hidden="true">▶</span>
          <span class="feed-item-category">${escapeHtml(item.label)}</span>
        </div>
        <div class="feed-item-content">
          <div class="feed-item-body">
            ${sponsoredBadge("Micro-ad")}
            <h4 class="feed-item-title">${escapeHtml(item.title)}</h4>
            <p class="feed-item-desc">${escapeHtml(item.description)}</p>
            <p class="feed-item-meta">${escapeHtml(item.sponsor)}</p>
          </div>
          <footer class="feed-item-cta-footer">
            <button type="button" class="feed-action feed-action--sponsored" data-monetization-action="sponsored-cta" data-cta-key="${item.ctaKey}">${escapeHtml(item.cta)}</button>
            <button type="button" class="feed-action feed-action--upgrade" data-monetization-action="upgrade" data-tier="plus">Unlock Advanced actions</button>
          </footer>
        </div>
      </article>`;
  }

  function renderSponsoredHeadline(item, rank) {
    return `
      <article class="feed-item feed-item--sponsored feed-item--headline unified-card neon-card" data-sponsored="true" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          ${sponsoredBadge(item.label)}
          <h4 class="feed-item-headline">${escapeHtml(item.headline)}</h4>
          <p class="feed-item-summary">${escapeHtml(item.summary)}</p>
          <p class="feed-item-source">${escapeHtml(item.source)}</p>
          <footer class="feed-item-cta-footer">
            <button type="button" class="feed-action feed-action--sponsored" data-monetization-action="sponsored-cta" data-cta-key="${item.ctaKey}">Read insight</button>
            <button type="button" class="feed-action feed-action--upgrade" data-monetization-action="upgrade" data-tier="pro">Unlock ${escapeHtml(uiLower("signals_pro", "world trends"))}</button>
          </footer>
        </div>
      </article>`;
  }

  function renderSponsoredPost(item, rank) {
    return `
      <article class="feed-item feed-item--sponsored feed-item--post feed-item--sponsored-deep unified-card neon-card" data-sponsored="true" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          ${sponsoredBadge(item.label)}
          <p class="feed-community-author">${escapeHtml(item.author)}</p>
          <p class="feed-community-meta">${escapeHtml(item.meta)}</p>
          <p class="feed-item-post-text">${escapeHtml(item.text)}</p>
          <footer class="feed-item-cta-footer">
            <button type="button" class="feed-action feed-action--sponsored" data-monetization-action="sponsored-cta" data-cta-key="${item.ctaKey}">Get templates</button>
            <button type="button" class="feed-action feed-action--upgrade" data-monetization-action="upgrade" data-tier="creator">Unlock Creator Mode</button>
          </footer>
        </div>
      </article>`;
  }

  function renderSponsoredSignal(item, rank) {
    return `
      <article class="feed-item feed-item--sponsored feed-item--headline unified-card neon-card" data-sponsored="true" data-tone="${item.tone}" style="animation-delay:${rank * 50}ms">
        <div class="feed-item-content">
          ${sponsoredBadge(item.label)}
          ${item.premium ? premiumBadge() : ""}
          <h4 class="feed-item-headline">${escapeHtml(item.headline)}</h4>
          <p class="feed-item-summary">${escapeHtml(item.summary)}</p>
          <p class="feed-item-source">${escapeHtml(item.region)} · ${escapeHtml(item.sponsor)}</p>
          <footer class="feed-item-cta-footer">
            <button type="button" class="feed-action feed-action--sponsored" data-monetization-action="sponsored-cta" data-cta-key="${item.ctaKey}">View signal</button>
            <button type="button" class="feed-action feed-action--upgrade" data-monetization-action="upgrade" data-tier="pro">Unlock ${escapeHtml(uiLower("signals_pro", "world trends"))}</button>
          </footer>
        </div>
      </article>`;
  }

  function renderSponsoredForLane(lane, rank) {
    const item = LANE_SPONSORED[lane];
    if (!item) return "";
    if (lane === "posts" && !item.deep) return "";

    switch (lane) {
      case "drama":
        return renderSponsoredDrama(item, rank);
      case "moments":
        return renderSponsoredMoment(item, rank);
      case "headlines":
        return renderSponsoredHeadline(item, rank);
      case "posts":
        return renderSponsoredPost(item, rank);
      case "signals":
        return renderSponsoredSignal(item, rank);
      default:
        return "";
    }
  }

  function injectSponsoredHtml(lane, organicHtml) {
    const sponsored = renderSponsoredForLane(lane, 1);
    if (!sponsored) return organicHtml;

    const parts = organicHtml.split("</article>");
    if (parts.length < 2) return organicHtml + sponsored;

    if (lane === "posts") {
      return parts.join("</article>") + sponsored;
    }

    return parts[0] + "</article>" + sponsored + parts.slice(1).join("</article>");
  }

  function renderPremiumSignalChip() {
    if (isPremium("pro")) return "";
    const item = LANE_SPONSORED.signals;
    return `
      <button type="button" class="world-signal-chip world-signal-chip--premium" data-monetization-action="upgrade" data-tier="pro" data-tone="calm">
        <span class="world-signal-chip-dot" aria-hidden="true"></span>
        <span class="world-signal-chip-text">${escapeHtml(item.chip)}</span>
      </button>`;
  }

  function renderComposerUpsell() {
    const el = document.getElementById("composer-premium-strip");
    if (!el) return;

    if (activeTier !== "basic") {
      el.hidden = true;
      return;
    }

    el.hidden = false;
    el.innerHTML = `
      <div class="premium-strip-inner">
        <p class="premium-strip-title">Unlock more from your spike</p>
        <div class="premium-strip-chips">
          ${COMPOSER_UPSELLS.map(
            (u) => `
            <button type="button" class="premium-chip" data-monetization-action="upgrade" data-tier="${u.tier}">
              ${escapeHtml(u.label)}
            </button>`
          ).join("")}
        </div>
        <button type="button" class="premium-strip-cta" data-monetization-action="upgrade" data-tier="plus">
          Try unlock levels
        </button>
      </div>`;
  }

  function renderPredictorTeaser() {
    const el = document.getElementById("premium-predictor-teaser");
    const panel = document.getElementById("bad-decision-predictor");
    if (!el) return;

    if (isFeatureUnlocked("predictor") || (panel && !panel.hidden)) {
      el.hidden = true;
      return;
    }

    el.hidden = false;
    el.innerHTML = `
      <div class="premium-teaser premium-teaser--predictor">
        ${premiumBadge()}
        <p class="premium-teaser-title">${escapeHtml(uiLabel("bad_decision_predictor", "Risk check"))}</p>
        <p class="premium-teaser-copy">Your spike is rising — unlock the safer move before you post.</p>
        <button type="button" class="premium-teaser-btn" data-monetization-action="upgrade" data-tier="creator">Unlock Creator Mode</button>
      </div>`;
  }

  function tierPreviewFeatures() {
    return {
      basic: [
        `Core feed + ${uiLower("composer", "draft box")}`,
        `Tone read + ${uiLower("momentum_cta", "suggested next step")}`,
        `${uiLabel("signals_pro", "World trends")} ${uiLower("pulse_strip", "signal bar")}`,
      ],
      plus: ["Deeper tone analysis", "Advanced action coaching", "More rewrite guidance"],
      creator: [
        uiLabel("bad_decision_predictor", "Risk check"),
        `${uiLabel("seed", "Draft idea")} optimizer`,
        "Database-guided rewrites",
        "Creator Mode dashboard",
      ],
      pro: [
        `${uiLabel("signals_pro", "World trends")} panel`,
        `${uiLabel("recovery_streak", "Win streak")} tracker`,
        "Spike history",
        "Algorithm dip recovery plan",
      ],
    };
  }

  let upgradeModalEl = null;
  let previewTier = null;

  function updateUpgradeModalUi(highlightTier) {
    const tiersRoot = document.getElementById("upgrade-tiers");
    const previewList = document.getElementById("upgrade-preview-list");
    if (!tiersRoot) return;

    tiersRoot.querySelectorAll(".tier-card").forEach((card) => {
      const tier = card.dataset.tier;
      card.classList.toggle("tier-card--highlight", tier === highlightTier);
      card.classList.toggle("tier-card--active", tier === activeTier);
    });

    tiersRoot.querySelectorAll(".upgrade-select").forEach((btn) => {
      const tier = btn.dataset.tier;
      const isCurrent = tier === activeTier;
      btn.disabled = isCurrent;
      if (tier === "basic") {
        btn.textContent = isCurrent ? "Current plan" : "Switch to Basic";
      } else if (tier === "pro") {
        btn.textContent = isCurrent ? "Current plan" : "Try Pro";
      } else {
        btn.textContent = isCurrent ? "Current plan" : `Preview ${TIERS[tier]?.label || tier}`;
      }
    });

    if (previewList) {
      const catalog = tierPreviewFeatures();
      const features = catalog[highlightTier || activeTier] || catalog.basic;
      previewList.innerHTML = features.map((f) => `<li>${escapeHtml(f)}</li>`).join("");
    }
  }

  function openUpgradeModal(tier) {
    upgradeModalEl = upgradeModalEl || document.getElementById("upgrade-modal");
    if (!upgradeModalEl) return;

    previewTier = tier || previewTier || "plus";
    upgradeModalEl.hidden = false;
    upgradeModalEl.setAttribute("aria-hidden", "false");
    document.body.classList.add("upgrade-modal-open");
    updateUpgradeModalUi(previewTier);

    const focusTarget = upgradeModalEl.querySelector(`[data-tier="${previewTier}"] .upgrade-select`);
    focusTarget?.focus();
  }

  function closeUpgradeModal() {
    upgradeModalEl = upgradeModalEl || document.getElementById("upgrade-modal");
    if (!upgradeModalEl) return;

    upgradeModalEl.hidden = true;
    upgradeModalEl.setAttribute("aria-hidden", "true");
    document.body.classList.remove("upgrade-modal-open");
  }

  function previewTierSelection(tier) {
    if (!TIERS[tier]) return;
    previewTier = tier;
    updateUpgradeModalUi(tier);
  }

  function applyTierPreview(tier) {
    if (!TIERS[tier] || tier === activeTier) return;

    activeTier = tier;
    renderComposerUpsell();
    renderComposerUpsellBar();
    renderPredictorTeaser();
    window.CrashoutPredictor?.refresh?.();
    window.CrashoutRecoveryStreak?.refresh?.();
    window.CrashoutCreatorDashboard?.render?.();
    updateUpgradeModalUi(tier);
    window.CrashoutWorldSignals?.renderStrip?.(null);
    window.CrashoutWorldSignals?.renderProPanel?.();
    window.CrashoutTabbedFeed?.render?.(null);

    const t = TIERS[tier];
    const status = document.getElementById("upgrade-toast");
    if (status) {
      status.hidden = false;
      status.textContent = `Previewing ${t.label} — connect App Store / Play Billing to keep.`;
      window.setTimeout(() => {
        status.hidden = true;
      }, 3500);
    }

    window.dispatchEvent(
      new CustomEvent("crashout:upgrade-preview", {
        detail: { tier: t.id, label: t.label, price: t.price },
      })
    );

    if (tier !== "basic") {
      closeUpgradeModal();
    }
  }

  function showUpgradeModal(tier) {
    openUpgradeModal(tier || "plus");
  }

  function renderComposerUpsellBar() {
    const el = document.getElementById("composer-upsell");
    if (!el) return;

    if (isFeatureUnlocked("predictor")) {
      el.hidden = true;
      return;
    }

    el.hidden = false;
    el.innerHTML = `
      <p class="composer-upsell-copy">${escapeHtml(uiLabel("bad_decision_predictor", "Risk check"))} unlocks in Creator Mode.</p>
      <button type="button" class="composer-upsell-btn" data-monetization-action="upgrade" data-tier="creator">Try Creator Mode</button>`;
  }

  function handleClick(e) {
    const upgradeSelect = e.target.closest(".upgrade-select");
    if (upgradeSelect && upgradeModalEl && !upgradeModalEl.hidden) {
      e.preventDefault();
      applyTierPreview(upgradeSelect.dataset.tier);
      return;
    }

    const closeUpgrade = e.target.closest("[data-close-upgrade]");
    if (closeUpgrade) {
      e.preventDefault();
      closeUpgradeModal();
      return;
    }

    const tierCard = e.target.closest(".tier-card");
    if (tierCard && upgradeModalEl && !upgradeModalEl.hidden) {
      previewTierSelection(tierCard.dataset.tier);
      return;
    }

    const btn = e.target.closest("[data-monetization-action]");
    if (!btn) return;

    const action = btn.dataset.monetizationAction;
    if (action === "upgrade") {
      e.preventDefault();
      e.stopPropagation();
      showUpgradeModal(btn.dataset.tier || "plus");
      return;
    }
    if (action === "sponsored-cta") {
      e.stopPropagation();
      const ctaKey = btn.dataset.ctaKey;
      window.CrashoutComposerModal?.open();
      window.dispatchEvent(
        new CustomEvent("crashout:feed-cta", {
          detail: { ctaKey, text: "Sponsored recovery tip — draft your move first.", sponsored: true },
        })
      );
    }
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && document.body.classList.contains("upgrade-modal-open")) {
      closeUpgradeModal();
    }
  }

  function initUpgradeModal() {
    upgradeModalEl = document.getElementById("upgrade-modal");
    updateUpgradeModalUi(activeTier);
    document.addEventListener("keydown", handleKeydown);
  }

  function getSponsoredCtaLine() {
    return SPONSORED_CTA;
  }

  function init() {
    document.body.addEventListener("click", handleClick);
    initUpgradeModal();
    renderComposerUpsell();
    renderComposerUpsellBar();
    renderPredictorTeaser();
  }

  window.CrashoutMonetization = {
    TIERS,
    get PREMIUM_FEATURES() {
      return premiumFeatures();
    },
    LANE_SPONSORED,
    activeTier: () => activeTier,
    getTier: () => activeTier,
    setTier: (tier) => {
      activeTier = tier;
      previewTier = tier;
      renderComposerUpsell();
      renderComposerUpsellBar();
      renderPredictorTeaser();
      window.CrashoutPredictor?.refresh?.();
      window.CrashoutRecoveryStreak?.refresh?.();
      window.CrashoutCreatorDashboard?.render?.();
      window.CrashoutMomentumScore?.render?.();
      updateUpgradeModalUi(tier);
      window.CrashoutWorldSignals?.renderStrip?.(null);
      window.CrashoutWorldSignals?.renderProPanel?.();
      window.CrashoutSpikeAlert?.check?.();
      window.CrashoutTabbedFeed?.render?.(null);
    },
    isPremium,
    isFeatureUnlocked,
    injectSponsoredHtml,
    renderPremiumSignalChip,
    renderComposerUpsell,
    renderComposerUpsellBar,
    renderPredictorTeaser,
    getSponsoredCtaLine,
    openUpgrade: openUpgradeModal,
    closeUpgrade: closeUpgradeModal,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
