/**
 * Staff flags — GET /api/staff/flags as table
 */
(function () {
  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function authHeaders() {
    try {
      const token = localStorage.getItem("crashout_access_token");
      if (token) return { Authorization: `Bearer ${token}` };
    } catch (_) {
      /* ignore */
    }
    return {};
  }

  function renderTable(items) {
    const rows = items
      .map(
        (item) => `<tr>
        <td>${escapeHtml(item.item_id || "")}</td>
        <td>${escapeHtml(item.reason || "—")}</td>
        <td>${escapeHtml(String(item.flagged_by ?? "—"))}</td>
        <td>${escapeHtml(item.flagged_at || "")}</td>
      </tr>`
      )
      .join("");
    return `<table class="staff-table">
      <thead><tr><th>Item</th><th>Reason</th><th>By</th><th>When</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  async function load() {
    const res = await fetch("/api/staff/flags", {
      credentials: "same-origin",
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`Staff flags failed (${res.status})`);
    return res.json();
  }

  async function mount(selector) {
    const root = typeof selector === "string" ? document.querySelector(selector) : selector;
    const empty = document.getElementById("staff-flags-empty");
    const errEl = document.getElementById("staff-flags-error");
    if (!root) return;
    try {
      const data = await load();
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        root.innerHTML = "";
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      if (errEl) errEl.hidden = true;
      root.innerHTML = renderTable(items);
    } catch (err) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "Could not load flags (staff login required).";
      }
    }
  }

  window.CrashoutStaffFlags = { mount, load };
})();
