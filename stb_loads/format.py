from stb_loads.equilibrium import build_equilibrium_check_rows, compute_seismic_equilibrium
from stb_loads.seismic import SeismicDistributionResult

import common


def stories_for_display(stories):
    """Result tables: upper floor first (calculation order is bottom-first)."""
    return tuple(sorted(stories, key=lambda s: s.mass_height_m, reverse=True))


def weight_stories_for_display(stories):
    return tuple(sorted(stories, key=lambda s: s.mass_height, reverse=True))


def _fmt_num(value, places=3):
    if value is None:
        return "—"
    n = float(value)
    if abs(n - round(n)) < 1.0e-9:
        return str(int(round(n)))
    return ("{0:." + str(places) + "f}").format(n)


def dlod_display_label(story_summary) -> str:
    if story_summary.mass_role == "BASE_MASS" or (
        story_summary.is_base_level and not story_summary.output_dlod
    ):
        return "非出力（総重量のみ）"
    if story_summary.output_dlod:
        return "出力"
    return "非出力"


def _story_elevations(result: SeismicDistributionResult):
    return {sw.story_name: sw.elevation for sw in result.weight_result.stories}


def _diap_table_fi_total_kN(result: SeismicDistributionResult) -> float:
    if not result.diaphragm_loads:
        return 0.0
    n_dir = max(1, result.num_seismic_directions)
    return sum(d.fi_kN for d in result.diaphragm_loads) / float(n_dir)


ALPHA_I_NOTE = (
    "alpha_i は、その階が支える重量を地上部分の総地震時重量で割った値です。"
    "DLOD の載荷高さではありません。"
)

WI_ABOVE_NOTE = (
    "当該階以上ΣWi は、Ai分布における alpha_i の分子です。"
    "alpha_i = 当該階以上ΣWi / ΣWi_total として計算します。"
)

REPORT_NOTICE = (
    "この表の Wi は各階の重量集計です。"
    "alpha_i は、その階が支える重量を総地震時重量で割った値です。"
    "DLOD の載荷位置は「質量高」ではなく、対応するダイアフラムのレベルです。"
    "BASE_MASS は総地震重量には含めますが、DLOD には出力しません。"
)

QI_FI_RULES_TEXT = (
    "Qi は層せん断力です。\n"
    "Fi は DLOD 用の階地震力です。\n"
    "Fi = Qi − Q(i+1)\n"
    "最上階では Fi = Qi とする。\n"
    "DLOD には Qi ではなく Fi を出力する。"
)

DLOD_SECTION_NOTE = (
    "この表には、DIAPHRAGM_MASS の Fi のみを出力する。"
    "BASE_MASS の Fi は DLOD に出力しない。"
)


def build_seismic_summary_rows(result: SeismicDistributionResult):
    lcs = ", ".join(str(lc) for lc in result.weight_result.weight_load_cases) or "0"
    rows = [
        {"label": "C0 (標準せん断力係数)", "value": _fmt_num(result.c0, 4)},
        {
            "label": "Z (地震地域係数)",
            "value": _fmt_num(result.z, 4),
            "note": "Z 未指定のため 1.0000 として扱う" if result.z_is_default else "",
        },
        {"label": "Rt (振動特性係数)", "value": _fmt_num(result.rt, 4)},
        {"label": "T (設計用1次固有周期)", "value": _fmt_num(result.design_period_s, 4), "unit": "sec"},
        {"label": "Tc (地盤係数)", "value": _fmt_num(result.tc, 4)},
        {"label": "base_level", "value": result.base_level},
        {"label": "base_mass_policy", "value": result.report_base_mass_policy},
        {"label": "Wi 集計 LC", "value": lcs},
        {
            "label": "ΣWi_total（総地震時重量、BASE_MASS含む）",
            "value": _fmt_num(result.total_weight_kN),
            "unit": "kN",
        },
        {
            "label": "Q1（基底せん断力）",
            "value": _fmt_num(result.q1_kN),
            "unit": "kN",
        },
        {
            "label": "ΣFi_all_mass_levels",
            "value": _fmt_num(result.fi_all_mass_levels_kN),
            "unit": "kN",
            "note": "BASE_MASS を含む全質量レベルの階地震力合計。Q1 と一致する。",
        },
        {
            "label": "ΣFi_DLOD_output",
            "value": _fmt_num(result.fi_dlod_output_kN),
            "unit": "kN",
            "note": "DLOD に実際に出力したダイアフラム水平力の合計。BASE_MASS は含めない。",
        },
    ]
    return rows


