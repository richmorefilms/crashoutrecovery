/**
 * Auth + per-user data sync.
 * Access JWT (short) + refresh token in localStorage.
 * crashout_* keys stay as offline cache; sync to structured SQLite tables when logged in.
 *
 * uiLabel() example with login state:
 *   const label = uiLabel("auth_login", "Log in");
 *   if (CrashoutAuth.isLoggedIn()) {
 *     status = `Synced ${uiLabel("seed", "Draft idea")}s · ${uiLabel("premium_tiers", "Unlock levels")}`;
 *   }
 */
(function () {
  if (window.CrashoutAuth) return;

  const TOKEN_KEY = "crashout_jwt";
  const REFRESH_KEY = "crashout_refresh";
  const USER_KEY = "crashout_user";
  const DATA_KEYS = [
    "crashout_recovery",
    "crashout_seeds",
    "crashout_market_packs",
    "crashout_world_signals",
  ];

  let pendingAction = null;
  let syncTimer = null;
  let wrappedOps = false;
  let refreshing = null;

  const uiLabel = (key, fallback) => window.CrashoutUICopy?.label?.(key) || fallback;
  const uiTip = (key) => window.CrashoutUICopy?.tooltip?.(key) || "";

  function token() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function refreshToken() {
    return localStorage.getItem(REFRESH_KEY) || "";
  }

  function user() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch (_) {
      return null;
    }
  }

  function isLoggedIn() {
    return Boolean((token() || refreshToken()) && user());
  }

  function setSession(accessToken, profile, refresh) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    localStorage.setItem(USER_KEY, JSON.stringify(profile));
    renderChrome();
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    renderChrome();
  }

  function authHeaders(extra) {
    const headers = { "Content-Type": "application/json", ...(extra || {}) };
    const t = token();
    if (t) headers.Authorization = `Bearer ${t}`;
    return headers;
  }

  async function tryRefresh() {
    const current = refreshToken();
    if (!current) return false;
    if (refreshing) return refreshing;

    refreshing = (async () => {
      const res = await fetch("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: current }),
      });
      let body = null;
      try {
        body = await res.json();
      } catch (_) {
        body = null;
      }
      if (!res.ok) {
        clearSession();
        return false;
      }
      setSession(body.access_token, body.user || user(), body.refresh_token);
      return true;
    })().finally(() => {
      refreshing = null;
    });

    return refreshing;
  }

  async function api(path, options, _retried) {
    const res = await fetch(path, {
      ...options,
      headers: authHeaders(options?.headers),
    });
    let body = null;
    try {
      body = await res.json();
    } catch (_) {
      body = null;
    }

    if (res.status === 401 && !_retried && path !== "/auth/refresh") {
      const ok = await tryRefresh();
      if (ok) return api(path, options, true);
      openModal("login");
      const err = new Error((body && body.detail) || "Session expired — log in again");
      err.status = 401;
      throw err;
    }

    if (res.status === 401) {
      clearSession();
      openModal("login");
      const err = new Error((body && body.detail) || "Not authenticated");
      err.status = 401;
      throw err;
    }

    if (!res.ok) {
      const detail = body?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join(", ")
            : `Request failed (${res.status})`;
      const err = new Error(message);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  function cacheGet(key) {
    try {
      const raw = localStorage.getItem(key);
      return raw == null ? null : JSON.parse(raw);
    } catch (_) {
      return null;
    }
  }

  function cacheSet(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function schedulePush() {
    if (!isLoggedIn()) return;
    window.clearTimeout(syncTimer);
    syncTimer = window.setTimeout(() => {
      pushAll().catch(() => {});
    }, 400);
  }

  function setLocal(key, value) {
    cacheSet(key, value);
    schedulePush();
  }

  function getLocal(key) {
    return cacheGet(key);
  }

  async function pushAll() {
    if (!isLoggedIn()) return;
    const data = {};
    DATA_KEYS.forEach((key) => {
      const value = cacheGet(key);
      if (value != null) data[key] = value;
    });
    const tier = window.CrashoutMonetization?.getTier?.();
    if (tier) data.tier = tier;
    await api("/api/user/data", {
      method: "PUT",
      body: JSON.stringify({ data }),
    });
  }

  async function pullAll() {
    if (!isLoggedIn()) return null;
    const bundle = await api("/api/user/data", { method: "GET" });
    DATA_KEYS.forEach((key) => {
      if (bundle[key] != null) cacheSet(key, bundle[key]);
    });
    if (bundle.tier && window.CrashoutMonetization) {
      const raw = window.CrashoutMonetization.setTierRaw || window.CrashoutMonetization.setTier;
      raw.call(window.CrashoutMonetization, bundle.tier);
    }
    window.dispatchEvent(new CustomEvent("crashout:user-data-synced", { detail: bundle }));
    window.CrashoutRecoveryStreak?.refresh?.();
    window.CrashoutCreatorDashboard?.render?.();
    window.CrashoutMomentumScore?.render?.();
    window.CrashoutMarketplace?.render?.();
    window.CrashoutWorldSignals?.renderStrip?.(null);
    window.CrashoutWorldSignals?.renderProPanel?.();
    window.CrashoutTabbedFeed?.render?.(null);
    return bundle;
  }

  function setStatus(message, isError) {
    const el = document.getElementById("auth-status");
    if (!el) return;
    el.hidden = !message;
    el.textContent = message || "";
    el.classList.toggle("auth-status--error", Boolean(isError));
  }

  function syncStatusCopy() {
    // uiLabel() keyed to login state (spec example)
    if (!isLoggedIn()) {
      return `${uiLabel("auth_login", "Log in")} to sync ${uiLabel("seed", "Draft idea")}s · ${uiLabel("premium_tiers", "Unlock levels")}`;
    }
    return `Synced ${uiLabel("seed", "Draft idea")}s · ${uiLabel("premium_tiers", "Unlock levels")}`;
  }

  function renderChrome() {
    const loginBtn = document.getElementById("auth-open-btn");
    const logoutBtn = document.getElementById("auth-logout-btn");
    const sessionEl = document.getElementById("auth-session");
    const nameEl = document.getElementById("auth-user-chip");
    const lede = document.getElementById("auth-modal-lede");
    const profile = user();
    const on = isLoggedIn();

    if (loginBtn) {
      loginBtn.hidden = on;
      const textEl = loginBtn.querySelector(".auth-header-login-text");
      if (textEl) textEl.textContent = uiLabel("auth_login", "Log in");
      else loginBtn.textContent = uiLabel("auth_login", "Log in");
      loginBtn.title = uiTip("auth") || uiLabel("auth", "Account");
    }
    if (sessionEl) sessionEl.hidden = !on;
    if (logoutBtn) {
      logoutBtn.textContent = uiLabel("auth_logout", "Log out");
      logoutBtn.title = uiTip("auth_logout");
    }
    if (nameEl) {
      nameEl.textContent = on ? `@${profile.username}` : "";
      nameEl.title = on ? profile.email : "";
    }
    if (lede) {
      lede.textContent = syncStatusCopy();
    }
  }

  function showPanel(mode) {
    const loginPanel = document.getElementById("auth-panel-login");
    const registerPanel = document.getElementById("auth-panel-register");
    const title = document.getElementById("auth-modal-title");
    const isRegister = mode === "register";
    if (loginPanel) loginPanel.hidden = isRegister;
    if (registerPanel) registerPanel.hidden = !isRegister;
    if (title) {
      title.textContent = isRegister
        ? uiLabel("auth_register", "Create account")
        : uiLabel("auth_login", "Log in");
    }
    document.querySelectorAll(".auth-tab[data-auth-panel]").forEach((tab) => {
      const panel = tab.getAttribute("data-auth-panel");
      const active = panel === (isRegister ? "register" : "login");
      tab.classList.toggle("auth-tab--active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.textContent =
        panel === "register"
          ? uiLabel("auth_register", "Create account")
          : uiLabel("auth_login", "Log in");
    });
    setStatus("");
    renderChrome();
  }

  function openModal(mode, afterLogin) {
    const modal = document.getElementById("auth-modal");
    if (!modal) return;
    pendingAction = typeof afterLogin === "function" ? afterLogin : pendingAction;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("auth-modal-open");
    showPanel(mode === "register" ? "register" : "login");
    window.setTimeout(() => {
      const focusId = mode === "register" ? "auth-register-username" : "auth-login-identity";
      document.getElementById(focusId)?.focus();
    }, 30);
  }

  function closeModal() {
    const modal = document.getElementById("auth-modal");
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("auth-modal-open");
  }

  function requireAuth(action) {
    if (isLoggedIn()) {
      if (typeof action === "function") action();
      return true;
    }
    pendingAction = typeof action === "function" ? action : null;
    openModal("login");
    setStatus(
      `Log in to use ${uiLabel("premium_tiers", "Unlock levels")} and sync ${uiLabel("seed", "Draft idea")}s.`,
      false
    );
    return false;
  }

  function applySession(body) {
    setSession(body.access_token, body.user, body.refresh_token);
  }

  async function register(username, email, password) {
    const body = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
    applySession(body);
    await pushAll();
    await pullAll();
    closeModal();
    const next = pendingAction;
    pendingAction = null;
    next?.();
    return body.user;
  }

  async function login(usernameOrEmail, password) {
    const body = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username_or_email: usernameOrEmail,
        password,
      }),
    });
    applySession(body);
    await pullAll();
    closeModal();
    const next = pendingAction;
    pendingAction = null;
    next?.();
    return body.user;
  }

  async function logout() {
    try {
      if (token()) {
        await api("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken() || null }),
        });
      }
    } catch (_) {
      /* still clear locally */
    }
    clearSession();
    closeModal();
  }

  function wrapMonetizationOps() {
    if (wrappedOps || !window.CrashoutMonetization) return;
    wrappedOps = true;
    const apiSurface = window.CrashoutMonetization;
    const rawSetTier = apiSurface.setTier.bind(apiSurface);
    const rawOpenUpgrade = apiSurface.openUpgrade?.bind(apiSurface);

    apiSurface.setTierRaw = rawSetTier;
    apiSurface.setTier = (tier) => {
      requireAuth(() => {
        rawSetTier(tier);
        schedulePush();
      });
    };

    if (rawOpenUpgrade) {
      apiSurface.openUpgrade = (tier) => {
        requireAuth(() => rawOpenUpgrade(tier));
      };
    }
  }

  function bindForms() {
    document.getElementById("auth-open-btn")?.addEventListener("click", () => openModal("login"));
    document.getElementById("auth-logout-btn")?.addEventListener("click", () => {
      logout().catch(() => clearSession());
    });

    document.querySelectorAll("[data-close-auth]").forEach((el) => {
      el.addEventListener("click", closeModal);
    });

    document.querySelectorAll("[data-auth-panel]").forEach((el) => {
      el.addEventListener("click", () => showPanel(el.getAttribute("data-auth-panel")));
    });

    document.getElementById("auth-login-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const identity = document.getElementById("auth-login-identity")?.value?.trim() || "";
      const password = document.getElementById("auth-login-password")?.value || "";
      setStatus("Signing in…");
      try {
        await login(identity, password);
        setStatus("");
      } catch (err) {
        setStatus(err.message || "Login failed", true);
      }
    });

    document.getElementById("auth-register-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("auth-register-username")?.value?.trim() || "";
      const email = document.getElementById("auth-register-email")?.value?.trim() || "";
      const password = document.getElementById("auth-register-password")?.value || "";
      setStatus("Creating account…");
      try {
        await register(username, email, password);
        setStatus("");
      } catch (err) {
        setStatus(err.message || "Could not create account", true);
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.body.classList.contains("auth-modal-open")) {
        closeModal();
      }
    });
  }

  async function boot() {
    wrapMonetizationOps();
    renderChrome();
    bindForms();

    if (new URLSearchParams(location.search).get("login") === "1") {
      openModal("login");
    }

    if (isLoggedIn()) {
      try {
        if (!token() && refreshToken()) {
          await tryRefresh();
        }
        const me = await api("/auth/me", { method: "GET" });
        localStorage.setItem(USER_KEY, JSON.stringify(me));
        await pullAll();
        renderChrome();
      } catch (_) {
        clearSession();
      }
    }

    window.addEventListener("crashout:upgrade-preview", () => schedulePush());
  }

  window.CrashoutAuth = {
    TOKEN_KEY,
    REFRESH_KEY,
    USER_KEY,
    DATA_KEYS,
    isLoggedIn,
    token,
    refreshToken,
    user,
    openModal,
    closeModal,
    requireAuth,
    register,
    login,
    logout,
    renderChrome,
    syncStatusCopy,
  };

  window.CrashoutUserStore = {
    KEYS: DATA_KEYS,
    get: getLocal,
    set: setLocal,
    push: pushAll,
    pull: pullAll,
    cacheGet,
    cacheSet,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
