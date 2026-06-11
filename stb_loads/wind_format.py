"""Markdown report for wind load generation."""

from __future__ import annotations

from stb_loads.wind import WIND_NOTICE, WindDistributionResult
from stb_loads.wind_equilibrium import compute_wind_equilibrium

UNIFORM_INPUT_NOTE = (
    "MVP では DIAPHRAGM_UNIFORM として、階風力合力 F_story を "
    "DLOD_area_load = F_story / diaphragm_area [kN/m²] の水平面荷重として等価入力します。"
    "これは床面への風圧ではなく、外壁風荷重の全体解析用等価入力です。"
)


def _fmt(value, places=3):
    if value is None:
        return "—"
    n = float(value)
    if abs(n - round(n)) < 1.0e-9:
        return str(int(round(n)))
    return ("{0:." + str(places) + "f}").format(n)


def _md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def render_wind_markdown(result: WindDistributionResult, project=None, mdl=None) -> str:
    parts = ["# 風荷重算定レポート", "", UNIFORM_INPUT_NOTE, ""]

    if not result.cases:
        parts.append("_風荷重ケースが定義されていません。_")
        return "\n".join(parts)

    parts.append("## 1. 算定条件")
    for c in result.cases:
        parts.append("")
        parts.append("### " + c.name)
        cond_rows = [
            ["V0", _fmt(c.v0, 1), "m/s"],
            ["地表面粗度区分", c.roughness_category, ""],
            ["Zb", _fmt(c.zb, 1), "m"],
            ["ZG", _fmt(c.zg, 1), "m"],
            ["α", _fmt(c.alpha, 3), ""],
            ["H", _fmt(c.building_height_H, 3), "m"],
            ["Er", _fmt(c.er, 4), ""],
            ["Gf", _fmt(c.gf, 3), "自動" if c.gf_is_auto else "直接入力"],
            ["E (= Er²×Gf)", _fmt(c.e_factor, 4), ""],
            ["q", _fmt(c.q_N_m2, 1), "N/m²"],
            ["Cf (default)", _fmt(c.cf_default, 3), ""],
            ["w (default)", _fmt(c.w_default_N_m2, 1), "N/m²"],
            ["pressure_mode", c.pressure_mode, ""],
            ["diaphragm_input_mode", c.diaphragm_input_mode, ""],
            ["load_case", str(c.load_case), ""],
        ]
        parts.append(_md_table(["項目", "値", "単位"], cond_rows))

    parts.extend(["", "## 2. 受圧面一覧（風上・風下）"])
    if result.surfaces:
        surf_rows = []
        for s in result.surfaces:
            surf_rows.append([
                s.surface_id,
                s.name,
                s.surface_role,
                s.face_direction,
                _fmt(s.z_bottom, 3),
                _fmt(s.z_top, 3),
                _fmt(s.width, 3),
                _fmt(s.gross_area_m2, 3),
                _fmt(s.cf, 3),
            ])
        parts.append(_md_table(
            ["ID", "名称", "区分", "方向", "Z下", "Z上", "幅", "面積", "Cf"],
            surf_rows,
        ))
    else:
        parts.append("_受圧面なし_")

    parts.extend(["", "## 3. 受圧面別・階別風力（算定）"])
    if result.surface_contributions:
        comp_rows = []
        for sc in result.surface_contributions:
            comp_rows.append([
                sc.story,
                sc.surface_name,
                sc.surface_role,
                _fmt(sc.tributary_area_m2, 3),
                _fmt(sc.cf, 3),
                _fmt(sc.pressure_w_N_m2, 1),
                _fmt(sc.force_kN, 3),
            ])
        parts.append(_md_table(
            ["階", "受圧面", "区分", "受圧面積", "Cf", "w", "F"],
            comp_rows,
        ))
    else:
        parts.append("_受圧面別風力なし_")

    parts.extend(["", "## 4. 階風力合力 F_story"])
    if result.story_forces:
        sf_rows = []
        for sf in result.story_forces:
            sf_rows.append([
                sf.story,
                _fmt(sf.z_bottom, 3),
                _fmt(sf.z_top, 3),
                _fmt(sf.windward_force_kN, 3),
                _fmt(sf.leeward_force_kN, 3),
                _fmt(sf.f_story_kN, 3),
                sf.target_diaphragm_id if sf.target_diaphragm_id is not None else "—",
                "Yes" if sf.output_to_dlod else "No",
            ])
        parts.append(_md_table(
            ["階", "Z下", "Z上", "風上F", "風下F", "F_story", "DIAP", "DLOD"],
            sf_rows,
        ))
    else:
        parts.append("_階風力なし_")

    parts.extend(["", "## 5. DLOD等価入力（DIAPHRAGM_UNIFORM）"])
    if result.diaphragm_loads:
        dl_rows = []
        for dl in result.diaphragm_loads:
            dl_rows.append([
                dl.load_case,
                dl.diaphragm_id,
                dl.story,
                dl.input_mode,
                _fmt(dl.f_story_kN, 3),
                _fmt(dl.diaphragm_area_m2, 3),
                _fmt(dl.area_load_kN_m2, 4),
                _fmt(dl.eccentricity_e_m, 3) if dl.eccentricity_e_m is not None else "—",
                _fmt(dl.mz_knm, 3) if dl.mz_knm is not None else "—",
            ])
        parts.append(_md_table(
            ["LC", "DIAP", "階", "入力方式", "F_story", "DIAP面積", "kN/m²", "e", "Mz"],
            dl_rows,
        ))
    else:
        parts.append("_DLOD出力なし_")

    parts.extend(["", "## 6. 釣合チェック"])
    if mdl is not None:
        eq_rows = compute_wind_equilibrium(mdl, result)
        if eq_rows:
            check_rows = []
            for row in eq_rows:
                check_rows.append([
                    row["wind_case_name"],
                    _fmt(row["sum_f_wind_generated_kN"], 3),
                    _fmt(row["sum_f_dlod_output_kN"], 3),
                    _fmt(row["fx_applied_kN"], 3),
                    _fmt(row["sum_reaction_kN"], 3),
                    _fmt(row["equilibrium_residual_kN"], 4),
                    "OK" if row["equilibrium_ok"] else "NG",
                ])
            parts.append(_md_table(
                ["ケース", "ΣF_story", "ΣF_DLOD", "ΣFx_applied", "ΣRx", "残差", "判定"],
                check_rows,
            ))
        else:
            parts.append("_釣合対象なし_")
    else:
        parts.append("_モデル未指定のため解析釣合は省略_")

    if result.warnings:
        parts.extend(["", "## 警告"])
        for w in result.warnings:
            parts.append("- " + w)

    parts.extend(["", "## 7. 注意", "", "> " + WIND_NOTICE, ""])
    return "\n".join(parts)