def build_raw_weight_rows(result: SeismicDistributionResult, project=None):
    roles_by_story = {}
    if project is not None:
        for entry in project.load_conditions.seismic_masses:
            if entry.story:
                roles_by_story[entry.story] = entry.mass_role
    rows = []
    for sw in weight_stories_for_display(result.weight_result.stories):
        row = {
            "story": sw.story_name,
            "story_level_m": sw.elevation,
            "height_m": sw.height,
            "weight_kN": sw.weight_kN,
        }
        role = roles_by_story.get(sw.story_name)
        if role:
            row["mass_role"] = role
        rows.append(row)
    return rows


def build_seismic_story_rows(result: SeismicDistributionResult):
    rows = []
    for s in stories_for_display(result.stories):
        rows.append({
            "story": s.story_name,
            "weight_kN": s.weight_kN,
            "wi_above_kN": s.w_supported_above_kN,
            "alpha_i": s.beta,
            "ai": s.ai,
            "ci": s.ci_story,
            "qi_kN": s.qi_kN,
            "fi_kN": s.fi_kN,
            "mass_role": s.mass_role or "",
            "output_dlod": s.output_dlod,
            "dlod_label": dlod_display_label(s),
        })
    return rows


def _bottom_story_summary(result: SeismicDistributionResult):
    if not result.stories:
        return None
    return min(result.stories, key=lambda s: s.mass_height_m)


def _check_vertical_weight_reactions(mdl, result: SeismicDistributionResult):
    import copy

    from stb_engine import solve_model

    mdl_solved = copy.deepcopy(mdl)
    solve_model(mdl_solved)
    total_tz = 0.0
    lc_parts = []
    tol = max(1.0, result.total_weight_kN * 0.05)
    for lc in result.weight_result.weight_load_cases:
        try:
            col = mdl_solved.lcs.index(lc)
        except ValueError:
            continue
        lc_tz = 0.0
        for c in mdl_solved.cons:
            reacts = getattr(c.nd, "reacts", None)
            if reacts is None:
                continue
            lc_tz += float(reacts[col, 2]) * 1e-3
        total_tz += lc_tz
        lc_parts.append("LC{0} ΣTz={1} kN".format(lc, _fmt_num(lc_tz)))
    ok = abs(abs(total_tz) - result.total_weight_kN) <= tol
    detail = "ΣWi_total={0} kN, 反力 {1}".format(
        _fmt_num(result.total_weight_kN),
        ", ".join(lc_parts) if lc_parts else "—",
    )
    return ok, detail


def build_seismic_diaphragm_rows(result: SeismicDistributionResult):
    elevation_by_story = _story_elevations(result)
    rows = []
    for d in sorted(
        result.diaphragm_loads,
        key=lambda item: elevation_by_story.get(item.story_name, 0.0),
        reverse=True,
    ):
        rows.append({
            "diaphragm_id": d.diaphragm_id,
            "story": d.story_name,
            "load_level_m": elevation_by_story.get(d.story_name, 0.0),
            "load_case": d.load_case,
            "axis": d.axis.upper(),
            "sign": "+" if d.sign >= 0 else "-",
            "area_m2": d.area_m2,
            "fi_kN": d.fi_kN,
            "pressure_kN_m2": d.pressure_kN_m2,
        })
    return rows


