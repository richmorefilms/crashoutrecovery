/**
 * Marketplace packs — tone packs, CTA packs, seed templates.
 * localStorage-backed; Creator+ gating. UI scaffolding only.
 */
(function () {
  const STORAGE_KEY = "crashout_market_packs";
  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;

  const PACKS = {
    tone: [
      {
        id: "tone_clarity",
        type: "tone",
        title: "Clarity Tone Pack",
        desc: "Clean, calm, and stable tone suggestions.",
        items: ["Clear rewrite", "Calm version", "Stable phrasing"],
      },
      {
        id: "tone_spike",
        type: "tone",
        title: "Spike Tone Pack",
        desc: "High-energy tone for moments and reactions.",
        items: ["Hype rewrite", "Spike phrasing", "Reaction booster"],
      },
      {
        id: "tone_sponsored",
        type: "tone",
        sponsored: true,
        sponsor: "Clarity Journal",
        title: "Sponsored: Calm Rewrite Pack",
        desc: "Sponsored tone pack — draft-first phrasing for meltdown windows.",
        items: ["Draft instead of delete", "Pause line", "Morning-you rewrite"],
      },
    ],
    cta: [
      {
        id: "cta_recovery",
        type: "cta",
        title: "Recovery Action Pack",
        desc: "Micro-actions for safe moves and recovery.",
        items: ["Draft instead", "Save draft idea", "Tone shift"],
      },
      {
        id: "cta_sponsored",
        type: "cta",
        sponsored: true,
        sponsor: "Draft Tools",
        title: "Sponsored: Progress Action Pack",
        desc: "Sponsored micro-actions — turn spikes into draft ideas faster.",
        items: ["One-line draft", "Test one variable", "Micro-thread start"],
      },
    ],
    seed: [
      {
        id: "seed_templates",
        type: "seed",
        title: "Draft Template Pack",
        desc: "Starter templates for safe posting.",
        items: ["Short draft", "Neutral draft", "Steady draft"],
      },
      {
        id: "seed_sponsored",
        type: "seed",
        sponsored: true,
        sponsor: "Creator Wire",
        title: "Sponsored: Thread Starter Pack",
        desc: "Sponsored draft templates for calm comebacks.",
        items: ["Turnaround draft", "Soft reset line", "Algo-dip draft"],
      },
    ],
  };

  let previewPack = null;
  let modalEl;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function isUnlocked() {
    return window.CrashoutMonetization?.isFeatureUnlocked?.("marketplace_packs") === true;
  }

  function loadInstalled() {
    try {
      const raw = window.CrashoutUserStore
        ? window.CrashoutUserStore.get(STORAGE_KEY)
        : JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (raw && typeof raw === "object") {
        return {
          tone: Array.isArray(raw.tone) ? raw.tone : [],
          cta: Array.isArray(raw.cta) ? raw.cta : [],
          seed: Array.isArray(raw.seed) ? raw.seed : [],
        };
      }
    } catch (_) {
      /* ignore */
    }
    return { tone: [], cta: [], seed: [] };
  }

  function saveInstalled(data) {
    if (window.CrashoutUserStore) {
      window.CrashoutUserStore.set(STORAGE_KEY, data);
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  function isPackInstalled(pack) {
    const installed = loadInstalled();
    return installed[pack.type]?.some((p) => p.id === pack.id);
  }

  function showToast(message) {
    const toast = document.getElementById("upgrade-toast");
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      toast.hidden = true;
    }, 2400);
  }

  function renderCategory(type, elementId) {
    const list = document.getElementById(elementId);
    if (!list) return;

    list.innerHTML = "";
    const installed = loadInstalled();

    PACKS[type].forEach((pack) => {
      const installedMark = installed[type].some((p) => p.id === pack.id);
      const li = document.createElement("li");
      li.className = "market-pack-item";
      if (pack.sponsored) li.classList.add("market-pack-item--sponsored");
      if (installedMark) li.classList.add("market-pack-item--installed");
      li.dataset.packId = pack.id;
      li.dataset.packType = type;
      li.innerHTML = `
        <span class="market-pack-item-title">${escapeHtml(pack.title)}</span>
        ${pack.sponsored ? `<span class="market-pack-item-sponsor">Sponsored · ${escapeHtml(pack.sponsor)}</span>` : ""}
        <span class="market-pack-item-desc">${escapeHtml(pack.desc)}</span>
        ${installedMark ? '<span class="market-pack-item-badge">Installed</span>' : ""}`;
      li.addEventListener("click", () => openPreview(pack));
      list.appendChild(li);
    });
  }

  function render() {
    const locked = document.getElementById("market-locked");
    const panel = document.getElementById("market-panel");

    if (locked) locked.hidden = isUnlocked();
    panel?.classList.toggle("market-panel--locked", !isUnlocked());

    renderCategory("tone", "market-tone-list");
    renderCategory("cta", "market-cta-list");
    renderCategory("seed", "market-seed-list");
  }

  function openPreview(pack) {
    previewPack = pack;
    const titleEl = document.getElementById("pack-preview-title");
    const descEl = document.getElementById("pack-preview-desc");
    const itemsEl = document.getElementById("pack-preview-items");
    const installBtn = document.getElementById("pack-install-btn");

    if (titleEl) {
      titleEl.textContent = pack.title;
    }
    if (descEl) {
      descEl.textContent = pack.sponsored
        ? `${pack.desc} — by ${pack.sponsor}`
        : pack.desc;
    }
    if (itemsEl) {
      itemsEl.innerHTML = pack.items
        .map((item) => `<li class="pack-preview-item">${escapeHtml(item)}</li>`)
        .join("");
    }
    if (installBtn) {
      const done = isPackInstalled(pack);
      installBtn.textContent = done ? "Already installed" : "Install pack";
      installBtn.disabled = done;
    }

    if (!modalEl) modalEl = document.getElementById("pack-preview-modal");
    if (modalEl) {
      modalEl.hidden = false;
      modalEl.setAttribute("aria-hidden", "false");
      document.body.classList.add("pack-preview-modal-open");
    }
  }

  function closePreview() {
    previewPack = null;
    if (!modalEl) modalEl = document.getElementById("pack-preview-modal");
    if (modalEl) {
      modalEl.hidden = true;
      modalEl.setAttribute("aria-hidden", "true");
      document.body.classList.remove("pack-preview-modal-open");
    }
  }

  function installPack(pack) {
    if (!isUnlocked()) {
      window.CrashoutMonetization?.openUpgrade?.("creator");
      return;
    }

    const installed = loadInstalled();
    if (installed[pack.type].some((p) => p.id === pack.id)) {
      showToast("Pack already installed.");
      closePreview();
      return;
    }

    installed[pack.type].push({
      id: pack.id,
      type: pack.type,
      title: pack.title,
      desc: pack.desc,
      items: [...pack.items],
      sponsored: Boolean(pack.sponsored),
      sponsor: pack.sponsor || null,
      installedAt: new Date().toISOString(),
    });
    saveInstalled(installed);
    showToast(`${pack.title} installed.`);
    closePreview();
    render();
    window.CrashoutMomentumScore?.render?.();
    window.dispatchEvent(new CustomEvent("crashout:pack-installed", { detail: { pack } }));
  }

  function getInstalledItems(type) {
    const installed = loadInstalled();
    const items = [];
    installed[type].forEach((pack) => {
      (pack.items || []).forEach((item) => items.push({ pack, item }));
    });
    return items;
  }

  function appendTonePackPills(toneRowEl, activeTone) {
    if (!toneRowEl || !activeTone) return;

    toneRowEl.querySelectorAll(".crashout-tone-pill--pack").forEach((el) => el.remove());

    const items = getInstalledItems("tone");
    if (!items.length) return;

    items.forEach(({ pack, item }) => {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = "crashout-tone-pill crashout-tone-pill--pack";
      pill.dataset.packItem = item;
      pill.dataset.packId = pack.id;
      pill.title = `${pack.title}: ${item}`;
      pill.textContent = item;
      pill.addEventListener("click", () => {
        const hint = document.getElementById("crashout-tone-hint");
        if (hint) {
          hint.hidden = false;
          hint.textContent = `Pack rewrite: ${item}`;
        }
        window.dispatchEvent(
          new CustomEvent("crashout:pack-tone", { detail: { item, pack } })
        );
      });
      toneRowEl.appendChild(pill);
    });
  }

  function appendCtaPackActions(ctaCardEl) {
    if (!ctaCardEl || ctaCardEl.classList.contains("hidden")) return;

    const actions = ctaCardEl.querySelector(".crashout-cta-actions");
    if (!actions) return;

    actions.querySelectorAll("[data-pack-cta]").forEach((el) => el.remove());

    const items = getInstalledItems("cta");
    items.forEach(({ pack, item }) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "feed-action feed-action--pack";
      btn.dataset.packCta = "true";
      btn.textContent = item;
      btn.title = `${pack.title}: ${item}`;
      btn.addEventListener("click", () => {
        const status = ctaCardEl.querySelector("#feed-post-status");
        if (status) {
          status.hidden = false;
          status.textContent = `Pack action: ${item} — one small reversible step.`;
        }
        window.dispatchEvent(
          new CustomEvent("crashout:pack-cta", { detail: { item, pack } })
        );
      });
      actions.appendChild(btn);
    });
  }

  function applySeedTemplates() {
    const slot = document.getElementById("crashout-seed-templates");
    if (!slot) return;

    const items = getInstalledItems("seed");
    if (!items.length) {
      slot.hidden = true;
      slot.innerHTML = "";
      return;
    }

    slot.hidden = false;
    slot.innerHTML = `
      <span class="crashout-seed-templates-label">${escapeHtml(uiLabel("seed", "Draft idea"))} templates</span>
      <div class="crashout-seed-templates-row">
        ${items
          .map(
            ({ pack, item }) =>
              `<button type="button" class="crashout-seed-template-btn" data-seed-item="${escapeHtml(item)}" title="${escapeHtml(pack.title)}">${escapeHtml(item)}</button>`
          )
          .join("")}
      </div>`;

    slot.querySelectorAll(".crashout-seed-template-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const input = document.getElementById("crashout-input");
        const text = btn.dataset.seedItem || btn.textContent;
        if (input && !input.value.trim()) {
          input.value = `${text}: `;
          input.focus();
        }
        window.dispatchEvent(
          new CustomEvent("crashout:pack-seed", { detail: { item: text } })
        );
      });
    });
  }

  function applyToComposer() {
    applySeedTemplates();
    const toneRow = document.getElementById("crashout-tone-row");
    const active = toneRow?.querySelector(".crashout-tone-pill.detected");
    if (active?.dataset.tone) {
      appendTonePackPills(toneRow, active.dataset.tone);
    }
    appendCtaPackActions(document.getElementById("crashout-cta-card"));
  }

  function showPanel() {
    const panel = document.getElementById("market-panel");
    if (panel) panel.hidden = false;
    render();
  }

  function hidePanel() {
    const panel = document.getElementById("market-panel");
    if (panel) panel.hidden = true;
  }

  function handleClick(e) {
    if (e.target.closest("[data-close-pack-preview]")) {
      closePreview();
      return;
    }
    if (e.target.id === "pack-install-btn" && previewPack) {
      installPack(previewPack);
    }
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && document.body.classList.contains("pack-preview-modal-open")) {
      e.preventDefault();
      closePreview();
    }
  }

  function init() {
    modalEl = document.getElementById("pack-preview-modal");
    document.body.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeydown);
    window.addEventListener("crashout:pack-installed", applyToComposer);
    render();
  }

  window.CrashoutMarketplace = {
    PACKS,
    loadInstalled,
    render,
    showPanel,
    hidePanel,
    openPreview,
    closePreview,
    installPack,
    applyToComposer,
    appendTonePackPills,
    appendCtaPackActions,
    applySeedTemplates,
    isUnlocked,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
