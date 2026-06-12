(function () {
  "use strict";

  const params = new URLSearchParams(window.location.search);
  const modelPath = params.get("path") || "";

  const el = {
    title: document.getElementById("lvTitle"),
    path: document.getElementById("lvPath"),
    tabs: document.getElementById("lvTabs"),
    main: document.getElementById("lvMain"),
    status: document.getElementById("lvStatus"),
    btnRefresh: document.getElementById("btnLvRefresh"),
    btnApply: document.getElementById("btnLvApply"),
    btnProject: document.getElementById("btnLvProject"),
  };

  let currentView = null;
  let activeTab = "seismic";
  let selectedWindCaseId = null;

  function apiPathForTab(tab) {
    if (tab === "wind") return "/api/loads/wind";
    return "/api/loads/seismic";
  }

  function applyPathForTab(tab) {
    if (tab === "wind") return "/api/loads/wind/apply";
    return "/api/loads/seismic/apply";
  }

  function guiApiOrigin() {
    if (window.__stbGuiOrigin && window.__stbGuiOrigin !== "null") {
      return window.__stbGuiOrigin;
    }
    try {
      if (window.opener && window.opener.__stbGuiOrigin) {
        return window.opener.__stbGuiOrigin;
      }
    } catch (_) {
      /* cross-origin */
    }
    const origin = window.location.origin;
    return origin && origin !== "null" ? origin : "";
  }

  function guiApiUrl(path) {
    const rel = path.startsWith("/") ? path : "/" + path;
    const origin = guiApiOrigin();
    if (!origin) throw new Error("GUI API の接続先を特定できません。");
    return origin + rel;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtNum(value, places) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    if (!Number.isFinite(n)) return String(value);
    if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));
    return n.toFixed(places !== undefined ? places : 3);
  }

  function setStatus(msg) {
    if (el.status) el.status.textContent = msg || "";
  }

  async function fetchJson(path, options) {
    const url = guiApiUrl(path);
    let res;
    try {
      res = await fetch(url, options);
    } catch (ex) {
      throw new Error("API 接続に失敗しました: " + ex.message);
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      throw new Error(typeof detail === "string" ? detail : "HTTP " + res.status);
    }
    return res.json();
  }

  function renderTabs(view) {
    el.tabs.innerHTML = "";
    activeTab = view.active_tab || activeTab;
    (view.tabs || []).forEach(function (tab) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lv-tab" + (tab.id === activeTab ? " active" : "");
      if (!tab.enabled) btn.classList.add("lv-tab-disabled");
      btn.textContent = tab.label;
      btn.dataset.tabId = tab.id;
      btn.disabled = !tab.enabled;
      if (tab.enabled && tab.id === activeTab) {
        btn.setAttribute("aria-current", "page");
      }
      if (!tab.enabled) {
        btn.title = "今後対応予定";
      } else if (tab.id !== activeTab) {
        btn.addEventListener("click", function () {
          activeTab = tab.id;
          loadView();
        });
      }
      el.tabs.appendChild(btn);
    });
  }

  function renderSummary(view) {
    const rows = view.summary || [];
    if (!rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">算定条件・合計</h2>';
    html += '<dl class="lv-summary-grid">';
    rows.forEach(function (row) {
      const unit = row.unit ? " " + escapeHtml(row.unit) : "";
      let value = escapeHtml(row.value) + unit;
      if (row.note) {
        value += ' <span class="lv-summary-note">(' + escapeHtml(row.note) + ")</span>";
      }
      html += "<dt>" + escapeHtml(row.label) + "</dt>";
      html += "<dd>" + value + "</dd>";
    });
    html += "</dl></section>";
    return html;
  }

  function renderNotice(text) {
    if (!text) return "";
    return '<section class="lv-section"><h2 class="lv-section-title">注意</h2>'
      + '<p class="lv-section-note">' + escapeHtml(text) + "</p></section>";
  }

  function renderRawWeightTable(rows) {
    if (!rows || !rows.length) return "";
    const hasRole = rows.some(function (r) { return r.mass_role; });
    let html = '<section class="lv-section"><h2 class="lv-section-title">階別重量集計 (Wi)</h2>';
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>階</th><th>階レベル m</th><th>階高 m</th><th>Wi kN</th>";
    if (hasRole) html += "<th>質量役割</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += "<td>" + escapeHtml(r.story) + "</td>";
      html += '<td class="num">' + fmtNum(r.story_level_m) + "</td>";
      html += '<td class="num">' + fmtNum(r.height_m) + "</td>";
      html += '<td class="num">' + fmtNum(r.weight_kN) + "</td>";
      if (hasRole) html += "<td>" + escapeHtml(r.mass_role || "—") + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function renderMassLevelTable(view) {
    const rows = view.mass_level_rows;
    if (!rows || !rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">質量レベル・Ai 分布 (非モーダル)</h2>';
    if (view.alpha_i_note) {
      html += '<p class="lv-section-note">' + escapeHtml(view.alpha_i_note) + "</p>";
    }
    if (view.wi_above_note) {
      html += '<p class="lv-section-note">' + escapeHtml(view.wi_above_note) + "</p>";
    }
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>階</th><th>Wi kN</th><th>当該階以上ΣWi kN</th><th>alpha_i</th><th>Ai</th><th>Ci</th>";
    html += "<th>Qi kN</th><th>Fi kN</th><th>役割</th><th>DLOD</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += "<td>" + escapeHtml(r.story) + "</td>";
      html += '<td class="num">' + fmtNum(r.weight_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.wi_above_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.alpha_i, 4) + "</td>";
      html += '<td class="num">' + fmtNum(r.ai, 4) + "</td>";
      html += '<td class="num">' + fmtNum(r.ci, 4) + "</td>";
      html += '<td class="num">' + fmtNum(r.qi_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.fi_kN) + "</td>";
      html += "<td>" + escapeHtml(r.mass_role || "—") + "</td>";
      html += "<td>" + escapeHtml(r.dlod_label || (r.output_dlod ? "出力" : "—")) + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function renderDiaphragmTable(view) {
    const rows = view.diaphragm_rows;
    if (!rows || !rows.length) return "";
    const title = view.dlod_section_title || "ダイアフラム DLOD（TYPE=0 AREA、DLOD出力対象の Fi のみ）";
    let html = '<section class="lv-section"><h2 class="lv-section-title">' + escapeHtml(title) + "</h2>";
    if (view.dlod_section_note) {
      html += '<p class="lv-section-note">' + escapeHtml(view.dlod_section_note) + "</p>";
    }
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>DIAP</th><th>階</th><th>載荷レベル m</th><th>LC</th><th>方向</th><th>面積 m²</th><th>Fi kN</th><th>kN/m²</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += '<td class="num">' + escapeHtml(r.diaphragm_id) + "</td>";
      html += "<td>" + escapeHtml(r.story) + "</td>";
      html += '<td class="num">' + fmtNum(r.load_level_m) + "</td>";
      html += '<td class="num">' + escapeHtml(r.load_case) + "</td>";
      html += "<td>" + escapeHtml(r.axis + r.sign) + "</td>";
      html += '<td class="num">' + fmtNum(r.area_m2) + "</td>";
      html += '<td class="num">' + fmtNum(r.fi_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.pressure_kN_m2, 4) + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function renderQiFiRules(text) {
    if (!text) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">Qi・Fi の算定</h2><ul class="lv-rules">';
    text.split("\n").forEach(function (line) {
      if (line.trim()) html += "<li>" + escapeHtml(line) + "</li>";
    });
    html += "</ul></section>";
    return html;
  }

  function renderWarnings(warnings) {
    if (!warnings || !warnings.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">警告</h2><ul class="lv-warnings">';
    warnings.forEach(function (w) {
      html += "<li>" + escapeHtml(w) + "</li>";
    });
    html += "</ul></section>";
    return html;
  }

  function renderChecks(checks) {
    if (!checks || !checks.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">検算</h2><ul class="lv-checks">';
    checks.forEach(function (c) {
      const mark = c.ok ? "OK" : "NG";
      const cls = c.ok ? "lv-check-ok" : "lv-check-ng";
      html += '<li class="' + cls + '">[' + mark + "] " + escapeHtml(c.label)
        + " — " + escapeHtml(c.detail || "") + "</li>";
    });
    html += "</ul></section>";
    return html;
  }

  function renderEquilibrium(rows) {
    if (!rows || !rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">荷重・反力釣合（解析モデル）</h2>';
    rows.forEach(function (row) {
      html += "<h3 class=\"lv-subtitle\">LC" + escapeHtml(row.load_case) + " "
        + escapeHtml(row.direction) + "</h3>";
      html += "<ul class=\"lv-equilibrium\">";
      html += "<li>ΣFi_DLOD_output = " + fmtNum(row.fi_dlod_output_kN) + " kN</li>";
      html += "<li>ΣFx_applied = " + fmtNum(row.fx_applied_kN) + " kN</li>";
      html += "<li>ΣTx = " + fmtNum(row.sum_reaction_kN) + " kN</li>";
      html += "<li>|ΣFx_applied + ΣTx| = " + fmtNum(row.equilibrium_residual_kN) + " kN</li>";
      html += "</ul>";
      if (row.dlod_loads && row.dlod_loads.length) {
        html += "<p class=\"lv-section-note\">DLOD: ";
        html += row.dlod_loads.map(function (d) {
          return "DIAP" + d.diap_id + " Fx=" + fmtNum(d.fx_kN) + " kN";
        }).join(", ");
        html += "</p>";
      }
      if (row.other_loads && row.other_loads.length) {
        html += "<p class=\"lv-section-note\">その他: "
          + row.other_loads.map(function (r) { return r.kind; }).join(", ")
          + "</p>";
      } else {
        html += "<p class=\"lv-section-note\">PLOD/GLOD/ALOD 等の水平荷重: なし</p>";
      }
    });
    html += "</section>";
    return html;
  }

  function renderSeismic(view) {
    let html = renderSummary(view);
    html += renderNotice(view.report_notice);
    html += renderRawWeightTable(view.raw_weight_rows);
    html += renderMassLevelTable(view);
    html += renderDiaphragmTable(view);
    html += renderQiFiRules(view.qi_fi_rules_text);
    html += renderEquilibrium(view.equilibrium_rows);
    html += renderChecks(view.checks);
    html += renderWarnings(view.warnings);
    if (view.dlod_record_count) {
      html += '<p class="loads-verify-status">DLOD レコード数: ' + view.dlod_record_count + "</p>";
    }
    return html;
  }

  function renderWindSurfaceTable(rows) {
    if (!rows || !rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">受圧面一覧</h2>';
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>ID</th><th>名称</th><th>ケース</th><th>区分</th><th>方向</th>";
    html += "<th>Z下</th><th>Z上</th><th>幅 m</th><th>面積 m²</th><th>Cf</th><th>ΣF kN</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += '<td class="num">' + escapeHtml(r.surface_id) + "</td>";
      html += "<td>" + escapeHtml(r.name) + "</td>";
      html += "<td>" + escapeHtml(r.wind_case) + "</td>";
      html += "<td>" + escapeHtml(r.surface_role) + "</td>";
      html += "<td>" + escapeHtml(r.direction_label || r.face_direction) + "</td>";
      html += '<td class="num">' + fmtNum(r.z_bottom) + "</td>";
      html += '<td class="num">' + fmtNum(r.z_top) + "</td>";
      html += '<td class="num">' + fmtNum(r.width) + "</td>";
      html += '<td class="num">' + fmtNum(r.gross_area_m2) + "</td>";
      html += '<td class="num">' + fmtNum(r.cf, 3) + "</td>";
      html += '<td class="num">' + fmtNum(r.total_force_kN) + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function renderWindStoryForceTable(rows) {
    if (!rows || !rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">階風力合力 F_story</h2>';
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>ケース</th><th>階</th><th>風上 kN</th><th>風下 kN</th><th>F_story kN</th><th>DIAP</th><th>DLOD</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += "<td>" + escapeHtml(r.wind_case) + "</td>";
      html += "<td>" + escapeHtml(r.story) + "</td>";
      html += '<td class="num">' + fmtNum(r.windward_force_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.leeward_force_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.f_story_kN) + "</td>";
      html += '<td class="num">' + escapeHtml(r.target_diaphragm_id != null ? r.target_diaphragm_id : "—") + "</td>";
      html += "<td>" + (r.output_to_dlod ? "出力" : "—") + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function renderWindDiaphragmTable(view) {
    const rows = view.diaphragm_rows;
    if (!rows || !rows.length) return "";
    const title = view.dlod_section_title || "DLOD 等価入力";
    let html = '<section class="lv-section"><h2 class="lv-section-title">' + escapeHtml(title) + "</h2>";
    if (view.uniform_input_note) {
      html += '<p class="lv-section-note">' + escapeHtml(view.uniform_input_note) + "</p>";
    }
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>LC</th><th>DIAP</th><th>階</th><th>方向</th><th>載荷レベル m</th><th>F_story kN</th><th>面積 m²</th><th>kN/m²</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += '<td class="num">' + escapeHtml(r.load_case) + "</td>";
      html += '<td class="num">' + escapeHtml(r.diaphragm_id) + "</td>";
      html += "<td>" + escapeHtml(r.story) + "</td>";
      html += "<td>" + escapeHtml(r.direction) + "</td>";
      html += '<td class="num">' + fmtNum(r.load_level_m) + "</td>";
      html += '<td class="num">' + fmtNum(r.f_story_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.diaphragm_area_m2) + "</td>";
      html += '<td class="num">' + fmtNum(r.area_load_kN_m2, 4) + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function renderWindEquilibrium(rows) {
    if (!rows || !rows.length) return "";
    let html = '<section class="lv-section"><h2 class="lv-section-title">荷重・反力釣合（解析モデル）</h2>';
    html += '<div class="lv-table-wrap"><table class="lv-table"><thead><tr>';
    html += "<th>ケース</th><th>LC</th><th>方向</th><th>ΣF_story</th><th>ΣF_DLOD</th><th>ΣFx</th><th>ΣRx</th><th>残差</th><th>判定</th>";
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      html += "<td>" + escapeHtml(r.wind_case_name) + "</td>";
      html += '<td class="num">' + escapeHtml(r.load_case) + "</td>";
      html += "<td>" + escapeHtml(r.direction) + "</td>";
      html += '<td class="num">' + fmtNum(r.sum_f_wind_generated_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.sum_f_dlod_output_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.fx_applied_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.sum_reaction_kN) + "</td>";
      html += '<td class="num">' + fmtNum(r.equilibrium_residual_kN, 4) + "</td>";
      html += "<td>" + (r.equilibrium_ok ? "OK" : "NG") + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table></div></section>";
    return html;
  }

  function windCaseById(visual, caseId) {
    const cases = (visual && visual.cases) || [];
    if (!cases.length) return null;
    if (caseId == null) return cases[0];
    return cases.find(function (c) { return c.wind_case_id === caseId; }) || cases[0];
  }

  function renderWindVisual(view) {
    const visual = view.visual;
    if (!visual || !visual.bbox || !visual.cases || !visual.cases.length) {
      return '<section class="lv-section"><h2 class="lv-section-title">風荷重の当たり方（平面図）</h2>'
        + '<p class="lv-section-note">モデル節点から平面範囲を取得できないか、風荷重ケースが未定義です。</p></section>';
    }

    const wc = windCaseById(visual, selectedWindCaseId);
    selectedWindCaseId = wc.wind_case_id;
    const bbox = visual.bbox;
    const pad = 48;
    const w = 420;
    const h = 320;
    const spanX = Math.max(bbox.x_max - bbox.x_min, 1e-6);
    const spanY = Math.max(bbox.y_max - bbox.y_min, 1e-6);
    const scale = Math.min((w - 2 * pad) / spanX, (h - 2 * pad) / spanY);
    const ox = pad + (w - 2 * pad - spanX * scale) / 2;
    const oy = pad + (h - 2 * pad - spanY * scale) / 2;

    function tx(x) { return ox + (x - bbox.x_min) * scale; }
    function ty(y) { return h - oy - (y - bbox.y_min) * scale; }

    const x0 = tx(bbox.x_min);
    const x1 = tx(bbox.x_max);
    const y0 = ty(bbox.y_min);
    const y1 = ty(bbox.y_max);

    let svg = '<svg class="lv-wind-svg" viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="風荷重平面図">';
    svg += '<rect x="0" y="0" width="' + w + '" height="' + h + '" class="lv-wind-bg"/>';
    svg += '<rect x="' + x0 + '" y="' + y1 + '" width="' + (x1 - x0) + '" height="' + (y0 - y1)
      + '" class="lv-wind-footprint"/>';

    (wc.surfaces || []).forEach(function (s) {
      const roleCls = s.surface_role === "WINDWARD" ? "lv-wind-wall-windward" : "lv-wind-wall-leeward";
      const thick = 8;
      let lx0, ly0, lx1, ly1;
      if (s.wall_side === "x_max") {
        lx0 = lx1 = x1; ly0 = y1; ly1 = y0;
      } else if (s.wall_side === "x_min") {
        lx0 = lx1 = x0; ly0 = y1; ly1 = y0;
      } else if (s.wall_side === "y_max") {
        ly0 = ly1 = y0; lx0 = x0; lx1 = x1;
      } else {
        ly0 = ly1 = y1; lx0 = x0; lx1 = x1;
      }
      svg += '<line x1="' + lx0 + '" y1="' + ly0 + '" x2="' + lx1 + '" y2="' + ly1
        + '" class="lv-wind-wall ' + roleCls + '" stroke-width="' + thick + '"/>';
    });

    const flow = wc.flow || { ux: 0, uy: 0 };
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const arrowLen = 56;
    let ax = cx - flow.ux * arrowLen * 0.5;
    let ay = cy - flow.uy * arrowLen * 0.5;
    let bx = cx + flow.ux * arrowLen * 0.5;
    let by = cy + flow.uy * arrowLen * 0.5;
    if (Math.abs(flow.ux) > Math.abs(flow.uy)) {
      ax = flow.ux < 0 ? x1 + 18 : x0 - 18;
      bx = flow.ux < 0 ? x0 - 10 : x1 + 10;
      ay = by = cy;
    } else {
      ay = flow.uy < 0 ? y0 + 18 : y1 - 18;
      by = flow.uy < 0 ? y1 - 10 : y0 + 10;
      ax = bx = cx;
    }
    svg += '<defs><marker id="lvWindArrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
      + '<path d="M0,0 L6,3 L0,6 Z" class="lv-wind-arrow-head"/></marker></defs>';
    svg += '<line x1="' + ax + '" y1="' + ay + '" x2="' + bx + '" y2="' + by
      + '" class="lv-wind-flow" marker-end="url(#lvWindArrow)"/>';
    svg += '<text x="' + bx + '" y="' + (by - 8) + '" class="lv-wind-flow-label">'
      + escapeHtml(wc.direction_label) + "</text>";

    const stories = wc.story_forces || [];
    const maxF = wc.max_f_story_kN || 1;
    const innerW = x1 - x0 - 24;
    stories.forEach(function (sf, idx) {
      const rowY = y1 + 18 + idx * 22;
      if (rowY > y0 - 12) return;
      const len = Math.max(4, (Math.abs(sf.f_story_kN) / maxF) * innerW * 0.45);
      const sx = cx;
      const sy = rowY;
      const ex = sx + (flow.ux || 0) * len;
      const ey = sy - (flow.uy || 0) * len;
      svg += '<line x1="' + sx + '" y1="' + sy + '" x2="' + ex + '" y2="' + ey
        + '" class="lv-wind-story-force" marker-end="url(#lvWindArrow)"/>';
      svg += '<text x="' + (x0 + 4) + '" y="' + (rowY + 4) + '" class="lv-wind-story-label">'
        + escapeHtml(sf.story) + " F=" + fmtNum(sf.f_story_kN) + "kN</text>";
    });

    svg += '<text x="' + x0 + '" y="' + (y0 + 14) + '" class="lv-wind-axis">X</text>';
    svg += '<text x="' + (x1 - 8) + '" y="' + (y1 - 6) + '" class="lv-wind-axis">Y</text>';
    svg += "</svg>";

    let html = '<section class="lv-section lv-wind-visual-section"><h2 class="lv-section-title">風荷重の当たり方（平面図）</h2>';
    html += '<p class="lv-section-note">建物平面（節点範囲）上に、選択ケースの受圧面（橙=風上、青=風下）と風向・階別 F_story を表示します。'
      + " DLOD は床面への等価水平荷重です。</p>";
    html += '<div class="lv-wind-controls"><label>表示ケース ';
    html += '<select id="lvWindCaseSelect" class="lv-wind-select">';
    visual.cases.forEach(function (c) {
      html += '<option value="' + c.wind_case_id + '"'
        + (c.wind_case_id === selectedWindCaseId ? " selected" : "") + ">"
        + escapeHtml(c.name + " (" + c.direction_label + ", LC" + c.load_case + ")") + "</option>";
    });
    html += "</select></label>";
    html += '<span class="lv-wind-legend"><span class="lv-legend-windward">■ 風上</span> '
      + '<span class="lv-legend-leeward">■ 風下</span> '
      + '<span class="lv-legend-flow">→ 風向 / 階 F_story</span></span></div>';
    html += '<div class="lv-wind-diagram-wrap">' + svg + "</div>";
    html += "</section>";
    return html;
  }

  function bindWindCaseSelect() {
    const sel = document.getElementById("lvWindCaseSelect");
    if (!sel) return;
    sel.addEventListener("change", function () {
      selectedWindCaseId = Number(sel.value);
      if (currentView && currentView.kind === "wind") {
        el.main.innerHTML = renderWind(currentView);
        bindWindCaseSelect();
      }
    });
  }

  function renderWind(view) {
    let html = renderWindVisual(view);
    html += renderSummary(view);
    if (view.uniform_input_note) {
      html += '<section class="lv-section"><h2 class="lv-section-title">入力方式</h2>'
        + '<p class="lv-section-note">' + escapeHtml(view.uniform_input_note) + "</p></section>";
    }
    html += renderNotice(view.report_notice);
    html += renderWindSurfaceTable(view.surface_rows);
    html += renderWindStoryForceTable(view.story_force_rows);
    html += renderWindDiaphragmTable(view);
    html += renderWindEquilibrium(view.equilibrium_rows);
    html += renderChecks(view.checks);
    html += renderWarnings(view.warnings);
    if (view.dlod_record_count) {
      html += '<p class="loads-verify-status">DLOD レコード数: ' + view.dlod_record_count + "</p>";
    }
    return html;
  }

  function renderView(view) {
    currentView = view;
    activeTab = view.active_tab || activeTab;
    el.title.textContent = view.title || "荷重・外力確認";
    const pathLine = view.dat_path || modelPath;
    const proj = view.project_path ? " · " + view.project_path : "";
    el.path.textContent = pathLine + proj;
    renderTabs(view);

    if (view.kind === "seismic") {
      el.main.innerHTML = renderSeismic(view);
    } else if (view.kind === "wind") {
      el.main.innerHTML = renderWind(view);
      bindWindCaseSelect();
    } else {
      el.main.innerHTML = '<div class="lv-placeholder">この荷重種別は未対応です。</div>';
    }

    el.btnApply.disabled = !view.can_apply_dlod;
    setStatus(view.applied ? "DLOD を .dat に反映しました。" : "");
  }

  async function loadView() {
    if (!modelPath) {
      el.main.innerHTML = '<div class="lv-placeholder">モデルパスが指定されていません。メイン画面から開き直してください。</div>';
      return;
    }
    setStatus("読み込み中…");
    el.btnApply.disabled = true;
    try {
      const view = await fetchJson(
        apiPathForTab(activeTab) + "?path=" + encodeURIComponent(modelPath)
      );
      view.active_tab = activeTab;
      renderView(view);
    } catch (ex) {
      el.main.innerHTML = "";
      setStatus("エラー: " + ex.message);
    }
  }

  async function applyDlod() {
    if (!modelPath || !currentView || !currentView.can_apply_dlod) return;
    const tab = currentView.kind || activeTab;
    const msg = tab === "wind"
      ? "風荷重 DLOD ブロックを .dat に書き込みます。よろしいですか？"
      : "地震 DLOD ブロックを .dat に書き込みます。よろしいですか？";
    if (!window.confirm(msg)) return;
    setStatus("DLOD 反映中…");
    el.btnApply.disabled = true;
    try {
      const body = await fetchJson(
        applyPathForTab(tab) + "?path=" + encodeURIComponent(modelPath),
        { method: "POST" }
      );
      renderView(body.view);
      try {
        if (window.opener && !window.opener.closed && typeof window.opener.reloadCurrentModel === "function") {
          window.opener.reloadCurrentModel();
        }
      } catch (_) {
        /* ignore */
      }
    } catch (ex) {
      setStatus("反映エラー: " + ex.message);
      el.btnApply.disabled = false;
    }
  }

  function openProject() {
    try {
      if (window.opener && !window.opener.closed && typeof window.opener.openProjectWindow === "function") {
        window.opener.openProjectWindow();
        return;
      }
    } catch (_) {
      /* ignore */
    }
    window.alert("メイン画面から Project… を開いてください。");
  }

  el.btnRefresh.addEventListener("click", loadView);
  el.btnApply.addEventListener("click", applyDlod);
  el.btnProject.addEventListener("click", openProject);

  if (window.opener) {
    try {
      const origin = window.opener.__stbGuiOrigin;
      if (origin) window.__stbGuiOrigin = origin;
    } catch (_) {
      /* ignore */
    }
  }

  loadView();
})();