def build_seismic_report_checks(result: SeismicDistributionResult, report: dict, mdl=None):
    tol = max(1.0e-3, result.q1_kN * 1.0e-6)
    tol_w = max(0.01, result.total_weight_kN * 1.0e-4)
    mass_rows = report.get("mass_level_rows") or []
    diap_rows = report.get("diaphragm_rows") or []
    diap_fi = _diap_table_fi_total_kN(result)
    base_mass_stories = {
        s.story_name for s in result.stories if s.mass_role == "BASE_MASS"
    }
    base_mass_in_dlod = any(d.story_name in base_mass_stories for d in result.diaphragm_loads)

    forbidden_story_keys = {"c0", "z", "rt", "mass_height_m"}
    story_keys_ok = all(not forbidden_story_keys.intersection(r.keys()) for r in mass_rows)
    has_ci = all("ci" in r for r in mass_rows) if mass_rows else True
    raw_rows = report.get("raw_weight_rows") or []
    no_mass_height_label = "質量高 m" not in report.get("_header_text", "")

    elevation_by_story = _story_elevations(result)
    diap_level_ok = True
    for row in diap_rows:
        expected = elevation_by_story.get(row.get("story", ""), 0.0)
        if abs(float(row.get("load_level_m", 0.0)) - expected) > 1.0e-3:
            diap_level_ok = False
            break

    bottom = _bottom_story_summary(result)
    bottom_wi_above_ok = True
    bottom_detail = "—"
    if bottom is not None:
        bottom_wi_above_ok = abs(bottom.w_supported_above_kN - result.total_weight_kN) <= tol_w
        bottom_detail = "最下階={0} kN, ΣWi_total={1} kN".format(
            _fmt_num(bottom.w_supported_above_kN), _fmt_num(result.total_weight_kN)
        )

    alpha_ratio_ok = True
    alpha_ratio_detail = "—"
    if result.total_weight_kN > common.PRES_ZERO:
        alpha_parts = []
        for s in result.stories:
            expected = s.w_supported_above_kN / result.total_weight_kN
            ok = abs(s.beta - expected) <= max(1.0e-4, tol_w / result.total_weight_kN)
            alpha_ratio_ok = alpha_ratio_ok and ok
            alpha_parts.append(
                "{0}: {1}/{2}={3}".format(
                    s.story_name,
                    _fmt_num(s.w_supported_above_kN),
                    _fmt_num(result.total_weight_kN),
                    _fmt_num(expected, 4),
                )
            )
        alpha_ratio_detail = "; ".join(alpha_parts)

    vertical_reaction_ok = True
    vertical_reaction_detail = "解析モデル未指定"
    if mdl is not None and result.weight_result.weight_load_cases:
        vertical_reaction_ok, vertical_reaction_detail = _check_vertical_weight_reactions(
            mdl, result
        )

    return [
        {
            "label": "各階表に C0 列がないこと",
            "ok": story_keys_ok and not any("c0" in r for r in mass_rows),
            "detail": "質量レベル表の列構成 OK" if story_keys_ok else "不要列が残っています",
        },
        {
            "label": "各階表に Z 列、Rt 列がないこと",
            "ok": not any(("z" in r or "rt" in r) for r in mass_rows),
            "detail": "Z/Rt は上部条件のみ",
        },
        {
            "label": "各階表に Ci 列があること",
            "ok": has_ci,
            "detail": "Ci 列あり" if has_ci else "Ci 列なし",
        },
        {
            "label": "「質量高 m」という列名が通常レポートに出ていないこと",
            "ok": no_mass_height_label and not any("mass_height_m" in r for r in mass_rows + raw_rows),
            "detail": "質量高 m 列なし",
        },
        {
            "label": "DLOD表に載荷レベルがある場合、DIAPのレベルと一致すること",
            "ok": diap_level_ok if diap_rows else True,
            "detail": "載荷レベル = 階レベル m",
        },
        {
            "label": "Q1 と ΣFi_all_mass_levels が一致すること",
            "ok": abs(result.q1_kN - result.fi_all_mass_levels_kN) <= tol,
            "detail": "Q1={0} kN, ΣFi_all={1} kN".format(
                _fmt_num(result.q1_kN), _fmt_num(result.fi_all_mass_levels_kN)
            ),
        },
        {
            "label": "ΣFi_DLOD_output が DLOD表の Fi 合計と一致すること",
            "ok": abs(result.fi_dlod_output_kN - diap_fi) <= tol,
            "detail": "ΣFi_DLOD={0} kN, DLOD表={1} kN".format(
                _fmt_num(result.fi_dlod_output_kN), _fmt_num(diap_fi)
            ),
        },
        {
            "label": "BASE_MASS の Fi が DLOD に出力されていないこと",
            "ok": not base_mass_in_dlod,
            "detail": "BASE_MASS 階の DLOD 行なし" if not base_mass_in_dlod else "BASE_MASS が DLOD に含まれています",
        },
        {
            "label": "最下階の当該階以上ΣWi が ΣWi_total と一致すること",
            "ok": bottom_wi_above_ok,
            "detail": bottom_detail,
        },
        {
            "label": "各階の alpha_i が当該階以上ΣWi / ΣWi_total と一致すること",
            "ok": alpha_ratio_ok,
            "detail": alpha_ratio_detail,
        },
        {
            "label": "ΣWi_total が鉛直荷重反力合計と概ね一致すること",
            "ok": vertical_reaction_ok,
            "detail": vertical_reaction_detail,
        },
    ]


