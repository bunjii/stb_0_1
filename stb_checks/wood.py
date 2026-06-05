from dataclasses import dataclass
import math
from typing import Optional, Tuple

from stb_project import ProjectDefinition, WoodAllowableStresses


CHECKED_MEMBER_KINDS = ("beam", "column", "brace")
DEFAULT_TOLERANCE = 1.0e-9
STRESS_UNIT = 1.0e6  # N/mm2 to N/m2


@dataclass(frozen=True)
class WoodCheckDemand:
    load_case: int
    axial: float
    shear_y: float
    shear_z: float
    moment_y: float
    moment_z: float
    deflection: Optional[float]


@dataclass(frozen=True)
class WoodElementCheck:
    element_id: int
    member_class: str
    kind: str
    section: str
    material: str
    governing_load_case: int
    axial_ratio: float
    bending_ratio: float
    shear_ratio: float
    deflection_ratio: Optional[float]
    combined_ratio: float
    status: str
    demand: WoodCheckDemand


@dataclass(frozen=True)
class WoodCheckTables:
    element_checks: Tuple[dict, ...]
    member_classes: Tuple[dict, ...]


@dataclass(frozen=True)
class WoodCheckSummary:
    element_checks: Tuple[WoodElementCheck, ...]
    warnings: Tuple[str, ...]
    max_ratio: float
    status: str
    tables: WoodCheckTables


def build_wood_check_summary(mdl, project: ProjectDefinition):
    """Build MVP wood member checks for beams, columns, and braces.

    Stresses are calculated from solved member end forces. Allowable stresses
    in project JSON are expected in N/mm2 and converted to internal N/m2.
    """

    warnings = []
    if project.building.structure.lower() != "wood":
        warnings.append("Project building.structure is not wood; wood checks were still evaluated.")

    load_cases = _load_cases_to_check(mdl, project, warnings)
    load_case_indices = {lc: idx for idx, lc in enumerate(mdl.lcs)}
    checks = []
    for member_class in project.member_classes:
        if member_class.kind not in CHECKED_MEMBER_KINDS:
            continue
        for element_id in member_class.element_ids:
            e = mdl.FindElemFromEid(element_id)
            if e == -1:
                warnings.append(
                    "Member class {0} references missing element {1}.".format(
                        member_class.name,
                        element_id,
                    )
                )
                continue
            if getattr(e, "forces", None) is None:
                warnings.append("Element {0} has no solved forces and was skipped.".format(element_id))
                continue
            checks.append(_check_element(e, member_class, load_cases, load_case_indices, project, warnings))

    if not checks:
        warnings.append("No beam, column, or brace member classes were available for wood checks.")

    max_ratio = max([c.combined_ratio for c in checks] + [0.0])
    status = "OK" if checks and max_ratio <= 1.0 else "NG" if checks else "WARN"
    tables = _build_tables(checks, project)
    return WoodCheckSummary(
        element_checks=tuple(checks),
        warnings=tuple(warnings),
        max_ratio=max_ratio,
        status=status,
        tables=tables,
    )


def summarize_wood_checks(mdl, project: ProjectDefinition):
    return build_wood_check_summary(mdl, project)


def _load_cases_to_check(mdl, project, warnings):
    requested = project.design_checks.wood.load_cases
    available = tuple(mdl.lcs)
    if not requested:
        warnings.append("No wood check load_cases were specified; all analysis load cases were checked.")
        return available

    out = []
    for lc in requested:
        if lc in available:
            out.append(lc)
        else:
            warnings.append("Wood check load case {0} is not in the solved model.".format(lc))
    if not out:
        warnings.append("No requested wood check load cases were available; all analysis load cases were checked.")
        return available
    return tuple(out)


def _check_element(e, member_class, load_cases, load_case_indices, project, warnings):
    best = None
    for lc in load_cases:
        result = _check_element_load_case(e, member_class, lc, load_case_indices, project, warnings)
        if best is None or result.combined_ratio > best.combined_ratio:
            best = result
    return best


def _check_element_load_case(e, member_class, load_case, load_case_indices, project, warnings):
    clc = load_case_indices.get(load_case, 0)
    allowable = _allowable_for_element(e, project, warnings)
    demand = _demand_for_load_case(e, load_case, clc)

    axial_ratio = _axial_ratio(demand.axial, allowable, member_class.kind)
    bending_ratio = _bending_ratio(e, demand, allowable)
    shear_ratio = _shear_ratio(e, demand, allowable)
    deflection_ratio = _deflection_ratio(e, demand.deflection, project)

    if member_class.kind == "brace":
        combined_ratio = axial_ratio
    else:
        combined_ratio = axial_ratio + bending_ratio
    if deflection_ratio is not None:
        combined_ratio = max(combined_ratio, deflection_ratio)
    combined_ratio = max(combined_ratio, shear_ratio)

    return WoodElementCheck(
        element_id=e.id,
        member_class=member_class.name,
        kind=member_class.kind,
        section=e.sec.name,
        material=e.sec.mat.name,
        governing_load_case=load_case,
        axial_ratio=axial_ratio,
        bending_ratio=bending_ratio,
        shear_ratio=shear_ratio,
        deflection_ratio=deflection_ratio,
        combined_ratio=combined_ratio,
        status="OK" if combined_ratio <= 1.0 else "NG",
        demand=demand,
    )


