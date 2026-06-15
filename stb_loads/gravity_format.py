"""Dead / live gravity load verification views for the GUI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from load_case_types import LC_TYPE_DL, LC_TYPE_LL, canonical_name

from stb_loads.equilibrium import prepare_solved_model
from stb_loads.load_cases import resolve_load_cases_by_type
from stb_loads.weight import aggregate_story_weights_for_lcs, aggregate_weight_for_load_case

DEAD_NOTICE = (
    "固定荷重（LNME TYPE 1）の鉛直荷重を、解析モデルの nodal 載荷と支点反力で確認します。"
    "Wi は FEM 載荷マトリクスを階ごとに集計した値です。"
)

LIVE_NOTICE = (
    "積載荷重（LNME TYPE 2）の鉛直荷重を、解析モデルの nodal 載荷と支点反力で確認します。"
    "地震用 LL(E)（TYPE 3）は地震荷重タブで扱います。"
)


def _fmt_num(value, places=3):
    if value is None:
        return "—"
    n = float(value)
    if abs(n - round(n)) < 1.0e-9:
        return str(int(round(n)))
    return ("{0:." + str(places) + "f}").format(n)


def _lc_meta(mdl, lc: int) -> Dict[str, str]:
    for item in getattr(mdl, "lcases", []) or []:
        if item.lc != lc:
            continue
        label = getattr(item, "label", "") or getattr(item, "lname", "") or ""
        load_type = getattr(item, "load_type", None)
        return {
            "load_case": str(lc),
            "label": label or str(lc),
            "type_name": canonical_name(load_type, label) if load_type is not None else "—",
        }
    return {"load_case": str(lc), "label": str(lc), "type_name": "—"}


def _input_inventory(mdl, lc: int) -> Dict[str, int]:
    def _count(items, attr="lc"):
        n = 0
        for item in items or []:
            if getattr(item, attr, None) != lc:
                continue
            if getattr(item, "combi", False):
                continue
            n += 1
        return n

    dload = 0
    dload_weight = 0
    for dl in getattr(mdl, "dloads", []) or []:
        if dl.lc != lc or getattr(dl, "combi", False):
            continue
        dload += 1
        if getattr(dl, "load_type", None) in ("WEIGHT", "MASS"):
            dload_weight += 1

    return {
        "gld": _count(getattr(mdl, "glds", [])),
        "pld": _count(getattr(mdl, "lds", [])),
        "eld": _count(getattr(mdl, "elds", [])),
        "ald": _count(getattr(mdl, "alds", [])),
        "dlod_total": dload,
        "dlod_weight": dload_weight,
    }


def _sum_reaction_tz_kN(mdl_solved, lc: int) -> float:
    col = mdl_solved.lcs.index(lc)
    total = 0.0
    for c in mdl_solved.cons:
        reacts = getattr(c.nd, "reacts", None)
        if reacts is None:
            continue
        total += float(reacts[col, 2]) * 1e-3
    return total


def build_gravity_story_rows(weight_result) -> List[Dict[str, Any]]:
    rows = []
    for sw in sorted(weight_result.stories, key=lambda s: s.elevation, reverse=True):
        rows.append(
            {
                "story": sw.story_name,
                "story_level_m": sw.elevation,
                "height_m": sw.height,
                "weight_kN": sw.weight_kN,
            }
        )
    return rows


def build_gravity_lc_rows(
    mdl,
    project,
    load_lcs: Sequence[int],
    mdl_solved=None,
) -> List[Dict[str, Any]]:
    if mdl_solved is None:
        mdl_solved = prepare_solved_model(mdl)
    rows: List[Dict[str, Any]] = []
    for lc in load_lcs:
        meta = _lc_meta(mdl, lc)
        wi = aggregate_weight_for_load_case(mdl, project, lc)
        tz = _sum_reaction_tz_kN(mdl_solved, lc)
        tol = max(1.0e-3, abs(wi) * 1.0e-9)
        ok = abs(abs(tz) - wi) <= tol
        inv = _input_inventory(mdl, lc)
        rows.append(
            {
                **meta,
                "wi_kN": wi,
                "reaction_tz_kN": tz,
                "equilibrium_ok": ok,
                **inv,
            }
        )
    return rows


def build_gravity_summary_rows(kind: str, load_lcs: Sequence[int], total_kN: float) -> List[Dict[str, Any]]:
    type_label = "固定荷重 (TYPE 1 DL)" if kind == "dead" else "積載荷重 (TYPE 2 LL)"
    return [
        {"label": "荷重種別", "value": type_label},
        {
            "label": "対象 LC",
            "value": ", ".join("LC{0}".format(lc) for lc in load_lcs) or "—",
        },
        {"label": "ΣWi", "value": _fmt_num(total_kN), "unit": "kN"},
    ]


def build_gravity_checks(lc_rows: List[Dict[str, Any]], total_kN: float) -> List[Dict[str, Any]]:
    checks = []
    if not lc_rows:
        checks.append(
            {
                "label": "対象荷重ケースが 1 件以上定義されている",
                "ok": False,
                "detail": "LNME に該当 TYPE がありません",
            }
        )
        return checks

    checks.append(
        {
            "label": "対象荷重ケースが 1 件以上定義されている",
            "ok": True,
            "detail": "{0} 件".format(len(lc_rows)),
        }
    )
    all_ok = all(r.get("equilibrium_ok") for r in lc_rows)
    parts = [
        "LC{0} Wi={1} kN, ΣTz={2} kN".format(
            r["load_case"], _fmt_num(r["wi_kN"]), _fmt_num(r["reaction_tz_kN"])
        )
        for r in lc_rows
    ]
    checks.append(
        {
            "label": "各 LC の Wi が鉛直反力合計と一致すること",
            "ok": all_ok,
            "detail": "; ".join(parts) if parts else "—",
        }
    )
    if len(lc_rows) > 1:
        tz_sum = sum(r["reaction_tz_kN"] for r in lc_rows)
        tol = max(1.0e-3, abs(total_kN) * 1.0e-9)
        checks.append(
            {
                "label": "ΣWi が全 LC の反力合計と一致すること",
                "ok": abs(abs(tz_sum) - total_kN) <= tol,
                "detail": "ΣWi={0} kN, ΣTz={1} kN".format(
                    _fmt_num(total_kN), _fmt_num(tz_sum)
                ),
            }
        )
    return checks


def build_gravity_load_report(
    mdl,
    project,
    *,
    kind: str,
    load_type: int,
    notice: str,
) -> Dict[str, Any]:
    load_lcs, _ = resolve_load_cases_by_type(mdl, load_type)
    weight_result = aggregate_story_weights_for_lcs(mdl, project, load_lcs)
    mdl_solved = prepare_solved_model(mdl) if load_lcs else None
    lc_rows = build_gravity_lc_rows(mdl, project, load_lcs, mdl_solved=mdl_solved)
    return {
        "summary": build_gravity_summary_rows(kind, load_lcs, weight_result.total_weight_kN),
        "story_rows": build_gravity_story_rows(weight_result),
        "lc_rows": lc_rows,
        "checks": build_gravity_checks(lc_rows, weight_result.total_weight_kN),
        "report_notice": notice,
        "warnings": list(weight_result.warnings),
        "found": bool(load_lcs),
        "load_cases": list(load_lcs),
    }


def build_dead_load_report(mdl, project) -> Dict[str, Any]:
    return build_gravity_load_report(
        mdl,
        project,
        kind="dead",
        load_type=LC_TYPE_DL,
        notice=DEAD_NOTICE,
    )


def build_live_load_report(mdl, project) -> Dict[str, Any]:
    return build_gravity_load_report(
        mdl,
        project,
        kind="live",
        load_type=LC_TYPE_LL,
        notice=LIVE_NOTICE,
    )