def build_seismic_report_view(result: SeismicDistributionResult, project=None, mdl=None):
    raw_weight_rows = build_raw_weight_rows(result, project)
    mass_level_rows = build_seismic_story_rows(result)
    diaphragm_rows = build_seismic_diaphragm_rows(result)
    report = {
        "summary": build_seismic_summary_rows(result),
        "raw_weight_rows": raw_weight_rows,
        "mass_level_rows": mass_level_rows,
        "diaphragm_rows": diaphragm_rows,
        "alpha_i_note": ALPHA_I_NOTE,
        "wi_above_note": WI_ABOVE_NOTE,
        "report_notice": REPORT_NOTICE,
        "dlod_section_title": "ダイアフラム DLOD（TYPE=0 AREA、DLOD出力対象の Fi のみ）",
        "dlod_section_note": DLOD_SECTION_NOTE,
        "qi_fi_rules_text": QI_FI_RULES_TEXT,
        "_header_text": (
            "階 | Wi kN | 当該階以上ΣWi kN | alpha_i | Ai | Ci | Qi kN | Fi kN | 役割 | DLOD\n"
            "階 | 階レベル m | 階高 m | Wi kN"
        ),
    }
    report["checks"] = build_seismic_report_checks(result, report, mdl=mdl)
    if mdl is not None:
        report["equilibrium_rows"] = compute_seismic_equilibrium(mdl, result)
        report["checks"] = report["checks"] + build_equilibrium_check_rows(mdl, result)
    return report


