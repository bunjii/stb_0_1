"""Wind load generation: velocity pressure, story forces, diaphragm DLOD."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import common

from stb_loads.story import (
    diaphragm_area_m2,
    diaphragm_floor_z,
    resolve_diaphragm_story,
    sorted_stories,
    story_mass_height,
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


def _intersect_height(z_bottom: float, z_top: float, story) -> Optional[Tuple[float, float, float]]:
    z_lo = max(z_bottom, story.elevation)
    z_hi = min(z_top, story.elevation + story.height)
    if z_hi - z_lo <= common.PRES_ZERO:
        return None
    return z_lo, z_hi, z_hi - z_lo


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


def _diaphragm_story_map(project: ProjectDefinition) -> Dict[str, int]:
    return {d.story: d.diaphragm_id for d in project.load_conditions.diaphragms}


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
    stories = sorted_stories(project.stories)
    diap_by_story = _diaphragm_story_map(project)
    case_map = _case_by_id(wind)
    mode_warnings, blocked_surfaces = _validate_surface_output_modes(wind, case_map)
    warnings.extend(mode_warnings)

    case_summaries: List[WindCaseSummary] = []
    surface_summaries: List[WindSurfaceSummary] = []
    contributions: List[WindSurfaceStoryContribution] = []
    story_buckets: Dict[Tuple[int, str], Dict[str, float]] = {}

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

        if case.diaphragm_input_mode not in _DIAPHRAGM_OUTPUT_MODES.union(_MEMBER_OUTPUT_MODES):
            continue

        building_h = resolve_building_height_m(case, project.stories)
        gf, _ = resolve_wind_gf(case, building_h)

        for story in stories:
            hit = _intersect_height(surf.z_bottom, surf.z_top, story)
            if hit is None:
                continue
            z_lo, z_hi, seg_h = hit
            z_ref = 0.5 * (z_lo + z_hi)
            trib_area = seg_h * surf.width
            _, w = _pressure_at_z(z_ref, case, case.roughness_category, building_h, cf, gf)
            force = story_force_kN(w, trib_area)

            contributions.append(WindSurfaceStoryContribution(
                wind_case_id=case.case_id,
                story=story.name,
                z_bottom=z_lo,
                z_top=z_hi,
                z_ref=z_ref,
                surface_id=surf.surface_id,
                surface_name=surf.name,
                surface_role=surf.surface_role,
                cf=cf,
                tributary_area_m2=trib_area,
                pressure_w_N_m2=w,
                force_kN=force,
            ))

            key = (case.case_id, story.name)
            bucket = story_buckets.setdefault(key, {
                "f_story_kN": 0.0,
                "trib_area_m2": 0.0,
                "windward_kN": 0.0,
                "leeward_kN": 0.0,
                "z_bottom": z_lo,
                "z_top": z_hi,
                "z_ref": story_mass_height(story),
            })
            bucket["f_story_kN"] += force
            bucket["trib_area_m2"] += trib_area
            if surf.surface_role == "LEEWARD":
                bucket["leeward_kN"] += force
            elif surf.surface_role == "WINDWARD":
                bucket["windward_kN"] += force
            bucket["z_bottom"] = min(bucket["z_bottom"], z_lo)
            bucket["z_top"] = max(bucket["z_top"], z_hi)

    story_forces: List[WindStoryForce] = []
    diap_accum: Dict[Tuple[int, int, int], Dict[str, float]] = {}

    for (case_id, story_name), bucket in sorted(story_buckets.items()):
        case = case_map[case_id]
        diap_id = diap_by_story.get(story_name)
        emit_dlod = case.diaphragm_input_mode in _DIAPHRAGM_OUTPUT_MODES and diap_id is not None
        story_forces.append(WindStoryForce(
            wind_case_id=case_id,
            story=story_name,
            z_bottom=bucket["z_bottom"],
            z_top=bucket["z_top"],
            z_ref=bucket["z_ref"],
            f_story_kN=bucket["f_story_kN"],
            tributary_wall_area_m2=bucket["trib_area_m2"],
            windward_force_kN=bucket["windward_kN"],
            leeward_force_kN=bucket["leeward_kN"],
            target_diaphragm_id=diap_id,
            output_to_dlod=emit_dlod,
        ))
        if emit_dlod and diap_id is not None:
            key = (case_id, diap_id, case.load_case)
            diap_accum[key] = {
                "f_story_kN": bucket["f_story_kN"],
                "trib_area_m2": bucket["trib_area_m2"],
                "story": story_name,
                "z_ref": bucket["z_ref"],
                "eccentricity_e_m": None,
            }

    diaphragm_loads: List[WindDiaphragmLoad] = []
    case_summary_map = {c.case_id: c for c in case_summaries}
    for (case_id, diap_id, lc), bucket in sorted(diap_accum.items()):
        case = case_summary_map[case_id]
        area = diaphragm_area_m2(mdl, diap_id)
        f_story = bucket["f_story_kN"]
        p_area = uniform_diaphragm_area_load_kN_m2(f_story, area)
        floor_z = diaphragm_floor_z(mdl, diap_id)
        story_name = bucket["story"]
        if not story_name and floor_z is not None:
            story_name = resolve_diaphragm_story(
                diap_id, floor_z, project.stories,
                {d.diaphragm_id: d.story for d in project.load_conditions.diaphragms},
                warnings,
            )
        ecc = bucket.get("eccentricity_e_m")
        mz = compute_story_torsion_mz_knm(f_story, ecc) if ecc is not None else None
        diaphragm_loads.append(WindDiaphragmLoad(
            wind_case_id=case_id,
            load_case=lc,
            diaphragm_id=diap_id,
            story=story_name,
            direction=case.direction,
            axis=case.axis,
            sign=case.sign,
            load_level_m=floor_z if floor_z is not None else bucket["z_ref"],
            input_mode=case.diaphragm_input_mode,
            f_story_kN=f_story,
            diaphragm_area_m2=area,
            area_load_kN_m2=p_area,
            tributary_wall_area_m2=bucket["trib_area_m2"],
            eccentricity_e_m=ecc,
            mz_knm=mz,
        ))

    return WindDistributionResult(
        cases=tuple(case_summaries),
        surfaces=tuple(surface_summaries),
        surface_contributions=tuple(contributions),
        story_forces=tuple(story_forces),
        diaphragm_loads=tuple(diaphragm_loads),
        warnings=tuple(warnings),
    )


def total_wind_generated_kN(result: WindDistributionResult, wind_case_id: Optional[int] = None) -> float:
    total = 0.0
    for sf in result.story_forces:
        if wind_case_id is not None and sf.wind_case_id != wind_case_id:
            continue
        total += sf.f_story_kN
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
