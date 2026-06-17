"""Wind load generation: velocity pressure, story forces, diaphragm DLOD."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import common

from stb_loads.story import (
    diaphragm_area_m2,
    diaphragm_floor_z,
)
from stb_loads.wind_tributary import (
    aggregate_case_by_tributary,
    build_diaphragm_levels,
    resolve_base_support_context,
    validate_tributary_conservation,
)
from stb_project import (
    DEFAULT_WIND_DIAPHRAGM_INPUT_MODE,
    LoadConditionSettings,
    ProjectDefinition,
    WindLoadCaseSettings,
    WindLoadSettings,
    WindSurfaceSettings,
    direction_to_axis_sign,
    resolve_building_height_m,
    resolve_wind_gf,
    roughness_params,
)

WIND_NOTICE = (
    "この風荷重は、外壁面に作用する風圧力から求めた階風力を、建物全体解析用として"
    "ダイアフラム面に等価入力したものです。床面に実際に風圧が作用するという意味ではありません。"
    "外壁材、間柱、耐風梁、大梁弱軸方向など、風を直接受ける局部部材の検討は別途行ってください。"
)

_DIAPHRAGM_OUTPUT_MODES = frozenset({
    "DIAPHRAGM_DIRECT",
    "DIAPHRAGM_UNIFORM",
    "DIAPHRAGM_FORCE_WITH_TORSION",
})
_MEMBER_OUTPUT_MODES = frozenset({"EDGE_OR_MEMBER_LOAD"})


@dataclass(frozen=True)
class WindCaseSummary:
    case_id: int
    name: str
    direction: str
    axis: str
    sign: int
    load_case: int
    v0: float
    roughness_category: str
    building_height_H: float
    zb: float
    zg: float
    alpha: float
    er: float
    gf: float
    gf_is_auto: bool
    e_factor: float
    q_N_m2: float
    cf_default: float
    w_default_N_m2: float
    pressure_mode: str
    use_kz: bool
    diaphragm_input_mode: str


@dataclass(frozen=True)
class WindSurfaceSummary:
    surface_id: int
    name: str
    wind_case_id: int
    face_direction: str
    surface_role: str
    z_bottom: float
    z_top: float
    width: float
    gross_area_m2: float
    cf: float


@dataclass(frozen=True)
class WindSurfaceStoryContribution:
    """Per-surface story force before aggregation (windward / leeward components)."""
    wind_case_id: int
    story: str
    z_bottom: float
    z_top: float
    z_ref: float
    surface_id: int
    surface_name: str
    surface_role: str
    cf: float
    tributary_area_m2: float
    pressure_w_N_m2: float
    force_kN: float


@dataclass(frozen=True)
class WindStoryForce:
    """Net story resultant F_story from all wall surfaces on that level."""
    wind_case_id: int
    story: str
    z_bottom: float
    z_top: float
    z_ref: float
    f_story_kN: float
    tributary_wall_area_m2: float
    windward_force_kN: float
    leeward_force_kN: float
    target_diaphragm_id: Optional[int]
    output_to_dlod: bool


@dataclass(frozen=True)
class WindDiaphragmTributarySummary:
    wind_case_id: int
    diaphragm_id: int
    story: str
    diaphragm_level_m: float
    lower_adjacent_level_m: Optional[float]
    upper_adjacent_level_m: Optional[float]
    tributary_z_bottom: float
    tributary_z_top: float
    tributary_height: float
    exposed_width: float
    tributary_area_m2: float
    wind_pressure_w_N_m2: float
    story_wind_force_kN: float
    output_to_dlod: bool
    windward_force_kN: float = 0.0
    leeward_force_kN: float = 0.0


@dataclass(frozen=True)
class WindBaseWindForce:
    wind_case_id: int
    z_bottom: float
    z_top: float
    tributary_height: float
    tributary_area_m2: float
    wind_pressure_w_N_m2: float
    f_wind_to_base_kN: float


@dataclass(frozen=True)
class WindTributaryValidation:
    wind_case_id: int
    gross_wall_area_m2: float
    diaphragm_tributary_area_m2: float
    base_tributary_area_m2: float
    gross_wall_force_kN: float
    diaphragm_force_kN: float
    base_force_kN: float
    area_conservation_ok: bool
    force_conservation_ok: bool

    @property
    def conservation_ok(self) -> bool:
        return self.area_conservation_ok and self.force_conservation_ok


@dataclass(frozen=True)
class WindDiaphragmLoad:
    wind_case_id: int
    load_case: int
    diaphragm_id: int
    story: str
    direction: str
    axis: str
    sign: int
    load_level_m: float
    input_mode: str
    f_story_kN: float
    diaphragm_area_m2: float
    area_load_kN_m2: float
    tributary_wall_area_m2: float
    eccentricity_e_m: Optional[float] = None
    mz_knm: Optional[float] = None


@dataclass
class WindDistributionResult:
    cases: Tuple[WindCaseSummary, ...] = ()
    surfaces: Tuple[WindSurfaceSummary, ...] = ()
    surface_contributions: Tuple[WindSurfaceStoryContribution, ...] = ()
    story_forces: Tuple[WindStoryForce, ...] = ()
    diaphragm_tributary_rows: Tuple[WindDiaphragmTributarySummary, ...] = ()
    base_wind_forces: Tuple[WindBaseWindForce, ...] = ()
    tributary_validations: Tuple[WindTributaryValidation, ...] = ()
    diaphragm_loads: Tuple[WindDiaphragmLoad, ...] = ()
    warnings: Tuple[str, ...] = ()


def compute_er(height_m: float, roughness_category: str) -> float:
    rp = roughness_params(roughness_category)
    h = max(0.0, float(height_m))
    if h <= rp.zb:
        return 1.7 * math.pow(rp.zb / rp.zg, rp.alpha)
    return 1.7 * math.pow(h / rp.zg, rp.alpha)


def compute_kz(z_m: float, building_height_m: float, roughness_category: str) -> float:
    rp = roughness_params(roughness_category)
    h = max(rp.zb, float(building_height_m))
    z = max(0.0, float(z_m))
    if z <= rp.zb:
        return 1.0
    if z <= h:
        return math.pow(z / h, 2.0 * rp.alpha)
    return math.pow(h / z, 2.0 * rp.alpha)


def compute_e_factor(er: float, gf: float) -> float:
    return float(er) ** 2 * float(gf)


def compute_q_N_m2(v0: float, er: float, gf: float) -> float:
    e = compute_e_factor(er, gf)
    return 0.6 * e * float(v0) ** 2


def compute_w_N_m2(cf: float, q_N_m2: float) -> float:
    return float(cf) * float(q_N_m2)


def story_force_kN(w_N_m2: float, area_m2: float) -> float:
    return w_N_m2 * area_m2 / 1000.0


def uniform_diaphragm_area_load_kN_m2(f_story_kN: float, diaphragm_area_m2: float) -> float:
    """MVP: DLOD_area_load = F_story / diaphragm_area."""
    if diaphragm_area_m2 <= common.PRES_ZERO:
        return 0.0
    return f_story_kN / diaphragm_area_m2


def compute_story_torsion_mz_knm(f_story_kN: float, eccentricity_e_m: float) -> float:
    """Future DIAPHRAGM_FORCE_WITH_TORSION: Mz = F_story * e."""
    return f_story_kN * float(eccentricity_e_m)


def _pressure_at_z(
    z_ref: float,
    case: WindLoadCaseSettings,
    roughness: str,
    building_h: float,
    cf: float,
    gf: float,
) -> Tuple[float, float]:
    if case.pressure_mode == "STORY_HEIGHT_KZ" and case.use_kz:
        kz = compute_kz(z_ref, building_h, roughness)
        er_building = compute_er(building_h, roughness)
        e = compute_e_factor(er_building, gf)
        q = 0.6 * e * case.v0 ** 2 * kz
    elif case.pressure_mode == "STORY_HEIGHT_KZ":
        er = compute_er(z_ref, roughness)
        q = compute_q_N_m2(case.v0, er, gf)
    else:
        er = compute_er(building_h, roughness)
        q = compute_q_N_m2(case.v0, er, gf)
    return q, compute_w_N_m2(cf, q)


def _case_by_id(settings: WindLoadSettings) -> Dict[int, WindLoadCaseSettings]:
    return {c.case_id: c for c in settings.cases}


def _validate_surface_output_modes(
    wind: WindLoadSettings,
    case_map: Dict[int, WindLoadCaseSettings],
) -> Tuple[List[str], set]:
    warnings: List[str] = []
    blocked: set = set()
    surface_auto_mode: Dict[int, str] = {}

    for surf in wind.surfaces:
        case = case_map.get(surf.wind_case_id)
        if case is None:
            continue
        mode = case.diaphragm_input_mode
        sid = surf.surface_id
        if sid not in surface_auto_mode:
            surface_auto_mode[sid] = mode
            continue
        prev = surface_auto_mode[sid]
        diaphragm_vs_member = (
            (prev in _DIAPHRAGM_OUTPUT_MODES and mode in _MEMBER_OUTPUT_MODES)
            or (prev in _MEMBER_OUTPUT_MODES and mode in _DIAPHRAGM_OUTPUT_MODES)
        )
        if diaphragm_vs_member:
            warnings.append(
                "Wind surface {0} ({1}) is referenced by cases with conflicting "
                "diaphragm_input_mode ({2} vs {3}); automatic output skipped to "
                "avoid double counting.".format(sid, surf.name, prev, mode)
            )
            blocked.add(sid)
    return warnings, blocked


def compute_wind_distribution(
    mdl,
    project: ProjectDefinition,
    load_conditions: Optional[LoadConditionSettings] = None,
) -> WindDistributionResult:
    load_conditions = load_conditions or project.load_conditions
    wind = load_conditions.wind
    if not wind.cases:
        return WindDistributionResult()

    warnings: List[str] = []
    case_map = _case_by_id(wind)
    mode_warnings, blocked_surfaces = _validate_surface_output_modes(wind, case_map)
    warnings.extend(mode_warnings)

    case_summaries: List[WindCaseSummary] = []
    surface_summaries: List[WindSurfaceSummary] = []
    contributions: List[WindSurfaceStoryContribution] = []
    tributary_rows: List[WindDiaphragmTributarySummary] = []
    base_forces: List[WindBaseWindForce] = []
    tributary_validations: List[WindTributaryValidation] = []
    story_forces: List[WindStoryForce] = []
    diaphragm_loads: List[WindDiaphragmLoad] = []

    diap_levels = build_diaphragm_levels(mdl, project, warnings)
    z_base, base_fixed = resolve_base_support_context(project)
    if not diap_levels:
        warnings.append("No diaphragm levels resolved; wind tributary aggregation skipped.")

    for case in wind.cases:
        if case.diaphragm_input_mode == "EDGE_OR_MEMBER_LOAD":
            warnings.append(
                "Wind case '{0}' diaphragm_input_mode=EDGE_OR_MEMBER_LOAD: "
                "DLOD is not generated (local member loads are manual).".format(case.name)
            )
        elif case.diaphragm_input_mode == "DIAPHRAGM_FORCE_WITH_TORSION":
            warnings.append(
                "Wind case '{0}' diaphragm_input_mode=DIAPHRAGM_FORCE_WITH_TORSION: "
                "MVP applies uniform area load only; Mz torsion is not yet written to DLOD.".format(
                    case.name
                )
            )

        building_h = resolve_building_height_m(case, project.stories)
        gf, gf_auto = resolve_wind_gf(case, building_h)
        rp = roughness_params(case.roughness_category)
        er = compute_er(building_h, case.roughness_category)
        q = compute_q_N_m2(case.v0, er, gf)
        w_def = compute_w_N_m2(case.cf_default, q)
        axis, sign = direction_to_axis_sign(case.direction)

        case_summaries.append(WindCaseSummary(
            case_id=case.case_id,
            name=case.name,
            direction=case.direction,
            axis=axis,
            sign=sign,
            load_case=case.load_case,
            v0=case.v0,
            roughness_category=case.roughness_category,
            building_height_H=building_h,
            zb=rp.zb,
            zg=rp.zg,
            alpha=rp.alpha,
            er=er,
            gf=gf,
            gf_is_auto=gf_auto,
            e_factor=compute_e_factor(er, gf),
            q_N_m2=q,
            cf_default=case.cf_default,
            w_default_N_m2=w_def,
            pressure_mode=case.pressure_mode,
            use_kz=case.use_kz,
            diaphragm_input_mode=case.diaphragm_input_mode,
        ))

    for surf in wind.surfaces:
        case = case_map.get(surf.wind_case_id)
        if case is None:
            warnings.append(
                "Wind surface '{0}': unknown wind_case_id {1}.".format(surf.name, surf.wind_case_id)
            )
            continue
        if surf.surface_id in blocked_surfaces:
            continue

        cf = surf.cf if surf.cf is not None else case.cf_default
        gross_h = max(0.0, surf.z_top - surf.z_bottom)
        surface_summaries.append(WindSurfaceSummary(
            surface_id=surf.surface_id,
            name=surf.name,
            wind_case_id=surf.wind_case_id,
            face_direction=surf.face_direction,
            surface_role=surf.surface_role,
            z_bottom=surf.z_bottom,
            z_top=surf.z_top,
            width=surf.width,
            gross_area_m2=gross_h * surf.width,
            cf=cf,
        ))

    case_summary_map = {c.case_id: c for c in case_summaries}
    active_surfaces = [s for s in wind.surfaces if s.surface_id not in blocked_surfaces]
    for case in wind.cases:
        if case.diaphragm_input_mode not in _DIAPHRAGM_OUTPUT_MODES:
            continue
        if not diap_levels:
            continue

        building_h = resolve_building_height_m(case, project.stories)
        gf, _ = resolve_wind_gf(case, building_h)
        roughness = case.roughness_category

        def pressure_at_z(z_ref: float, cf_value: float) -> float:
            _, w = _pressure_at_z(z_ref, case, roughness, building_h, cf_value, gf)
            return w

        emit_dlod = True
        diap_buckets, base_bucket, raw_contribs, gross_force = aggregate_case_by_tributary(
            case,
            active_surfaces,
            diap_levels,
            z_base,
            base_fixed,
            pressure_at_z,
            emit_dlod,
        )

        ok, validation = validate_tributary_conservation(
            case.case_id,
            active_surfaces,
            diap_buckets,
            base_bucket,
            gross_force,
        )
        tributary_validations.append(WindTributaryValidation(
            wind_case_id=case.case_id,
            gross_wall_area_m2=validation["gross_wall_area_m2"],
            diaphragm_tributary_area_m2=validation["diaphragm_tributary_area_m2"],
            base_tributary_area_m2=validation["base_tributary_area_m2"],
            gross_wall_force_kN=validation["gross_wall_force_kN"],
            diaphragm_force_kN=validation["diaphragm_force_kN"],
            base_force_kN=validation["base_force_kN"],
            area_conservation_ok=validation["area_conservation_ok"],
            force_conservation_ok=validation["force_conservation_ok"],
        ))
        if not ok:
            warnings.append(
                "Wind case '{0}': tributary conservation check failed "
                "(area_ok={1}, force_ok={2}).".format(
                    case.name,
                    validation["area_conservation_ok"],
                    validation["force_conservation_ok"],
                )
            )

        for row in raw_contribs:
            z_ref = 0.5 * (row["z_bottom"] + row["z_top"])
            contributions.append(WindSurfaceStoryContribution(
                wind_case_id=row["wind_case_id"],
                story=row["story"],
                z_bottom=row["z_bottom"],
                z_top=row["z_top"],
                z_ref=z_ref,
                surface_id=row["surface_id"],
                surface_name=row["surface_name"],
                surface_role=row["surface_role"],
                cf=row["cf"],
                tributary_area_m2=row["tributary_area_m2"],
                pressure_w_N_m2=row["pressure_w_N_m2"],
                force_kN=row["force_kN"],
            ))

        if base_bucket is not None and base_bucket.f_wind_to_base_kN > common.PRES_ZERO:
            base_forces.append(WindBaseWindForce(
                wind_case_id=case.case_id,
                z_bottom=base_bucket.z_bottom,
                z_top=base_bucket.z_top,
                tributary_height=base_bucket.height,
                tributary_area_m2=base_bucket.tributary_area_m2,
                wind_pressure_w_N_m2=base_bucket.wind_pressure_w_N_m2,
                f_wind_to_base_kN=base_bucket.f_wind_to_base_kN,
            ))

        for bucket in diap_buckets.values():
            if bucket.f_story_kN <= common.PRES_ZERO and bucket.tributary_area_m2 <= common.PRES_ZERO:
                continue
            tributary_rows.append(WindDiaphragmTributarySummary(
                wind_case_id=bucket.wind_case_id,
                diaphragm_id=bucket.diaphragm_id,
                story=bucket.story,
                diaphragm_level_m=bucket.diaphragm_level,
                lower_adjacent_level_m=bucket.lower_adjacent_level,
                upper_adjacent_level_m=bucket.upper_adjacent_level,
                tributary_z_bottom=bucket.tributary_z_bottom,
                tributary_z_top=bucket.tributary_z_top,
                tributary_height=bucket.tributary_height,
                exposed_width=bucket.exposed_width,
                tributary_area_m2=bucket.tributary_area_m2,
                wind_pressure_w_N_m2=bucket.wind_pressure_w_N_m2,
                story_wind_force_kN=bucket.f_story_kN,
                output_to_dlod=bucket.output_to_dlod,
                windward_force_kN=bucket.windward_force_kN,
                leeward_force_kN=bucket.leeward_force_kN,
            ))
            story_forces.append(WindStoryForce(
                wind_case_id=bucket.wind_case_id,
                story=bucket.story,
                z_bottom=bucket.tributary_z_bottom,
                z_top=bucket.tributary_z_top,
                z_ref=bucket.diaphragm_level,
                f_story_kN=bucket.f_story_kN,
                tributary_wall_area_m2=bucket.tributary_area_m2,
                windward_force_kN=bucket.windward_force_kN,
                leeward_force_kN=bucket.leeward_force_kN,
                target_diaphragm_id=bucket.diaphragm_id,
                output_to_dlod=bucket.output_to_dlod,
            ))

            if not bucket.output_to_dlod:
                continue
            area = diaphragm_area_m2(mdl, bucket.diaphragm_id)
            f_story = bucket.f_story_kN
            p_area = uniform_diaphragm_area_load_kN_m2(f_story, area)
            floor_z = diaphragm_floor_z(mdl, bucket.diaphragm_id)
            summary = case_summary_map[bucket.wind_case_id]
            ecc = None
            mz = compute_story_torsion_mz_knm(f_story, ecc) if ecc is not None else None
            diaphragm_loads.append(WindDiaphragmLoad(
                wind_case_id=bucket.wind_case_id,
                load_case=summary.load_case,
                diaphragm_id=bucket.diaphragm_id,
                story=bucket.story,
                direction=summary.direction,
                axis=summary.axis,
                sign=summary.sign,
                load_level_m=floor_z if floor_z is not None else bucket.diaphragm_level,
                input_mode=case.diaphragm_input_mode,
                f_story_kN=f_story,
                diaphragm_area_m2=area,
                area_load_kN_m2=p_area,
                tributary_wall_area_m2=bucket.tributary_area_m2,
                eccentricity_e_m=ecc,
                mz_knm=mz,
            ))

    return WindDistributionResult(
        cases=tuple(case_summaries),
        surfaces=tuple(surface_summaries),
        surface_contributions=tuple(contributions),
        story_forces=tuple(story_forces),
        diaphragm_tributary_rows=tuple(tributary_rows),
        base_wind_forces=tuple(base_forces),
        tributary_validations=tuple(tributary_validations),
        diaphragm_loads=tuple(diaphragm_loads),
        warnings=tuple(warnings),
    )


def total_wind_generated_kN(result: WindDistributionResult, wind_case_id: Optional[int] = None) -> float:
    if result.tributary_validations:
        total = 0.0
        for row in result.tributary_validations:
            if wind_case_id is not None and row.wind_case_id != wind_case_id:
                continue
            total += row.gross_wall_force_kN
        return total
    total = 0.0
    for sf in result.story_forces:
        if wind_case_id is not None and sf.wind_case_id != wind_case_id:
            continue
        total += sf.f_story_kN
    return total


def total_base_wind_kN(result: WindDistributionResult, wind_case_id: Optional[int] = None) -> float:
    total = 0.0
    for row in result.base_wind_forces:
        if wind_case_id is not None and row.wind_case_id != wind_case_id:
            continue
        total += row.f_wind_to_base_kN
    return total


def total_dlod_output_kN(result: WindDistributionResult, wind_case_id: Optional[int] = None) -> float:
    total = 0.0
    for dl in result.diaphragm_loads:
        if wind_case_id is not None and dl.wind_case_id != wind_case_id:
            continue
        total += dl.f_story_kN
    return total


def generate_wind_dlod_records(result: WindDistributionResult):
    """MVP: TYPE=AREA uniform horizontal load = F_story / diaphragm_area."""
    from diaphragm import DiaphragmLoad

    records = []
    for item in result.diaphragm_loads:
        if item.input_mode not in _DIAPHRAGM_OUTPUT_MODES:
            continue
        px = item.area_load_kN_m2 * 1.0e3 if item.axis == "x" else 0.0
        py = item.area_load_kN_m2 * 1.0e3 if item.axis == "y" else 0.0
        if item.sign < 0:
            px = -px
            py = -py
        records.append(DiaphragmLoad(
            item.diaphragm_id,
            item.load_case,
            DiaphragmLoad.AREA,
            px,
            py,
            _source="WIND",
        ))
    return records
