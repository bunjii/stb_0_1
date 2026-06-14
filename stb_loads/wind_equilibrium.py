"""Wind load equilibrium checks."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from stb_loads.wind import (
    WindDistributionResult,
    total_base_wind_kN,
    total_dlod_output_kN,
    total_wind_generated_kN,
)


def _ensure_solver_path():
    import os
    import sys
    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)


def _lc_column(mdl, lc: int) -> Optional[int]:
    if mdl.lcs is None:
        return None
    try:
        return mdl.lcs.index(lc)
    except ValueError:
        return None


def _load_matrix_kN(mdl):
    _ensure_solver_path()
    from solve import Solve

    solver = Solve.__new__(Solve)
    solver.mdl = mdl
    solver.ndof = 6
    solver.num_row = solver.ndof * len(mdl.nds)
    lm = solver.CreateLoadMx(apply_constraints=False)
    return lm * 1e-3, solver.ndof


def _sum_translation_kN(mdl, lc: int, dof: int) -> float:
    col = _lc_column(mdl, lc)
    if col is None:
        return 0.0
    lm, ndof = _load_matrix_kN(mdl)
    total = 0.0
    for n in mdl.nds:
        total += float(lm[n.cid * ndof + dof, col])
    return total


def _sum_reaction_translation_kN(mdl, lc: int, dof: int) -> float:
    col = _lc_column(mdl, lc)
    if col is None:
        return 0.0
    total = 0.0
    for c in mdl.cons:
        reacts = getattr(c.nd, "reacts", None)
        if reacts is None:
            continue
        total += float(reacts[col, dof]) * 1e-3
    return total


from stb_project.schema import format_applied_load_direction_label, format_wind_case_short_name


def compute_wind_equilibrium(mdl, result: WindDistributionResult) -> List[Dict[str, Any]]:
    from stb_engine import solve_model

    keys: List[Tuple[int, int, str, int]] = []
    seen = set()
    for dl in result.diaphragm_loads:
        key = (dl.wind_case_id, dl.load_case, dl.axis, dl.sign)
        if key not in seen:
            seen.add(key)
            keys.append(key)

    if not keys:
        return []

    mdl_solved = copy.deepcopy(mdl)
    solve_model(mdl_solved)

    rows: List[Dict[str, Any]] = []
    for case_id, lc, axis, sign in sorted(keys):
        dof = 0 if axis == "x" else 1
        fx_applied = _sum_translation_kN(mdl, lc, dof)
        sum_rx = _sum_reaction_translation_kN(mdl_solved, lc, dof)
        f_wind = total_wind_generated_kN(result, case_id)
        f_dlod = total_dlod_output_kN(result, case_id)
        f_base = total_base_wind_kN(result, case_id)
        residual = abs(fx_applied + sum_rx)

        case_name = next((c.name for c in result.cases if c.case_id == case_id), str(case_id))
        direction = next(
            (dl.direction for dl in result.diaphragm_loads if dl.wind_case_id == case_id),
            "X_PLUS" if axis == "x" and sign >= 0 else "X_MINUS",
        )

        rows.append({
            "wind_case_id": case_id,
            "wind_case_name": case_name,
            "load_case": lc,
            "direction": format_wind_case_short_name(direction),
            "applied_load_direction_label": format_applied_load_direction_label(direction),
            "axis": axis,
            "sign": sign,
            "sum_f_wind_generated_kN": f_wind,
            "sum_f_dlod_output_kN": f_dlod,
            "sum_f_to_base_kN": f_base,
            "fx_applied_kN": fx_applied,
            "sum_reaction_kN": sum_rx,
            "equilibrium_residual_kN": residual,
            "equilibrium_ok": residual <= max(1.0e-2, abs(f_dlod) * 1.0e-3),
            "distribution_ok": abs(f_wind - (f_dlod + f_base)) <= max(0.05, abs(f_wind) * 1.0e-3),
        })
    return rows
