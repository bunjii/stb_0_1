"""Editable project.json form schema for the GUI."""

from __future__ import annotations

from typing import Any, Dict, List

from stb_project.schema import (
    ALLOWED_BASE_MASS_POLICIES,
    ALLOWED_MEMBER_KINDS,
    ALLOWED_REPORT_FORMATS,
    ALLOWED_REPORT_MODES,
    DEFAULT_SEISMIC_RT,
)
from stb_project import ProjectDefinition, effective_seismic_ci


def build_project_edit_form(project: ProjectDefinition) -> Dict[str, Any]:
    seismic = project.load_conditions.seismic
    ci_eff = effective_seismic_ci(seismic) if seismic.ci > 0 else 0.0
    wood = project.design_checks.wood
    b = project.building
    d = b.designer
    r = project.report

    sections: List[Dict[str, Any]] = [
        {
            "id": "model",
            "title": "モデル",
            "fields": [
                {"path": "model.dat", "label": "解析ファイル (.dat)", "type": "text", "value": project.dat_path},
                {"path": "schema", "label": "スキーマ版", "type": "number", "value": project.schema},
            ],
        },
        {
            "id": "building",
            "title": "建築情報",
            "fields": [
                {"path": "building.name", "label": "建築名称", "type": "text", "value": b.name},
                {"path": "building.location", "label": "所在地", "type": "text", "value": b.location},
                {"path": "building.use", "label": "用途", "type": "text", "value": b.use},
                {"path": "building.structure", "label": "構造", "type": "text", "value": b.structure},
                {"path": "building.calculation_route", "label": "計算ルート", "type": "text", "value": b.calculation_route},
                {"path": "building.designer.name", "label": "設計者", "type": "text", "value": d.name},
                {"path": "building.designer.qualification", "label": "資格", "type": "text", "value": d.qualification},
                {"path": "building.designer.license_number", "label": "登録番号", "type": "text", "value": d.license_number},
                {"path": "building.designer.contact", "label": "連絡先", "type": "text", "value": d.contact},
            ],
        },
        {
            "id": "grids",
            "title": "通り芯",
            "table": {
                "path": "grids",
                "label": "通り芯一覧",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "direction", "label": "方向", "type": "select", "options": ["x", "y"]},
                    {"path": "coordinate", "label": "座標 m", "type": "number"},
                ],
                "rows": [
                    {"name": g.name, "direction": g.direction, "coordinate": g.coordinate}
                    for g in project.grids
                ],
            },
        },
        {
            "id": "stories",
            "title": "階",
            "table": {
                "path": "stories",
                "label": "階情報",
                "columns": [
                    {"path": "name", "label": "階", "type": "text"},
                    {"path": "elevation", "label": "床レベル m", "type": "number"},
                    {"path": "height", "label": "階高 m", "type": "number"},
                ],
                "rows": [
                    {"name": s.name, "elevation": s.elevation, "height": s.height}
                    for s in project.stories
                ],
            },
        },
        {
            "id": "member_classes",
            "title": "部材クラス",
            "table": {
                "path": "member_classes",
                "label": "部材クラス",
                "columns": [
                    {"path": "name", "label": "名称", "type": "text"},
                    {"path": "kind", "label": "種別", "type": "select", "options": list(ALLOWED_MEMBER_KINDS)},
                    {"path": "story", "label": "階", "type": "text"},
                    {"path": "element_ids", "label": "要素 ID (カンマ区切り)", "type": "csv_int"},
                    {"path": "use", "label": "用途", "type": "text"},
                    {"path": "notes", "label": "メモ", "type": "text"},
                ],
                "rows": [
                    {
                        "name": c.name,
                        "kind": c.kind,
                        "story": c.story,
                        "element_ids": c.element_ids,
                        "use": c.use,
                        "notes": c.notes,
                    }
                    for c in project.member_classes
                ],
            },
        },
        {
            "id": "load_conditions",
            "title": "荷重条件",
            "fields": [
                {
                    "path": "load_conditions.seismic.ci",
                    "label": "Ci (入力)",
                    "type": "number",
                    "value": seismic.ci,
                    "hint": "Z×C0 相当（Rt 除く）",
                },
                {
                    "path": "load_conditions.seismic.rt",
                    "label": "Rt (振動特性係数)",
                    "type": "number",
                    "value": seismic.rt,
                    "hint": "省略時は {0}".format(DEFAULT_SEISMIC_RT),
                },
                {
                    "path": "load_conditions.seismic.base_level",
                    "label": "基礎・土台レベル (階)",
                    "type": "text",
                    "value": seismic.base_level or "",
                    "hint": "地震載荷階として扱わない床レベル",
                },
                {
                    "path": "load_conditions.seismic.base_elevation",
                    "label": "基礎レベル標高 m",
                    "type": "number",
                    "value": seismic.base_elevation if seismic.base_elevation is not None else "",
                    "hint": "base_level 未指定時の代替",
                },
                {
                    "path": "load_conditions.seismic.base_mass_policy",
                    "label": "基礎レベル質量の扱い",
                    "type": "select",
                    "options": list(ALLOWED_BASE_MASS_POLICIES),
                    "value": seismic.base_mass_policy,
                },
                {
                    "path": "load_conditions.seismic.dead_load_lc",
                    "label": "DL 荷重ケース (override)",
                    "type": "optional_int",
                    "value": seismic.dead_load_lc,
                },
                {
                    "path": "load_conditions.seismic.live_load_lc",
                    "label": "LL 荷重ケース (override)",
                    "type": "optional_int",
                    "value": seismic.live_load_lc,
                },
                {
                    "path": "load_conditions.seismic.live_load_factor",
                    "label": "活荷重係数",
                    "type": "number",
                    "value": seismic.live_load_factor,
                },
            ],
            "readonly": [
                {
                    "label": "Ci (有効 = Ci×Rt)",
                    "value": ci_eff if ci_eff > 0 else None,
                    "hint": "V = Ci(有効) × ΣWi",
                },
            ],
            "table": {
                "path": "load_conditions.diaphragms",
                "label": "ダイアフラム ↔ 階",
                "columns": [
                    {"path": "id", "label": "DIAP ID", "type": "number"},
                    {"path": "story", "label": "階", "type": "text"},
                ],
                "rows": [
                    {"id": d.diaphragm_id, "story": d.story}
                    for d in project.load_conditions.diaphragms
                ],
            },
        },
        {
            "id": "design_checks",
            "title": "設計検討 (木造)",
            "fields": [
                {"path": "design_checks.wood.enabled", "label": "有効", "type": "bool", "value": wood.enabled},
                {
                    "path": "design_checks.wood.load_cases",
                    "label": "荷重ケース (カンマ区切り)",
                    "type": "csv_int",
                    "value": list(wood.load_cases),
                },
                {
                    "path": "design_checks.wood.deflection_limit_ratio",
                    "label": "たわみ限界 (L/×)",
                    "type": "number",
                    "value": wood.deflection_limit_ratio,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.bending",
                    "label": "許容曲げ N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.bending,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.shear",
                    "label": "許容せん断 N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.shear,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.compression",
                    "label": "許容圧縮 N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.compression,
                },
                {
                    "path": "design_checks.wood.allowable_stresses.tension",
                    "label": "許容引張 N/mm²",
                    "type": "number",
                    "value": wood.allowable_stresses.tension,
                },
            ],
        },
        {
            "id": "report",
            "title": "帳票",
            "fields": [
                {"path": "report.title", "label": "タイトル", "type": "text", "value": r.title},
                {"path": "report.mode", "label": "モード", "type": "select", "options": list(ALLOWED_REPORT_MODES), "value": r.mode},
                {"path": "report.language", "label": "言語", "type": "text", "value": r.language},
                {"path": "report.format", "label": "形式", "type": "select", "options": list(ALLOWED_REPORT_FORMATS), "value": r.format},
                {"path": "report.include_manual_items", "label": "手入力項目を含む", "type": "bool", "value": r.include_manual_items},
                {"path": "report.include_warnings", "label": "警告を含む", "type": "bool", "value": r.include_warnings},
            ],
        },
    ]

    return {"sections": sections}
