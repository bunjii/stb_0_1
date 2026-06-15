"""Markdown report for wind load generation."""

from __future__ import annotations

from stb_loads.equilibrium import prepare_solved_model
from stb_loads.wind import WIND_NOTICE, WindDistributionResult
from stb_loads.wind_equilibrium import compute_wind_equilibrium
from stb_project.schema import (
    format_applied_load_direction_label,
    format_wind_case_short_name,
    format_wind_face_label_jp,
    format_wind_flow_label,
    resolve_wind_direction_convention,
    wind_face_to_wall_side,
)

UNIFORM_INPUT_NOTE = (
    "DIAPHRAGM_DIRECT / DIAPHRAGM_UNIFORM では、外壁面風圧を各ダイアフラムの支配高さ "
    "（隣接ダイアフラムとの中間高さで区切る）に集約し、"
    "F_story を DLOD_area_load = F_story / diaphragm_area [kN/m²] として等価入力します。"
    "基礎側に割り当てた F_wind_to_base は DLOD には出力しません。"
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
        conv = resolve_wind_direction_convention(c.direction)
        parts.append("")
        parts.append("- 荷重ケース：" + format_wind_case_short_name(c.direction))
        parts.append("- 荷重作用方向：" + format_applied_load_direction_label(c.direction))
        parts.append("- 風の流れ：" + format_wind_flow_label(c.direction))
        parts.append("- 風上面：" + format_wind_face_label_jp(conv.windward_face))
        parts.append("- 風下面：" + format_wind_face_label_jp(conv.leeward_face))
        parts.append("")
        cond_rows = [
            ["applied_load_direction", conv.applied_load_direction, ""],
            ["wind_flow_from", conv.wind_flow_from, ""],
            ["wind_flow_to", conv.wind_flow_to, ""],
            ["windward_face", conv.windward_face, ""],
            ["leeward_face", conv.leeward_face, ""],
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
                format_wind_face_label_jp(s.face_direction),
                _fmt(s.z_bottom, 3),
                _fmt(s.z_top, 3),
                _fmt(s.width, 3),
                _fmt(s.gross_area_m2, 3),
                _fmt(s.cf, 3),
            ])
        parts.append(_md_table(
            ["ID", "名称", "区分", "面", "面（説明）", "Z下", "Z上", "幅", "面積", "Cf"],
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

    parts.extend(["", "## 4. ダイアフラム支配高さ別 風力集約"])
    if result.diaphragm_tributary_rows:
        trib_rows = []
        for row in result.diaphragm_tributary_rows:
            trib_rows.append([
                row.diaphragm_id,
                _fmt(row.diaphragm_level_m, 3),
                _fmt(row.lower_adjacent_level_m, 3) if row.lower_adjacent_level_m is not None else "—",
                _fmt(row.upper_adjacent_level_m, 3) if row.upper_adjacent_level_m is not None else "—",
                _fmt(row.tributary_z_bottom, 3),
                _fmt(row.tributary_z_top, 3),
                _fmt(row.tributary_height, 3),
                _fmt(row.exposed_width, 3),
                _fmt(row.tributary_area_m2, 3),
                _fmt(row.wind_pressure_w_N_m2, 1),
                _fmt(row.story_wind_force_kN, 3),
                "Yes" if row.output_to_dlod else "No",
            ])
        parts.append(_md_table(
            [
                "DIAP", "level", "lower", "upper", "z_bot", "z_top", "h_trib",
                "width", "A_trib", "w", "F_story", "DLOD",
            ],
            trib_rows,
        ))
    else:
        parts.append("_ダイアフラム支配高さ集約なし_")

    if result.base_wind_forces:
        parts.extend(["", "### 基礎側風力 F_wind_to_base"])
        base_rows = []
        for row in result.base_wind_forces:
            base_rows.append([
                row.wind_case_id,
                _fmt(row.z_bottom, 3),
                _fmt(row.z_top, 3),
                _fmt(row.tributary_height, 3),
                _fmt(row.tributary_area_m2, 3),
                _fmt(row.wind_pressure_w_N_m2, 1),
                _fmt(row.f_wind_to_base_kN, 3),
            ])
        parts.append(_md_table(
            ["case", "z_bot", "z_top", "h", "A_trib", "w", "F_to_base"],
            base_rows,
        ))

    parts.extend(["", "## 5. 階風力合力 F_story（ダイアフラム集約）"])
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

    parts.extend(["", "## 6. DLOD等価入力"])
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

    parts.extend(["", "## 7. 釣合・分配チェック"])
    if mdl is not None:
        eq_rows = compute_wind_equilibrium(mdl, result)
        if eq_rows:
            check_rows = []
            for row in eq_rows:
                check_rows.append([
                    row["wind_case_name"],
                    _fmt(row["sum_f_wind_generated_kN"], 3),
                    _fmt(row["sum_f_dlod_output_kN"], 3),
                    _fmt(row.get("sum_f_to_base_kN", 0.0), 3),
                    _fmt(row["fx_applied_kN"], 3),
                    _fmt(row["sum_reaction_kN"], 3),
                    _fmt(row["equilibrium_residual_kN"], 4),
                    "OK" if row["equilibrium_ok"] else "NG",
                    "OK" if row.get("distribution_ok", True) else "NG",
                ])
            parts.append(_md_table(
                ["ケース", "ΣF_wall", "ΣF_DLOD", "ΣF_base", "ΣFx", "ΣRx", "残差", "釣合", "分配"],
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

    parts.extend(["", "## 8. 注意", "", "> " + WIND_NOTICE, ""])
    return "\n".join(parts)


def _wind_flow_vector(direction: str) -> dict:
    conv = resolve_wind_direction_convention(direction)
    ux = float(conv.sign) if conv.axis == "x" else 0.0
    uy = float(conv.sign) if conv.axis == "y" else 0.0
    return {"ux": ux, "uy": uy}


def _direction_label(direction: str) -> str:
    return format_wind_case_short_name(direction)


def build_wind_summary_rows(result: WindDistributionResult):
    rows = []
    if not result.cases:
        rows.append({"label": "風荷重ケース", "value": "—", "unit": "", "note": "未設定"})
        return rows
    for c in result.cases:
        rows.append({
            "label": c.name,
            "value": _direction_label(c.direction),
            "unit": "",
            "note": "LC{0} · V0={1} m/s · q={2} N/m²".format(
                c.load_case, _fmt(c.v0, 1), _fmt(c.q_N_m2, 1),
            ),
        })
    total_f = sum(sf.f_story_kN for sf in result.story_forces)
    rows.append({
        "label": "ΣF_story（全ケース・全階）",
        "value": _fmt(total_f, 3),
        "unit": "kN",
        "note": "",
    })
    rows.append({
        "label": "DLOD 出力",
        "value": str(len(result.diaphragm_loads)),
        "unit": "件",
        "note": result.cases[0].diaphragm_input_mode if result.cases else "",
    })
    return rows


def build_wind_surface_rows(result: WindDistributionResult):
    rows = []
    case_names = {c.case_id: c.name for c in result.cases}
    force_by_surface: dict = {}
    for sc in result.surface_contributions:
        key = sc.surface_id
        force_by_surface[key] = force_by_surface.get(key, 0.0) + sc.force_kN
    for s in result.surfaces:
        rows.append({
            "surface_id": s.surface_id,
            "name": s.name,
            "wind_case": case_names.get(s.wind_case_id, str(s.wind_case_id)),
            "surface_role": s.surface_role,
            "face_direction": s.face_direction,
            "face_label": format_wind_face_label_jp(s.face_direction),
            "direction_label": format_wind_face_label_jp(s.face_direction),
            "z_bottom": s.z_bottom,
            "z_top": s.z_top,
            "width": s.width,
            "gross_area_m2": s.gross_area_m2,
            "cf": s.cf,
            "total_force_kN": force_by_surface.get(s.surface_id, 0.0),
            "wall_side": wind_face_to_wall_side(s.face_direction),
        })
    return rows


def build_wind_story_force_rows(result: WindDistributionResult):
    case_names = {c.case_id: c.name for c in result.cases}
    rows = []
    for sf in result.story_forces:
        rows.append({
            "wind_case_id": sf.wind_case_id,
            "wind_case": case_names.get(sf.wind_case_id, str(sf.wind_case_id)),
            "story": sf.story,
            "z_bottom": sf.z_bottom,
            "z_top": sf.z_top,
            "windward_force_kN": sf.windward_force_kN,
            "leeward_force_kN": sf.leeward_force_kN,
            "f_story_kN": sf.f_story_kN,
            "target_diaphragm_id": sf.target_diaphragm_id,
            "output_to_dlod": sf.output_to_dlod,
        })
    return rows


def build_wind_tributary_rows(result: WindDistributionResult):
    case_names = {c.case_id: c.name for c in result.cases}
    rows = []
    for row in result.diaphragm_tributary_rows:
        rows.append({
            "wind_case_id": row.wind_case_id,
            "wind_case": case_names.get(row.wind_case_id, str(row.wind_case_id)),
            "diaphragm_id": row.diaphragm_id,
            "diaphragm_level": row.diaphragm_level_m,
            "lower_adjacent_level": row.lower_adjacent_level_m,
            "upper_adjacent_level": row.upper_adjacent_level_m,
            "tributary_z_bottom": row.tributary_z_bottom,
            "tributary_z_top": row.tributary_z_top,
            "tributary_height": row.tributary_height,
            "exposed_width": row.exposed_width,
            "tributary_area": row.tributary_area_m2,
            "wind_pressure": row.wind_pressure_w_N_m2,
            "story_wind_force": row.story_wind_force_kN,
            "output_to_dlod": row.output_to_dlod,
            "story": row.story,
            "windward_force_kN": row.windward_force_kN,
            "leeward_force_kN": row.leeward_force_kN,
        })
    return rows


def build_wind_base_rows(result: WindDistributionResult):
    case_names = {c.case_id: c.name for c in result.cases}
    rows = []
    for row in result.base_wind_forces:
        rows.append({
            "wind_case_id": row.wind_case_id,
            "wind_case": case_names.get(row.wind_case_id, str(row.wind_case_id)),
            "z_bottom": row.z_bottom,
            "z_top": row.z_top,
            "tributary_height": row.tributary_height,
            "tributary_area": row.tributary_area_m2,
            "wind_pressure": row.wind_pressure_w_N_m2,
            "f_wind_to_base_kN": row.f_wind_to_base_kN,
        })
    return rows


def build_wind_validation_rows(result: WindDistributionResult):
    rows = []
    for row in result.tributary_validations:
        rows.append({
            "wind_case_id": row.wind_case_id,
            "gross_wall_area_m2": row.gross_wall_area_m2,
            "diaphragm_tributary_area_m2": row.diaphragm_tributary_area_m2,
            "base_tributary_area_m2": row.base_tributary_area_m2,
            "gross_wall_force_kN": row.gross_wall_force_kN,
            "diaphragm_force_kN": row.diaphragm_force_kN,
            "base_force_kN": row.base_force_kN,
            "area_conservation_ok": row.area_conservation_ok,
            "force_conservation_ok": row.force_conservation_ok,
            "conservation_ok": row.conservation_ok,
        })
    return rows


def build_wind_diaphragm_rows(result: WindDistributionResult):
    rows = []
    for dl in result.diaphragm_loads:
        rows.append({
            "load_case": dl.load_case,
            "diaphragm_id": dl.diaphragm_id,
            "story": dl.story,
            "direction": _direction_label(dl.direction),
            "axis": dl.axis,
            "sign": dl.sign,
            "load_level_m": dl.load_level_m,
            "input_mode": dl.input_mode,
            "f_story_kN": dl.f_story_kN,
            "diaphragm_area_m2": dl.diaphragm_area_m2,
            "area_load_kN_m2": dl.area_load_kN_m2,
        })
    return rows


def _node_xy_bbox(mdl):
    if mdl is None or not getattr(mdl, "nds", None):
        return None
    xs = [float(n.x) for n in mdl.nds]
    ys = [float(n.y) for n in mdl.nds]
    if not xs or not ys:
        return None
    return {
        "x_min": min(xs),
        "x_max": max(xs),
        "y_min": min(ys),
        "y_max": max(ys),
    }


def build_wind_visual_cases(mdl, result: WindDistributionResult):
    bbox = _node_xy_bbox(mdl)
    if bbox is None:
        return {"bbox": None, "cases": []}

    force_by_surface: dict = {}
    for sc in result.surface_contributions:
        force_by_surface[sc.surface_id] = force_by_surface.get(sc.surface_id, 0.0) + sc.force_kN

    visual_cases = []
    for case in result.cases:
        flow = _wind_flow_vector(case.direction)
        conv = resolve_wind_direction_convention(case.direction)
        surfaces = []
        for s in result.surfaces:
            if s.wind_case_id != case.case_id:
                continue
            surfaces.append({
                "surface_id": s.surface_id,
                "name": s.name,
                "surface_role": s.surface_role,
                "face_direction": s.face_direction,
                "wall_side": wind_face_to_wall_side(s.face_direction),
                "z_bottom": s.z_bottom,
                "z_top": s.z_top,
                "width": s.width,
                "cf": s.cf,
                "total_force_kN": force_by_surface.get(s.surface_id, 0.0),
            })
        story_forces = []
        max_f = 0.0
        for sf in result.story_forces:
            if sf.wind_case_id != case.case_id:
                continue
            max_f = max(max_f, abs(sf.f_story_kN))
            story_forces.append({
                "story": sf.story,
                "z_bottom": sf.z_bottom,
                "z_top": sf.z_top,
                "z_ref": sf.z_ref,
                "f_story_kN": sf.f_story_kN,
                "windward_force_kN": sf.windward_force_kN,
                "leeward_force_kN": sf.leeward_force_kN,
                "target_diaphragm_id": sf.target_diaphragm_id,
                "output_to_dlod": sf.output_to_dlod,
            })
        diaphragm_loads = []
        for dl in result.diaphragm_loads:
            if dl.wind_case_id != case.case_id:
                continue
            diaphragm_loads.append({
                "diaphragm_id": dl.diaphragm_id,
                "story": dl.story,
                "load_case": dl.load_case,
                "f_story_kN": dl.f_story_kN,
                "area_load_kN_m2": dl.area_load_kN_m2,
                "load_level_m": dl.load_level_m,
                "axis": dl.axis,
                "sign": dl.sign,
            })
        tributary_rows = []
        for tr in result.diaphragm_tributary_rows:
            if tr.wind_case_id != case.case_id:
                continue
            tributary_rows.append({
                "diaphragm_id": tr.diaphragm_id,
                "story": tr.story,
                "diaphragm_level": tr.diaphragm_level_m,
                "tributary_z_bottom": tr.tributary_z_bottom,
                "tributary_z_top": tr.tributary_z_top,
                "tributary_height": tr.tributary_height,
                "story_wind_force_kN": tr.story_wind_force_kN,
                "output_to_dlod": tr.output_to_dlod,
            })
        visual_cases.append({
            "wind_case_id": case.case_id,
            "name": case.name,
            "load_case": case.load_case,
            "direction": case.direction,
            "direction_label": _direction_label(case.direction),
            "applied_load_direction": conv.applied_load_direction,
            "applied_load_direction_label": format_applied_load_direction_label(case.direction),
            "wind_flow_from": conv.wind_flow_from,
            "wind_flow_to": conv.wind_flow_to,
            "wind_flow_label": format_wind_flow_label(case.direction),
            "windward_face": conv.windward_face,
            "leeward_face": conv.leeward_face,
            "windward_face_label": format_wind_face_label_jp(conv.windward_face),
            "leeward_face_label": format_wind_face_label_jp(conv.leeward_face),
            "axis": case.axis,
            "sign": case.sign,
            "flow": flow,
            "max_f_story_kN": max_f,
            "surfaces": surfaces,
            "story_forces": story_forces,
            "diaphragm_loads": diaphragm_loads,
            "tributary_rows": tributary_rows,
        })

    return {"bbox": bbox, "cases": visual_cases}


def build_wind_report_checks(result: WindDistributionResult, report: dict):
    checks = []
    checks.append({
        "label": "風荷重ケースが 1 件以上定義されている",
        "ok": bool(result.cases),
        "detail": "{0} 件".format(len(result.cases)),
    })
    checks.append({
        "label": "受圧面が 1 件以上定義されている",
        "ok": bool(result.surfaces),
        "detail": "{0} 件".format(len(result.surfaces)),
    })
    dlod_count = len(report.get("diaphragm_rows") or [])
    checks.append({
        "label": "DLOD 等価入力が生成されている",
        "ok": dlod_count > 0,
        "detail": "{0} 件".format(dlod_count),
    })
    if result.tributary_validations:
        all_ok = all(r.conservation_ok for r in result.tributary_validations)
        checks.append({
            "label": "外壁面積・風力の支配高さ分配（ΣF_wall = ΣF_DLOD + ΣF_base）",
            "ok": all_ok,
            "detail": "OK" if all_ok else "NG あり",
        })
    if report.get("equilibrium_rows"):
        all_ok = all(r.get("equilibrium_ok") for r in report["equilibrium_rows"])
        checks.append({
            "label": "解析モデルでの荷重・反力釣合",
            "ok": all_ok,
            "detail": "OK" if all_ok else "NG あり",
        })
        dist_ok = all(r.get("distribution_ok", True) for r in report["equilibrium_rows"])
        checks.append({
            "label": "DLOD + 基礎側風力 = 外壁生成風力",
            "ok": dist_ok,
            "detail": "OK" if dist_ok else "NG あり",
        })
    return checks


def build_wind_report_view(
    result: WindDistributionResult,
    project=None,
    mdl=None,
    *,
    include_visual: bool = True,
):
    mdl_solved = prepare_solved_model(mdl) if mdl is not None and result.diaphragm_loads else None
    report = {
        "summary": build_wind_summary_rows(result),
        "surface_rows": build_wind_surface_rows(result),
        "tributary_rows": build_wind_tributary_rows(result),
        "base_wind_rows": build_wind_base_rows(result),
        "validation_rows": build_wind_validation_rows(result),
        "story_force_rows": build_wind_story_force_rows(result),
        "diaphragm_rows": build_wind_diaphragm_rows(result),
        "uniform_input_note": UNIFORM_INPUT_NOTE,
        "report_notice": WIND_NOTICE,
        "dlod_section_title": "DLOD 等価入力",
        "visual": build_wind_visual_cases(mdl, result) if include_visual else None,
    }
    if mdl is not None:
        report["equilibrium_rows"] = compute_wind_equilibrium(
            mdl, result, mdl_solved=mdl_solved
        )
    else:
        report["equilibrium_rows"] = []
    report["checks"] = build_wind_report_checks(result, report)
    return report