def _demand_for_load_case(e, load_case, clc):
    f = e.forces[:, clc]
    axial = max(abs(float(f[0])), abs(float(f[6])))
    shear_y = max(abs(float(f[1])), abs(float(f[7])))
    shear_z = max(abs(float(f[2])), abs(float(f[8])))
    moment_y = max(abs(float(f[4])), abs(float(f[10])), abs(float(f[12])))
    moment_z = max(abs(float(f[5])), abs(float(f[11])), abs(float(f[13])))
    return WoodCheckDemand(
        load_case=load_case,
        axial=axial,
        shear_y=shear_y,
        shear_z=shear_z,
        moment_y=moment_y,
        moment_z=moment_z,
        deflection=_element_deflection(e, clc),
    )


def _allowable_for_element(e, project, warnings):
    configured = project.design_checks.wood.allowable_stresses
    if _has_all_allowables(configured):
        return _scale_allowables(configured)

    fy = max(0.0, getattr(e.sec.mat, "fy", 0.0))
    if fy <= 0.0:
        warnings.append(
            "Element {0} has no configured wood allowables and material Fy is zero.".format(e.id)
        )
        return WoodAllowableStresses()

    warnings.append(
        "Wood allowables are incomplete; element {0} used material Fy with shear=0.1*Fy.".format(e.id)
    )
    return WoodAllowableStresses(
        bending=fy,
        shear=0.1 * fy,
        compression=fy,
        tension=fy,
    )


def _has_all_allowables(allowable):
    return (
        allowable.bending > 0.0
        and allowable.shear > 0.0
        and allowable.compression > 0.0
        and allowable.tension > 0.0
    )


def _scale_allowables(allowable):
    return WoodAllowableStresses(
        bending=allowable.bending * STRESS_UNIT,
        shear=allowable.shear * STRESS_UNIT,
        compression=allowable.compression * STRESS_UNIT,
        tension=allowable.tension * STRESS_UNIT,
    )


def _axial_ratio(axial, allowable, kind):
    limit = min(_positive_or_inf(allowable.compression), _positive_or_inf(allowable.tension))
    if kind == "brace":
        limit = _positive_or_inf(allowable.tension)
    return _ratio(axial, limit)


def _bending_ratio(e, demand, allowable):
    return _ratio(demand.moment_y / _positive_or_inf(e.sec.Wy), allowable.bending) + _ratio(
        demand.moment_z / _positive_or_inf(e.sec.Wz),
        allowable.bending,
    )


def _shear_ratio(e, demand, allowable):
    shear_y_ratio = _ratio(demand.shear_y / _positive_or_inf(e.sec.Asy), allowable.shear)
    shear_z_ratio = _ratio(demand.shear_z / _positive_or_inf(e.sec.Asz), allowable.shear)
    return max(shear_y_ratio, shear_z_ratio)


def _deflection_ratio(e, deflection, project):
    limit_ratio = project.design_checks.wood.deflection_limit_ratio
    if limit_ratio <= 0.0 or deflection is None:
        return None
    allowable = e.len / limit_ratio
    return _ratio(deflection, allowable)


def _element_deflection(e, clc):
    ndisps = getattr(e, "ndisps", None)
    if ndisps is None:
        return None
    ui = [float(ndisps[0, clc]), float(ndisps[1, clc]), float(ndisps[2, clc])]
    uj = [float(ndisps[6, clc]), float(ndisps[7, clc]), float(ndisps[8, clc])]
    du = [uj[i] - ui[i] for i in range(3)]
    axis = _element_axis(e)
    axial = sum(du[i] * axis[i] for i in range(3))
    transverse_sq = max(0.0, sum(v * v for v in du) - axial * axial)
    return math.sqrt(transverse_sq)


def _element_axis(e):
    length = max(getattr(e, "len", 0.0), DEFAULT_TOLERANCE)
    return (
        (e.n1.x - e.n0.x) / length,
        (e.n1.y - e.n0.y) / length,
        (e.n1.z - e.n0.z) / length,
    )


def _positive_or_inf(value):
    return value if value > DEFAULT_TOLERANCE else float("inf")


def _ratio(demand, capacity):
    if capacity <= DEFAULT_TOLERANCE or math.isinf(demand):
        return 0.0
    return max(0.0, demand) / capacity


def _build_tables(checks, project):
    checks_by_class = {}
    for check in checks:
        checks_by_class.setdefault(check.member_class, []).append(check)

    return WoodCheckTables(
        element_checks=tuple(_check_to_dict(c) for c in checks),
        member_classes=tuple(
            {
                "name": member_class.name,
                "kind": member_class.kind,
                "checked_count": len(checks_by_class.get(member_class.name, [])),
                "max_ratio": max(
                    [c.combined_ratio for c in checks_by_class.get(member_class.name, [])] + [0.0]
                ),
                "status": "OK"
                if max([c.combined_ratio for c in checks_by_class.get(member_class.name, [])] + [0.0]) <= 1.0
                else "NG",
            }
            for member_class in project.member_classes
            if member_class.kind in CHECKED_MEMBER_KINDS
        ),
    )


def _check_to_dict(check):
    return {
        "element_id": check.element_id,
        "member_class": check.member_class,
        "kind": check.kind,
        "section": check.section,
        "material": check.material,
        "governing_load_case": check.governing_load_case,
        "axial_ratio": check.axial_ratio,
        "bending_ratio": check.bending_ratio,
        "shear_ratio": check.shear_ratio,
        "deflection_ratio": check.deflection_ratio,
        "combined_ratio": check.combined_ratio,
        "status": check.status,
        "demand": {
            "load_case": check.demand.load_case,
            "axial": check.demand.axial,
            "shear_y": check.demand.shear_y,
            "shear_z": check.demand.shear_z,
            "moment_y": check.demand.moment_y,
            "moment_z": check.demand.moment_z,
            "deflection": check.demand.deflection,
        },
    }
