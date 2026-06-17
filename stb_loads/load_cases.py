from typing import List, Optional, Tuple

from load_case_types import (
    LC_TYPE_CUSTOM,
    LC_TYPE_DL,
    LC_TYPE_E,
    SEISMIC_WEIGHT_TYPES,
    canonical_name,
    infer_axis_from_label,
)


def _lcases(mdl):
    return getattr(mdl, "lcases", []) or []


def resolve_load_cases_by_type(mdl, load_type: int) -> Tuple[List[int], List[str]]:
    """Return LC ids for one LNME TYPE (e.g. TYPE 1 DL, TYPE 2 LL)."""
    typed = sorted(
        lc.lc for lc in _lcases(mdl)
        if getattr(lc, "load_type", None) == load_type
    )
    return typed, []


def resolve_seismic_weight_load_cases(mdl, seismic_settings=None) -> Tuple[List[int], List[str]]:
    """Return LC ids used for Wi aggregation (TYPE 1 DL + TYPE 3 LL(E))."""

    warnings = []
    typed = sorted(
        lc.lc for lc in _lcases(mdl)
        if getattr(lc, "load_type", None) in SEISMIC_WEIGHT_TYPES
    )
    if typed:
        return typed, warnings

    if seismic_settings is not None:
        dead_lc = getattr(seismic_settings, "dead_load_lc", None)
        live_lc = getattr(seismic_settings, "live_load_lc", None)
        live_factor = float(getattr(seismic_settings, "live_load_factor", 0.0) or 0.0)
        if dead_lc is not None:
            warnings.append(
                "LNME TYPE 1/3 not found; using project.load_conditions.seismic.dead_load_lc override."
            )
            lcs = [int(dead_lc)]
            if live_lc is not None and live_factor != 0.0:
                lcs.append(int(live_lc))
            return lcs, warnings

    glod_lcs = sorted({
        g.lc for g in getattr(mdl, "glds", [])
        if not getattr(g, "combi", False)
    })
    if len(glod_lcs) == 1:
        warnings.append(
            "LNME TYPE 1/3 not found; using sole GLOD load case LC {0} as DL.".format(glod_lcs[0])
        )
        return glod_lcs, warnings

    legacy_dl = sorted(
        lc.lc for lc in _lcases(mdl)
        if str(getattr(lc, "label", "") or getattr(lc, "lname", "")).upper() in ("DL", "DEAD")
        or getattr(lc, "load_type", None) == LC_TYPE_DL
    )
    if legacy_dl:
        warnings.append("LNME TYPE 1/3 not found; using legacy DL-named load cases.")
        return legacy_dl, warnings

    return [], warnings + ["No seismic weight load cases (LNME TYPE 1 or 3) were resolved."]


def resolve_seismic_directions(mdl, project_directions=()) -> Tuple[list, List[str]]:
    """Build seismic direction targets from LNME TYPE 6, with optional project override."""

    if project_directions:
        return list(project_directions), []

    warnings = []
    directions = []
    for lc in _lcases(mdl):
        if getattr(lc, "load_type", None) != LC_TYPE_E:
            continue
        label = getattr(lc, "label", "") or getattr(lc, "lname", "")
        axis, sign = infer_axis_from_label(label)
        if axis is None:
            warnings.append(
                "LNME LC {0} (TYPE 6) has no axis hint in label '{1}'; defaulting to X.".format(
                    lc.lc, label
                )
            )
            axis = "x"
        directions.append(_Direction(name=canonical_name(LC_TYPE_E, label), axis=axis, load_case=lc.lc, sign=sign))

    if not directions:
        warnings.append("No LNME TYPE 6 (E) load cases found for seismic DLOD output.")
    return directions, warnings


class _Direction:
    __slots__ = ("name", "axis", "load_case", "sign")

    def __init__(self, name, axis, load_case, sign):
        self.name = name
        self.axis = axis
        self.load_case = load_case
        self.sign = sign
