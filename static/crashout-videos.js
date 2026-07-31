/**
 * Crashout video clips — loads /videos.json, embeds YouTube (or search fallback),
 * and auto-resolves missing IDs via /api/youtube/resolve (server-side API key).
 * Modules: risk_check | momentum | spike_alert | console_recipes
 */
(function () {
  let catalog = { clips: {}, modules: {} };
  let ready = null;
  let toastTimer = null;
  let lastSpikeToastAt = 0;
  let resolveInFlight = null;
  const SPIKE_TOAST_COOLDOWN_MS = 20000;
  const resolveMemo = new Map();

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function load() {
    if (ready) return ready;
    ready = fetch("/videos.json", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("videos.json missing"))))
      .then((data) => {
        catalog = {
          clips: data.clips || {},
          modules: data.modules || {},
        };
        return catalog;
      })
      .catch(() => {
        catalog = { clips: {}, modules: {} };
        return catalog;
      });
    return ready;
  }

  function getClip(refId) {
    const clip = catalog.clips[refId];
    if (!clip) return null;
    return { id: refId, ...clip };
  }

  function patchClip(refId, patch) {
    if (!catalog.clips[refId]) return null;
    Object.assign(catalog.clips[refId], patch);
    return getClip(refId);
  }

  function moduleClips(moduleId) {
    const ids = catalog.modules[moduleId] || [];
    return ids.map(getClip).filter(Boolean);
  }

  function allClips() {
    return Object.keys(catalog.clips).map(getClip).filter(Boolean);
  }

  function pick(moduleId) {
    const list = moduleClips(moduleId);
    if (!list.length) return null;
    return list[Math.floor(Math.random() * list.length)];
  }

  function orderedMomentIds() {
    const orderedIds = [];
    const seen = new Set();
    ["momentum", "spike_alert", "risk_check", "console_recipes"].forEach((mod) => {
      (catalog.modules[mod] || []).forEach((id) => {
        if (seen.has(id)) return;
        seen.add(id);
        orderedIds.push(id);
      });
    });
    Object.keys(catalog.clips).forEach((id) => {
      if (seen.has(id)) return;
      seen.add(id);
      orderedIds.push(id);
    });
    return orderedIds;
  }

  /** Feed-shaped cards for the Moments lane (ordered by module priority). */
  function momentFeedItems() {
    return orderedMomentIds()
      .map(getClip)
      .filter(Boolean)
      .map((clip) => {
        const tags = clip.tags || [];
        let category = "sideways";
        if (tags.includes("recovery") || tags.includes("console_recipes") || tags.includes("interview")) {
          category = "turnaround";
        } else if (tags.includes("risk_check") || tags.includes("prevention")) {
          category = "bad_decision";
        } else if (tags.includes("spike_alert") || tags.includes("crashout")) {
          category = "spike_moment";
        } else if (tags.includes("momentum") || tags.includes("crash_dummy")) {
          category = "reaction";
        }

        let tone = "direct";
        if (category === "turnaround") tone = "calm";
        else if (tags.includes("humorous") || category === "reaction") tone = "humorous";
        else if (tags.includes("prevention")) tone = "strategic";

        const thumb =
          clip.thumbnail ||
          clip.thumbnailUrl ||
          (clip.youtubeId ? `https://img.youtube.com/vi/${clip.youtubeId}/hqdefault.jpg` : "");

        return {
          id: clip.id,
          videoId: clip.id,
          youtubeId: clip.youtubeId || null,
          source: clip.source || (clip.youtubeId ? "manual" : null),
          searchQuery: clip.searchQuery || clip.title,
          thumbnailUrl: thumb,
          channel: clip.channel || null,
          tone,
          category,
          title: clip.title,
          description:
            tags.includes("recovery") || tags.includes("console_recipes")
              ? "Recovery narrative — watch, then take one reversible move."
              : "Crashout culture clip — pause before you match this energy.",
          duration: clip.duration || clip.durationLabel || (clip.youtubeId ? "Watch" : "Search"),
          creator: clip.channel
            ? clip.channel
            : tags.includes("gucci")
              ? "Gucci Mane arc"
              : tags.includes("pooh")
                ? "Crashout culture"
                : "Crashout Recovery",
          cta: category === "turnaround" ? "seed_post" : "draft_dont_delete",
        };
      });
  }

  function watchUrl(clip) {
    if (clip.youtubeId) return `https://www.youtube.com/watch?v=${clip.youtubeId}`;
    const q = encodeURIComponent(clip.searchQuery || clip.title || "");
    return `https://www.youtube.com/results?search_query=${q}`;
  }

  function embedUrl(clip) {
    if (clip.youtubeId) {
      return `https://www.youtube-nocookie.com/embed/${clip.youtubeId}?rel=0&modestbranding=1`;
    }
    return null;
  }

  function thumbUrl(clip) {
    if (clip.thumbnail) return clip.thumbnail;
    if (clip.thumbnailUrl) return clip.thumbnailUrl;
    if (clip.youtubeId) return `https://img.youtube.com/vi/${clip.youtubeId}/hqdefault.jpg`;
    return "";
  }

  async function resolveQuery(query, options = {}) {
    const q = (query || "").trim();
    if (!q) return null;

    const { manualId = null, refId = null, persist = false, force = false } = options;
    if (!manualId && !force && !persist && resolveMemo.has(q)) return resolveMemo.get(q);

    const body = {
      query: q,
      manual_id: manualId || null,
      persist: Boolean(persist || manualId || refId),
    };
    if (refId) body.refId = refId;

    const promise = fetch("/api/youtube/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          const detail = err.detail;
          throw new Error(
            typeof detail === "string" ? detail : `Resolve failed (${res.status})`
          );
        }
        return res.json();
      })
      .catch((err) => {
        resolveMemo.delete(q);
        throw err;
      });

    if (!manualId && !persist) resolveMemo.set(q, promise);
    return promise;
  }

  async function resolveClip(refId) {
    const clip = getClip(refId);
    if (!clip) return null;
    if (clip.youtubeId) return clip;

    const q = clip.searchQuery || clip.title;
    if (!q) return clip;

    try {
      const data = await resolveQuery(q, { refId });
      if (data?.youtubeId) {
        return patchClip(refId, {
          youtubeId: data.youtubeId,
          source: data.source || "auto",
          title: data.title || clip.title,
          channel: data.channel || null,
          duration: data.duration || clip.duration,
          thumbnail: data.thumbnail || null,
          thumbnailUrl: data.thumbnail || null,
        });
      }
    } catch {
      /* keep search fallback */
    }
    return getClip(refId);
  }

  async function refreshCatalog() {
    ready = null;
    await load();
    fillHelpShelves();
    window.dispatchEvent(new CustomEvent("crashout:videos-ready", { detail: { catalog } }));
  }

  async function submitManualId({ query, manualId, refId }) {
    const data = await resolveQuery(query, {
      manualId: manualId || null,
      refId: refId || null,
      persist: true,
      force: true,
    });
    await refreshCatalog();
    if (data?.youtubeId) {
      showToast(
        {
          id: data.refId || refId || data.youtubeId,
          title: data.title || query,
          youtubeId: data.youtubeId,
          searchQuery: query,
          thumbnail: data.thumbnail,
        },
        "Added · crashout clip"
      );
    }
    return data;
  }

  async function resolveMissingIds() {
    if (resolveInFlight) return resolveInFlight;
    resolveInFlight = (async () => {
      const missing = allClips().filter((c) => !c.youtubeId && (c.searchQuery || c.title));
      for (const clip of missing) {
        await resolveClip(clip.id);
      }
      window.dispatchEvent(new CustomEvent("crashout:videos-ready", { detail: { catalog } }));
    })().finally(() => {
      resolveInFlight = null;
    });
    return resolveInFlight;
  }

  function cardHtml(clip, options = {}) {
    if (!clip) return "";
    const { playLabel = "Play clip", compact = false } = options;
    const embed = embedUrl(clip);
    const external = watchUrl(clip);
    const media = embed
      ? `<div class="crashout-video-frame">
           <iframe
             src="${escapeHtml(embed)}"
             title="${escapeHtml(clip.title)}"
             loading="lazy"
             allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
             allowfullscreen
           ></iframe>
         </div>`
      : `<div class="crashout-video-frame crashout-video-frame--poster">
           <p class="crashout-video-poster-title">${escapeHtml(clip.title)}</p>
           <a class="crashout-video-play" href="${escapeHtml(external)}" target="_blank" rel="noopener">${escapeHtml(playLabel)}</a>
           <p class="crashout-video-fallback-note">No embed ID yet — opens YouTube search</p>
         </div>`;

    return `
      <article class="crashout-video-card unified-card neon-card${compact ? " crashout-video-card--compact" : ""}" data-video-id="${escapeHtml(clip.id)}">
        ${media}
        <div class="crashout-video-meta">
          <p class="crashout-video-title">${escapeHtml(clip.title)}</p>
          <div class="crashout-video-actions">
            <a class="crashout-video-play crashout-video-play--ghost" href="${escapeHtml(external)}" target="_blank" rel="noopener">Open on YouTube</a>
          </div>
        </div>
      </article>`;
  }

  function thumbTileHtml(item) {
    const thumb = item.thumbnailUrl
      ? ` style="background-image:url('${escapeHtml(item.thumbnailUrl)}')"`
      : "";
    const badge = item.youtubeId ? "Play" : "Search";
    const source = item.source ? `<span class="moments-thumb-source">${escapeHtml(item.source)}</span>` : "";
    const canManual = window.CrashoutMonetization?.isPremium?.("creator");
    const setId = canManual
      ? `<button type="button" class="moments-thumb-set-id" data-video-manual="${escapeHtml(item.videoId || item.id)}">Set ID</button>`
      : "";
    return `
      <div class="moments-thumb-card unified-card neon-card">
        <button type="button" class="moments-thumb-tile${item.youtubeId ? "" : " moments-thumb-tile--search"}" data-video-play="${escapeHtml(item.videoId || item.id)}" aria-label="Play ${escapeHtml(item.title)}">
          <span class="moments-thumb-media"${thumb}></span>
          <span class="moments-thumb-badge">${escapeHtml(badge)}</span>
          <span class="moments-thumb-title">${escapeHtml(item.title)}</span>
          ${source}
        </button>
        ${setId}
      </div>`;
  }

  function renderMomentsGridHtml() {
    const items = momentFeedItems();
    if (!items.length) {
      return `<p class="crashout-video-empty">No crashout clips mapped yet.</p>`;
    }
    return `
      <section class="moments-video-grid-wrap" aria-label="Crashout video moments">
        <header class="moments-video-grid-header">
          <div>
            <h4 class="moments-video-grid-title">Crashout clips</h4>
            <p class="moments-video-grid-desc">Tap a thumbnail to watch. Creators can add videos with a search query or manual YouTube ID.</p>
          </div>
        </header>
        <div class="moments-video-grid grid">
          ${items.map(thumbTileHtml).join("")}
        </div>
      </section>`;
  }

  function renderShelf(container, moduleId, options = {}) {
    if (!container) return;
    const clips = moduleClips(moduleId);
    if (!clips.length) {
      container.innerHTML = `<p class="crashout-video-empty">No clips mapped for ${escapeHtml(moduleId)}.</p>`;
      return;
    }
    const heading = options.heading
      ? `<h4 class="crashout-video-shelf-title">${escapeHtml(options.heading)}</h4>`
      : "";
    const limit = options.limit || clips.length;
    container.innerHTML = `
      ${heading}
      <div class="crashout-video-shelf-grid grid">
        ${clips.slice(0, limit).map((clip) => cardHtml(clip, { compact: true })).join("")}
      </div>`;
  }

  function ensureToast() {
    let el = document.getElementById("crashout-video-toast");
    if (el) return el;
    el = document.createElement("aside");
    el.id = "crashout-video-toast";
    el.className = "crashout-video-toast";
    el.hidden = true;
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "Crashout clip");
    document.body.appendChild(el);
    return el;
  }

  function hideToast() {
    const el = document.getElementById("crashout-video-toast");
    if (!el) return;
    el.hidden = true;
    el.innerHTML = "";
  }

  function showToast(clip, kicker) {
    if (!clip) return;
    const el = ensureToast();
    el.hidden = false;
    el.innerHTML = `
      <div class="crashout-video-toast-inner">
        <header class="crashout-video-toast-header">
          <p class="crashout-video-toast-kicker">${escapeHtml(kicker || "Crashout clip")}</p>
          <button type="button" class="crashout-video-toast-close" data-video-toast-close aria-label="Close">×</button>
        </header>
        ${cardHtml(clip, { playLabel: "Search on YouTube" })}
      </div>`;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(hideToast, 45000);
  }

  async function playInToast(refId, kicker) {
    const el = ensureToast();
    el.hidden = false;
    el.innerHTML = `
      <div class="crashout-video-toast-inner">
        <header class="crashout-video-toast-header">
          <p class="crashout-video-toast-kicker">${escapeHtml(kicker || "Moments · crashout clip")}</p>
          <button type="button" class="crashout-video-toast-close" data-video-toast-close aria-label="Close">×</button>
        </header>
        <p class="crashout-video-loading">Loading clip…</p>
      </div>`;

    let clip = getClip(refId);
    if (!clip) {
      hideToast();
      return;
    }

    if (!clip.youtubeId) {
      clip = (await resolveClip(refId)) || clip;
    }

    showToast(clip, kicker || "Moments · crashout clip");
  }

  function mountInPredictor(analysis) {
    const host = document.getElementById("bad-decision-predictor");
    if (!host || host.hidden) return;

    const level = analysis?.spikeLevel || "";
    const risky = ["rising", "hot"].includes(level) || (analysis?.score || 0) >= 4;
    if (!risky) {
      host.querySelector(".crashout-video-inline")?.remove();
      return;
    }

    const clip = pick("risk_check");
    if (!clip) return;

    let slot = host.querySelector(".crashout-video-inline");
    if (!slot) {
      slot = document.createElement("div");
      slot.className = "crashout-video-inline";
      host.querySelector(".predictor-panel-inner")?.appendChild(slot);
    }
    slot.innerHTML = `
      <p class="crashout-video-inline-kicker">Crashout example — pause before you match this energy</p>
      ${cardHtml(clip, { compact: true, playLabel: "Play" })}`;
  }

  function onSpikeAlert() {
    const now = Date.now();
    if (now - lastSpikeToastAt < SPIKE_TOAST_COOLDOWN_MS) return;
    lastSpikeToastAt = now;

    const preferred = ["turn0video5", "turn0video20", "turn0video21", "turn0video19"]
      .map(getClip)
      .filter(Boolean);
    const clip = preferred.length
      ? preferred[Math.floor(Math.random() * preferred.length)]
      : pick("spike_alert");
    if (clip?.id) playInToast(clip.id, "World flash · crashout clip");
    else showToast(clip, "World flash · crashout clip");
  }

  function fillModuleShelves(moduleId, options) {
    document.querySelectorAll(`[data-video-module="${moduleId}"]`).forEach((el) => {
      renderShelf(el, moduleId, options);
    });
  }

  function fillHelpShelves() {
    fillModuleShelves("risk_check", {
      heading: "Risk check — crashout examples",
      limit: 3,
    });
    fillModuleShelves("spike_alert", {
      heading: "World flash — culture clips",
      limit: 3,
    });
    fillModuleShelves("momentum", {
      heading: "Momentum — Crash Dummy arc",
      limit: 3,
    });
    fillModuleShelves("console_recipes", {
      heading: "Console recipes — reflection / recovery",
      limit: 4,
    });
  }

  function bind() {
    document.body.addEventListener("click", (e) => {
      if (e.target.closest("[data-video-toast-close]")) {
        hideToast();
        return;
      }
      if (e.target.closest("[data-video-manual-open]")) {
        openManualModal();
        return;
      }
      const setBtn = e.target.closest("[data-video-manual]");
      if (setBtn) {
        openManualModal(setBtn.dataset.videoManual);
      }
    });

    window.addEventListener("crashout:predictor-updated", (e) => {
      mountInPredictor(e.detail?.analysis);
    });

    window.addEventListener("crashout:spike-alert", () => {
      onSpikeAlert();
    });
  }

  function ensureManualModal() {
    let el = document.getElementById("video-manual-modal");
    if (el) return el;
    el = document.createElement("div");
    el.id = "video-manual-modal";
    el.className = "video-manual-modal";
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = `
      <div class="video-manual-modal-backdrop" data-close-video-manual tabindex="-1"></div>
      <div class="video-manual-modal-sheet" role="dialog" aria-modal="true" aria-labelledby="video-manual-title">
        <header class="video-manual-header">
          <h2 id="video-manual-title" class="video-manual-title">Add Crashout Video</h2>
          <button type="button" class="video-manual-close" data-close-video-manual aria-label="Close">×</button>
        </header>
        <form id="video-manual-form" class="video-manual-form">
          <label class="video-manual-label">
            Search query
            <input id="video-manual-query" class="video-manual-input" type="text" required maxlength="500" placeholder="Gucci Mane SPEAKS OUT…" />
          </label>
          <label class="video-manual-label">
            YouTube ID (optional manual override)
            <input id="video-manual-id" class="video-manual-input" type="text" maxlength="200" placeholder="m65MJSC1Jto or https://youtu.be/…" />
          </label>
          <details class="video-manual-advanced">
            <summary>Update existing clip (optional)</summary>
            <label class="video-manual-label">
              Clip
              <select id="video-manual-ref" class="video-manual-input">
                <option value="">— New clip —</option>
              </select>
            </label>
          </details>
          <p id="video-manual-status" class="video-manual-status" role="status" hidden></p>
          <div class="video-manual-actions">
            <button type="submit" class="video-manual-submit">Submit</button>
            <button type="button" class="video-manual-cancel" data-close-video-manual>Cancel</button>
          </div>
        </form>
        <div id="video-manual-preview" class="video-manual-preview" hidden></div>
      </div>`;
    document.body.appendChild(el);

    el.addEventListener("click", (e) => {
      if (e.target.closest("[data-close-video-manual]")) closeManualModal();
    });

    el.querySelector("#video-manual-ref")?.addEventListener("change", () => {
      const ref = el.querySelector("#video-manual-ref").value;
      if (!ref) return;
      const clip = getClip(ref);
      if (!clip) return;
      el.querySelector("#video-manual-query").value = clip.searchQuery || clip.title || "";
      el.querySelector("#video-manual-id").value = clip.youtubeId || "";
    });

    el.querySelector("#video-manual-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!window.CrashoutMonetization?.isPremium?.("creator")) {
        window.CrashoutMonetization?.openUpgrade?.("creator");
        return;
      }
      const refId = el.querySelector("#video-manual-ref").value || null;
      const query = el.querySelector("#video-manual-query").value.trim();
      const manualId = el.querySelector("#video-manual-id").value.trim() || null;
      const status = el.querySelector("#video-manual-status");
      const preview = el.querySelector("#video-manual-preview");
      const submit = el.querySelector(".video-manual-submit");
      status.hidden = false;
      status.textContent = "Saving…";
      preview.hidden = true;
      submit.disabled = true;
      try {
        const data = await submitManualId({ query, manualId, refId });
        status.textContent = `Saved (${data.source}) — ${data.youtubeId}`;
        preview.hidden = false;
        preview.innerHTML = cardHtml(
          {
            id: data.refId || refId || data.youtubeId,
            title: data.title || query,
            youtubeId: data.youtubeId,
            searchQuery: query,
            thumbnail: data.thumbnail,
          },
          { playLabel: "Watch" }
        );
        window.CrashoutTabbedFeed?.setActiveTab?.("moments");
        window.setTimeout(() => closeManualModal(), 700);
      } catch (err) {
        status.textContent = err.message || "Could not add video";
      } finally {
        submit.disabled = false;
      }
    });

    return el;
  }

  function openManualModal(prefRefId) {
    if (!window.CrashoutMonetization?.isPremium?.("creator")) {
      window.CrashoutMonetization?.openUpgrade?.("creator");
      return;
    }
    const el = ensureManualModal();
    const select = el.querySelector("#video-manual-ref");
    const clips = allClips();
    select.innerHTML =
      `<option value="">— New clip —</option>` +
      clips
        .map(
          (c) =>
            `<option value="${escapeHtml(c.id)}">${escapeHtml(c.title || c.id)}</option>`
        )
        .join("");
    if (prefRefId && clips.some((c) => c.id === prefRefId)) {
      select.value = prefRefId;
      select.dispatchEvent(new Event("change"));
    } else {
      select.value = "";
      el.querySelector("#video-manual-query").value = "";
      el.querySelector("#video-manual-id").value = "";
    }
    el.querySelector("#video-manual-status").hidden = true;
    el.querySelector("#video-manual-preview").hidden = true;
    el.hidden = false;
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("video-manual-open");
    el.querySelector("#video-manual-query")?.focus();
  }

  function closeManualModal() {
    const el = document.getElementById("video-manual-modal");
    if (!el) return;
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
    document.body.classList.remove("video-manual-open");
  }

  async function init() {
    await load();
    bind();
    fillHelpShelves();
    window.dispatchEvent(new CustomEvent("crashout:videos-ready", { detail: { catalog } }));
    resolveMissingIds().catch(() => {});
  }

  window.CrashoutVideos = {
    load,
    getClip,
    moduleClips,
    allClips,
    pick,
    momentFeedItems,
    resolveQuery,
    resolveClip,
    resolveMissingIds,
    submitManualId,
    playInToast,
    refreshCatalog,
    openAddVideoModal: openManualModal,
    closeManualModal,
    cardHtml,
    renderShelf,
    renderMomentsGridHtml,
    showToast,
    hideToast,
    mountInPredictor,
    fillHelpShelves,
    watchUrl,
    embedUrl,
    thumbUrl,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
