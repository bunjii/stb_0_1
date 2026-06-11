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
    (view.tabs || []).forEach(function (tab) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lv-tab" + (tab.id === view.active_tab ? " active" : "");
      if (!tab.enabled) btn.classList.add("lv-tab-disabled");
      btn.textContent = tab.label;
      btn.disabled = !tab.enabled;
      if (tab.enabled && tab.id === view.active_tab) {
        btn.setAttribute("aria-current", "page");
      }
      if (!tab.enabled) {
        btn.title = "今後対応予定";
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

  function renderView(view) {
    currentView = view;
    el.title.textContent = view.title || "荷重・外力確認";
    const pathLine = view.dat_path || modelPath;
    const proj = view.project_path ? " · " + view.project_path : "";
    el.path.textContent = pathLine + proj;
    renderTabs(view);

    if (view.kind === "seismic") {
      el.main.innerHTML = renderSeismic(view);
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
        "/api/loads/seismic?path=" + encodeURIComponent(modelPath)
      );
      renderView(view);
    } catch (ex) {
      el.main.innerHTML = "";
      setStatus("エラー: " + ex.message);
    }
  }

  async function applyDlod() {
    if (!modelPath || !currentView || !currentView.can_apply_dlod) return;
    if (!window.confirm("地震 DLOD ブロックを .dat に書き込みます。よろしいですか？")) return;
    setStatus("DLOD 反映中…");
    el.btnApply.disabled = true;
    try {
      const body = await fetchJson(
        "/api/loads/seismic/apply?path=" + encodeURIComponent(modelPath),
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