def render_seismic_markdown(result: SeismicDistributionResult, project=None, mdl=None) -> str:
    report = build_seismic_report_view(result, project, mdl=mdl)
    lines = []
    lines.append("## 地震力 Ai 分布")
    lines.append("")
    lines.append("### 算定条件・合計")
    lines.append("")
    lines.append("| 項目 | 値 |")
    lines.append("| --- | --- |")
    for row in report["summary"]:
        unit = (" " + row["unit"]) if row.get("unit") else ""
        note = row.get("note")
        value = row["value"] + unit
        if note:
            value += "（" + note + "）"
        lines.append("| {0} | {1} |".format(row["label"], value))
    lines.append("")

    lines.append("### 注意")
    lines.append("")
    lines.append(report["report_notice"])
    lines.append("")

    if report["raw_weight_rows"]:
        lines.append("### 階別重量集計 (Wi)")
        lines.append("")
        has_role = any(r.get("mass_role") for r in report["raw_weight_rows"])
        if has_role:
            lines.append("| 階 | 階レベル m | 階高 m | Wi kN | 質量役割 |")
            lines.append("| --- | ---: | ---: | ---: | --- |")
            for r in report["raw_weight_rows"]:
                lines.append(
                    "| {0} | {1} | {2} | {3} | {4} |".format(
                        r["story"],
                        _fmt_num(r["story_level_m"]),
                        _fmt_num(r["height_m"]),
                        _fmt_num(r["weight_kN"]),
                        r.get("mass_role") or "—",
                    )
                )
        else:
            lines.append("| 階 | 階レベル m | 階高 m | Wi kN |")
            lines.append("| --- | ---: | ---: | ---: |")
            for r in report["raw_weight_rows"]:
                lines.append(
                    "| {0} | {1} | {2} | {3} |".format(
                        r["story"],
                        _fmt_num(r["story_level_m"]),
                        _fmt_num(r["height_m"]),
                        _fmt_num(r["weight_kN"]),
                    )
                )
        lines.append("")

    lines.append("### 質量レベル・Ai 分布 (非モーダル)")
    lines.append("")
    lines.append(report["alpha_i_note"])
    lines.append("")
    lines.append(report.get("wi_above_note") or WI_ABOVE_NOTE)
    lines.append("")
    lines.append("| 階 | Wi kN | 当該階以上ΣWi kN | alpha_i | Ai | Ci | Qi kN | Fi kN | 役割 | DLOD |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for r in report["mass_level_rows"]:
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} |".format(
                r["story"],
                _fmt_num(r["weight_kN"]),
                _fmt_num(r["wi_above_kN"]),
                _fmt_num(r["alpha_i"], 4),
                _fmt_num(r["ai"], 4),
                _fmt_num(r["ci"], 4),
                _fmt_num(r["qi_kN"]),
                _fmt_num(r["fi_kN"]),
                r["mass_role"] or "—",
                r["dlod_label"],
            )
        )
    lines.append("")

    if report["diaphragm_rows"]:
        lines.append("### " + report["dlod_section_title"])
        lines.append("")
        lines.append(report["dlod_section_note"])
        lines.append("")
        lines.append("| DIAP | 階 | 載荷レベル m | LC | 方向 | 面積 m2 | Fi kN | kN/m2 |")
        lines.append("| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |")
        for d in report["diaphragm_rows"]:
            lines.append(
                "| {0} | {1} | {2} | {3} | {4}{5} | {6} | {7} | {8} |".format(
                    d["diaphragm_id"],
                    d["story"],
                    _fmt_num(d["load_level_m"]),
                    d["load_case"],
                    d["axis"],
                    d["sign"],
                    _fmt_num(d["area_m2"]),
                    _fmt_num(d["fi_kN"]),
                    _fmt_num(d["pressure_kN_m2"], 4),
                )
            )
        lines.append("")

    lines.append("### Qi・Fi の算定")
    lines.append("")
    for line in report["qi_fi_rules_text"].splitlines():
        lines.append("- " + line)
    lines.append("")

    if report.get("equilibrium_rows"):
        lines.append("### 荷重・反力釣合（解析モデル）")
        lines.append("")
        for row in report["equilibrium_rows"]:
            lines.append(
                "**LC{0} {1}**".format(row["load_case"], row["direction"])
            )
            lines.append("")
            lines.append(
                "- DLOD出力荷重合計 ΣFi_DLOD_output = {0} kN".format(
                    _fmt_num(row["fi_dlod_output_kN"])
                )
            )
            lines.append(
                "- 解析モデルに実際に載った水平荷重合計 ΣFx_applied = {0} kN".format(
                    _fmt_num(row["fx_applied_kN"])
                )
            )
            lines.append(
                "- 支点反力合計 ΣTx = {0} kN".format(_fmt_num(row["sum_reaction_kN"]))
            )
            lines.append(
                "- 釣合チェック |ΣFx_applied + ΣTx| = {0} kN".format(
                    _fmt_num(row["equilibrium_residual_kN"])
                )
            )
            if row["dlod_loads"]:
                lines.append("")
                lines.append("  DLOD 内訳:")
                for d in row["dlod_loads"]:
                    lines.append(
                        "  - DIAP{0}: px={1} kN/m², area={2} m² → Fx={3} kN".format(
                            d["diap_id"],
                            _fmt_num(d["px_kN_m2"], 4),
                            _fmt_num(d["area_m2"]),
                            _fmt_num(d["fx_kN"]),
                        )
                    )
            if row["other_loads"]:
                lines.append("  その他水平荷重: " + ", ".join(r["kind"] for r in row["other_loads"]))
            else:
                lines.append("  その他水平荷重 (PLOD/GLOD/ALOD 等): なし")
            lines.append("")

    lines.append("### 検算")
    lines.append("")
    for check in report["checks"]:
        mark = "OK" if check["ok"] else "NG"
        lines.append("- [{0}] {1} — {2}".format(mark, check["label"], check["detail"]))
    lines.append("")

    if result.warnings:
        lines.append("### 警告")
        lines.append("")
        for w in result.warnings:
            lines.append("- " + w)
        lines.append("")

    return "\n".join(lines)
