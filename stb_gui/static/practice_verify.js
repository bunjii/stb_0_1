(function () {
  "use strict";

  const params = new URLSearchParams(window.location.search);
  const modelPath = params.get("path") || "";

  const el = {
    title: document.getElementById("pvTitle"),
    path: document.getElementById("pvPath"),
    tabs: document.getElementById("pvTabs"),
    main: document.getElementById("pvMain"),
    status: document.getElementById("pvStatus"),
    btnRefresh: document.getElementById("btnPvRefresh"),
  };

  let currentView = null;
  let activeTab = "summary";

  function guiApiOrigin() {
    if (window.__stbGuiOrigin && window.__stbGuiOrigin !== "null") return window.__stbGuiOrigin;
    try {
      if (window.opener && window.opener.__stbGuiOrigin) return window.opener.__stbGuiOrigin;
    } catch (_) {
      /* cross-origin */
    }
    return window.location.origin || "";
  }

  function guiApiUrl(path) {
    const origin = guiApiOrigin();
    if (!origin) throw new Error("GUI API の接続先を特定できません。");
    return origin + (path.startsWith("/") ? path : "/" + path);
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtNum(value, places) {
    if (value === null || value === undefined || value === "") return "-";
    const n = Number(value);
    if (!Number.isFinite(n)) return String(value);
    if (Math.abs(n) < 1e-12) return "0";
    return n.toFixed(places == null ? 3 : places);
  }

  function fmtRatio(value) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return "-";
    return "1/" + (1 / n).toFixed(0);
  }

  function rigiditySymbolRsBar() {
    return "r\u0304s";
  }

  function storyMaxDriftMap(view) {
    const map = new Map();
    for (const row of view.story_drift_rows || []) {
      if (!row.is_story_max) continue;
      const key = String(row.direction).toLowerCase() + "|" + String(row.load_case) + "|" + String(row.story);
      map.set(key, row);
    }
    return map;
  }

  function rigidityDriftValues(r, view, direction) {
    const key = String(direction).toLowerCase() + "|" + String(r.load_case) + "|" + String(r.story);
    const driftRow = storyMaxDriftMap(view).get(key);
    const driftM = driftRow && driftRow.drift_m != null ? Number(driftRow.drift_m) : Number(r.drift_m);
    const heightM = driftRow && driftRow.height_m != null ? Number(driftRow.height_m) : Number(r.height_m);
    if (!Number.isFinite(driftM) || !Number.isFinite(heightM) || heightM <= 0) {
      return { driftM: null, heightM: null, driftAngle: null };
    }
    return {
      driftM: driftM,
      heightM: heightM,
      driftAngle: Math.abs(driftM) / heightM,
    };
  }

  async function fetchJson(path) {
    const res = await fetch(guiApiUrl(path));
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText || "request failed");
    }
    return res.json();
  }

  function setStatus(msg) {
    if (el.status) el.status.textContent = msg || "";
  }

  function renderTabs(view) {
    el.tabs.innerHTML = "";
    (view.tabs || []).forEach(function (tab) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lv-tab" + (tab.id === activeTab ? " active" : "");
      btn.textContent = tab.label;
      btn.disabled = !tab.enabled;
      if (tab.id === activeTab) btn.setAttribute("aria-current", "page");
      btn.addEventListener("click", function () {
        activeTab = tab.id;
        renderView(currentView);
      });
      el.tabs.appendChild(btn);
    });
  }

  function renderSummary(rows) {
    if (!rows || !rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">概要</h2>';
    html += '<dl class="lv-summary-grid">';
    rows.forEach(function (row) {
      const note = row.note ? ' <span class="lv-summary-note">(' + escapeHtml(row.note) + ")</span>" : "";
      html += "<dt>" + escapeHtml(row.label) + "</dt>";
      html += "<dd>" + escapeHtml(row.value) + note + "</dd>";
    });
    html += "</dl></section>";
    return html;
  }

  function renderWarnings(warnings) {
    if (!warnings || !warnings.length) {
      return '<section class="lv-section"><h2 class="lv-section-title">Warnings</h2><p class="pv-ok">警告はありません。</p></section>';
    }
    let html = '<section class="lv-section"><h2 class="lv-section-title">Warnings</h2><ul class="lv-warnings">';
    warnings.forEach(function (w) {
      html += "<li>" + escapeHtml(stripPdfSectionReference(w)) + "</li>";
    });
    html += "</ul></section>";
    return html;
  }

  function renderNotes(notes) {
    if (!notes || !notes.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">Notes</h2><ul class="pv-note-list">';
    notes.forEach(function (n) {
      html += "<li>" + escapeHtml(n) + "</li>";
    });
    html += "</ul></section>";
    return html;
  }

  function stripPdfSectionReference(text) {
    return String(text == null ? "" : text)
      .replace(/PDF\s*2\.5\s*節/g, "")
      .replace(/PDF\s*2\.5/g, "")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  function table(headers, rows, rowFn, title) {
    let html = '<section class="lv-section"><h2 class="lv-section-title">' + escapeHtml(title) + "</h2>";
    if (!rows || !rows.length) return html + '<p class="loads-verify-status">表示できる行がありません。</p></section>';
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    headers.forEach(function (h) { html += "<th>" + escapeHtml(h) + "</th>"; });
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) { html += rowFn(r); });
    html += "</tbody></table></div></section>";
    return html;
  }

  function storyLevelMap(view) {
    const map = new Map();
    (view.story_rows || []).forEach(function (s) {
      const z = Number(s.top_elevation != null ? s.top_elevation : s.elevation);
      if (Number.isFinite(z)) map.set(String(s.story), z);
    });
    return map;
  }

  function storyFallbackRank(story) {
    const n = Number(String(story).replace(/[^\d.-]/g, ""));
    return Number.isFinite(n) ? n : Number.NEGATIVE_INFINITY;
  }

  function upperStoriesFirst(rows, view) {
    const levels = storyLevelMap(view);
    return (rows || []).slice().sort(function (a, b) {
      const za = levels.has(String(a.story)) ? levels.get(String(a.story)) : storyFallbackRank(a.story);
      const zb = levels.has(String(b.story)) ? levels.get(String(b.story)) : storyFallbackRank(b.story);
      if (za !== zb) return zb - za;
      return String(b.story).localeCompare(String(a.story), "ja", { numeric: true });
    });
  }

  function renderDrift(view) {
    return table(
      ["階", "方向", "LC", "部材", "下節点", "上節点", "δ m", "h m", "δ/h", "逆数", "最大"],
      view.story_drift_rows,
      function (r) {
        return "<tr>"
          + "<td>" + escapeHtml(r.story) + "</td>"
          + "<td>" + escapeHtml(String(r.direction).toUpperCase()) + "</td>"
          + '<td class="num">' + escapeHtml(r.load_case) + "</td>"
          + '<td class="num">' + escapeHtml(r.element_id) + "</td>"
          + '<td class="num">' + escapeHtml(r.lower_node) + "</td>"
          + '<td class="num">' + escapeHtml(r.upper_node) + "</td>"
          + '<td class="num">' + fmtNum(r.drift_m, 6) + "</td>"
          + '<td class="num">' + fmtNum(r.height_m, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.drift_angle, 6) + "</td>"
          + '<td class="num pv-nowrap">' + fmtRatio(r.drift_angle) + "</td>"
          + "<td>" + (r.is_story_max ? "max" : "") + "</td>"
          + "</tr>";
      },
      "層間変形角"
    );
  }

  function renderEccentricity(view) {
    return table(
      ["階", "Xg", "Yg", "Xs", "Ys", "ex", "ey", "KX", "KY", "KR", "rex", "rey", "Rex", "Rey", "FeX", "FeY", "状態"],
      upperStoriesFirst(view.eccentricity_rows, view),
      function (r) {
        return "<tr>"
          + "<td>" + escapeHtml(r.story) + "</td>"
          + '<td class="num">' + fmtNum(r.xg, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.yg, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.xs, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.ys, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.ex, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.ey, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.kx_kN_m, 1) + "</td>"
          + '<td class="num">' + fmtNum(r.ky_kN_m, 1) + "</td>"
          + '<td class="num">' + fmtNum(r.kr_kN_m, 1) + "</td>"
          + '<td class="num">' + fmtNum(r.rex_m, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.rey_m, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.re_x, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.re_y, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.fe_x, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.fe_y, 3) + "</td>"
          + "<td>" + escapeHtml(r.status) + "</td>"
          + "</tr>";
      },
      "偏心率"
    );
  }

  function renderRigidityTable(rows, view, title, direction) {
    const rsBar = rigiditySymbolRsBar();
    const headers = [
      "階",
      "LC",
      "δ (m)",
      "h (m)",
      "δ/h",
      "rs",
      rsBar,
      "Rs",
      "Fs",
      "状態",
    ];
    return table(
      headers,
      upperStoriesFirst(rows, view),
      function (r) {
        const drift = rigidityDriftValues(r, view, direction);
        const rs = r.inverse_ratio != null ? Number(r.inverse_ratio) : (
          drift.driftAngle != null ? 1 / drift.driftAngle : null
        );
        const rsBarVal = r.mean_inverse_ratio != null ? Number(r.mean_inverse_ratio) : null;
        return "<tr>"
          + "<td>" + escapeHtml(r.story) + "</td>"
          + '<td class="num">' + escapeHtml(r.load_case) + "</td>"
          + '<td class="num">' + fmtNum(drift.driftM, 6) + "</td>"
          + '<td class="num">' + fmtNum(drift.heightM, 3) + "</td>"
          + '<td class="num">' + fmtNum(drift.driftAngle, 6) + "</td>"
          + '<td class="num">' + fmtNum(rs, 1) + "</td>"
          + '<td class="num">' + fmtNum(rsBarVal, 1) + "</td>"
          + '<td class="num">' + fmtNum(r.rigidity_ratio, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.fs, 3) + "</td>"
          + "<td>" + escapeHtml(r.status) + "</td>"
          + "</tr>";
      },
      title
    );
  }

  function rigidityRowsForDirection(rows, direction) {
    const dir = String(direction).toLowerCase();
    return (rows || []).filter(function (r) {
      return String(r.direction).toLowerCase() === dir;
    });
  }

  function renderRigidity(view) {
    const rows = view.rigidity_ratio_rows || [];
    return renderRigidityTable(rigidityRowsForDirection(rows, "x"), view, "剛性率（X方向）", "x")
      + renderRigidityTable(rigidityRowsForDirection(rows, "y"), view, "剛性率（Y方向）", "y");
  }

  function renderStiffness(view) {
    return table(
      ["階", "部材", "分類", "X", "Y", "DXX kN/m", "DXY kN/m", "DYY kN/m", "状態"],
      upperStoriesFirst(view.member_stiffness_rows, view),
      function (r) {
        return "<tr>"
          + "<td>" + escapeHtml(r.story) + "</td>"
          + '<td class="num">' + escapeHtml(r.element_id) + "</td>"
          + "<td>" + escapeHtml(r.member_class || "-") + "</td>"
          + '<td class="num">' + fmtNum(r.x, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.y, 3) + "</td>"
          + '<td class="num">' + fmtNum(r.dxx_kN_m, 1) + "</td>"
          + '<td class="num">' + fmtNum(r.dxy_kN_m, 1) + "</td>"
          + '<td class="num">' + fmtNum(r.dyy_kN_m, 1) + "</td>"
          + "<td>" + escapeHtml(r.status) + "</td>"
          + "</tr>";
      },
      "鉛直部材水平剛性"
    );
  }

  function renderView(view) {
    if (!view) return;
    renderTabs(view);
    el.title.textContent = view.title || "構造指標";
    el.path.textContent = (view.dat_path || "") + (view.project_path ? " · " + view.project_path : "");
    let html = "";
    if (activeTab === "summary") html = renderSummary(view.summary) + renderWarnings(view.warnings) + renderNotes(view.notes);
    else if (activeTab === "drift") html = renderDrift(view);
    else if (activeTab === "eccentricity") html = renderEccentricity(view) + renderStiffness(view);
    else if (activeTab === "rigidity") html = renderRigidity(view);
    else if (activeTab === "warnings") html = renderWarnings(view.warnings) + renderNotes(view.notes);
    el.main.innerHTML = html || '<p class="loads-verify-status">表示できる内容がありません。</p>';
  }

  async function loadView() {
    if (!modelPath) {
      setStatus("モデルパスが指定されていません。");
      return;
    }
    setStatus("読み込み中...");
    try {
      currentView = await fetchJson("/api/practice/summary?path=" + encodeURIComponent(modelPath));
      setStatus("");
      renderView(currentView);
    } catch (ex) {
      el.main.innerHTML = '<p class="loads-verify-status">Error: ' + escapeHtml(ex.message) + "</p>";
    }
  }

  if (el.btnRefresh) el.btnRefresh.addEventListener("click", loadView);
  loadView();
})();
