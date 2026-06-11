import math

from dataclasses import dataclass, field

from typing import Dict, List, Optional, Sequence, Tuple



import common



from stb_loads.load_cases import resolve_seismic_directions

from stb_loads.mass_level import (
    build_mass_level_summaries,
    build_mass_levels_from_seismic_masses,
    resolve_base_story_name,
)

from stb_loads.story import (

    diaphragm_area_m2,

    diaphragm_floor_z,

    resolve_diaphragm_story,

    sorted_stories,

)

from stb_loads.weight import WeightAggregationResult, aggregate_story_weights

from stb_project import (
    DEFAULT_SEISMIC_RT,
    DEFAULT_SEISMIC_STEEL_RATIO_ALPHA,
    DEFAULT_SEISMIC_TC,
    LoadConditionSettings,
    ProjectDefinition,
    SeismicLoadSettings,
    resolve_seismic_c0_z,
)





@dataclass(frozen=True)

class StorySeismicSummary:

    story_name: str

    weight_kN: float

    w_supported_above_kN: float

    mass_height_m: float

    beta: float

    ai: float

    qi_kN: float

    fi_kN: float

    ci_story: float = 0.0

    is_base_level: bool = False

    output_dlod: bool = True

    mass_role: Optional[str] = None





@dataclass(frozen=True)

class DiaphragmSeismicLoad:

    diaphragm_id: int

    story_name: str

    load_case: int

    axis: str

    sign: int

    area_m2: float

    fi_kN: float

    pressure_kN_m2: float





@dataclass

class SeismicDistributionResult:

    ci: float

    ci_input: float

    c0: float

    z: float

    z_is_default: bool

    rt: float
    design_period_s: float
    tc: float

    base_level: str

    base_mass_policy: str

    total_weight_kN: float

    base_shear_kN: float

    q1_kN: float

    fi_all_mass_levels_kN: float

    fi_dlod_output_kN: float

    report_base_mass_policy: str

    num_seismic_directions: int

    stories: Tuple[StorySeismicSummary, ...]

    diaphragm_loads: Tuple[DiaphragmSeismicLoad, ...]

    weight_result: WeightAggregationResult

    warnings: Tuple[str, ...] = field(default_factory=tuple)





def compute_alpha_ratios(weights_kN: Sequence[float]) -> Tuple[float, ...]:

    total_w = sum(weights_kN)

    if total_w <= common.PRES_ZERO:

        return tuple(1.0 for _ in weights_kN)

    alphas = []

    for i in range(len(weights_kN)):

        alphas.append(sum(weights_kN[j] for j in range(i, len(weights_kN))) / total_w)

    return tuple(alphas)


def compute_w_supported_above(weights_kN: Sequence[float]) -> Tuple[float, ...]:
    """Cumulative weight from story index i upward (alpha_i numerator)."""
    n = len(weights_kN)
    return tuple(sum(weights_kN[j] for j in range(i, n)) for i in range(n))


def compute_ai_coefficients(

    weights_kN: Sequence[float],

    heights_m: Sequence[float],

    design_period_s: float,

) -> Tuple[float, ...]:

    n = len(weights_kN)

    if n == 0:

        return tuple()

    alphas = compute_alpha_ratios(weights_kN)

    t = max(0.0, float(design_period_s))

    c = (2.0 * t) / (1.0 + 3.0 * t) if t > common.PRES_ZERO else 0.0

    ai = []

    for a in alphas:

        if a <= common.PRES_ZERO:

            ai.append(1.0)

            continue

        ai.append(1.0 + (1.0 / math.sqrt(a) - a) * c)

    return tuple(ai)





def compute_story_forces(

    weights_kN: Sequence[float],

    ai: Sequence[float],

    c0: float,

    z: float,

    rt: float,

) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:

    total_w = sum(weights_kN)

    if total_w <= common.PRES_ZERO:

        empty = tuple(0.0 for _ in weights_kN)

        return empty, empty

    qi = []

    ci_stories = []

    for i in range(len(weights_kN)):

        ci_i = z * rt * ai[i] * c0

        ci_stories.append(ci_i)

        cumulative_w = sum(weights_kN[j] for j in range(i, len(weights_kN)))

        qi.append(ci_i * cumulative_w)

    return tuple(qi), tuple(ci_stories)





def compute_story_seismic_forces(qi_kN: Sequence[float]) -> Tuple[float, ...]:

    """Story seismic force Fi = Qi - Q(i+1); top story Fi = Qi."""



    n = len(qi_kN)

    if n == 0:

        return tuple()

    out = []

    for i in range(n):

        q_above = qi_kN[i + 1] if i + 1 < n else 0.0

        out.append(qi_kN[i] - q_above)

    return tuple(out)


def compute_rt_from_period(period_s: float, tc: float) -> float:
    t = max(0.0, float(period_s))
    tc = max(common.PRES_ZERO, float(tc))
    if t < tc:
        return 1.0
    if t < 2.0 * tc:
        return 1.0 - 0.2 * ((t / tc) - 1.0)
    return 1.6 * tc / t


def resolve_non_modal_rt(
    seismic: SeismicLoadSettings,
    project_stories,
    warnings: list,
) -> Tuple[float, float, float]:
    h_auto = 0.0
    if project_stories:
        z_min = min(s.elevation for s in project_stories)
        z_top = max((s.elevation + s.height) for s in project_stories)
        h_auto = max(0.0, z_top - z_min)

    h = seismic.height_m if seismic.height_m is not None else h_auto
    alpha = seismic.steel_ratio_alpha if seismic.steel_ratio_alpha is not None else DEFAULT_SEISMIC_STEEL_RATIO_ALPHA
    tc = seismic.tc if seismic.tc is not None else DEFAULT_SEISMIC_TC

    if seismic.design_period_s is not None:
        period_s = seismic.design_period_s
    else:
        period_s = (0.02 + 0.01 * alpha) * h
    if period_s <= common.PRES_ZERO:
        period_s = 0.0
        warnings.append("Design period was non-positive; Rt defaults to 1.0.")

    rt_auto = compute_rt_from_period(period_s, tc)
    if seismic.rt is not None:
        rt = seismic.rt
        if rt < 0.75 * rt_auto:
            warnings.append(
                "Seismic Rt override ({0:.3f}) is below 3/4 of auto Rt ({1:.3f}); check applicability.".format(
                    rt, rt_auto
                )
            )
    else:
        rt = rt_auto
    if rt <= 0.0:
        rt = DEFAULT_SEISMIC_RT
        warnings.append("Rt was non-positive; 1.0 was applied.")
    return rt, period_s, tc





def compute_seismic_distribution(

    mdl,

    project: ProjectDefinition,

    load_conditions: Optional[LoadConditionSettings] = None,

) -> SeismicDistributionResult:

    load_conditions = load_conditions or project.load_conditions

    seismic = load_conditions.seismic

    c0, z, z_is_default = resolve_seismic_c0_z(seismic)



    weight_result = aggregate_story_weights(mdl, project, load_conditions)

    warnings = list(weight_result.warnings)



    project_stories = sorted_stories(project.stories)

    raw_weights = {sw.story_name: sw.weight_kN for sw in weight_result.stories}

    assignments = {d.diaphragm_id: d.story for d in load_conditions.diaphragms}

    diaphragm_stories = set(assignments.values())



    base_level = resolve_base_story_name(seismic, project_stories)
    rt, design_period_s, tc = resolve_non_modal_rt(seismic, project_stories, warnings)

    seismic_masses = load_conditions.seismic_masses
    if seismic_masses:
        mass_levels = build_mass_levels_from_seismic_masses(
            seismic_masses,
            raw_weights,
            project_stories,
            warnings,
        )
    else:
        mass_levels = build_mass_level_summaries(
            raw_weights,
            project_stories,
            seismic,
            diaphragm_stories,
            warnings,
        )

    alpha_weights = [
        ml.weight_kN if ml.include_in_alpha_denominator else 0.0
        for ml in mass_levels
    ]
    weights = alpha_weights
    heights = [ml.mass_height_m for ml in mass_levels]
    names = [ml.story_name for ml in mass_levels]



    ai = compute_ai_coefficients(weights, heights, design_period_s)

    qi, ci_stories = compute_story_forces(weights, ai, c0, z, rt)

    fi = compute_story_seismic_forces(qi)



    betas = list(compute_alpha_ratios(weights))

    w_supported = list(compute_w_supported_above(weights))



    story_summaries = tuple(

        StorySeismicSummary(

            story_name=names[i],

            weight_kN=weights[i],

            w_supported_above_kN=w_supported[i],

            mass_height_m=heights[i],

            beta=betas[i],

            ai=ai[i],

            qi_kN=qi[i],

            fi_kN=fi[i],

            ci_story=ci_stories[i],

            is_base_level=mass_levels[i].is_base_level,

            output_dlod=mass_levels[i].output_dlod,

            mass_role=mass_levels[i].mass_role,

        )

        for i in range(len(names))

    )



    fi_by_story = {s.story_name: s.fi_kN for s in story_summaries}

    output_dlod_by_story = {s.story_name: s.output_dlod for s in story_summaries}

    diap_ids = sorted({d.id for d in getattr(mdl, "diaps", [])})

    allowed_diap_ids = None
    diap_story_for_fi: Dict[int, str] = {}
    if seismic_masses:
        allowed_diap_ids = set()
        for entry in seismic_masses:
            if entry.generate_diaphragm_load and entry.application_diaphragm is not None:
                allowed_diap_ids.add(entry.application_diaphragm)
                if entry.story:
                    diap_story_for_fi[entry.application_diaphragm] = entry.story

    area_by_story: Dict[str, float] = {}

    diap_meta: List[Tuple[int, str, float]] = []

    for diap_id in diap_ids:

        area = diaphragm_area_m2(mdl, diap_id)

        if area <= common.PRES_ZERO:

            warnings.append("Diaphragm {0}: area is zero; skipped for seismic DLOD.".format(diap_id))

            continue

        floor_z = diaphragm_floor_z(mdl, diap_id)

        if floor_z is None:

            warnings.append("Diaphragm {0}: floor elevation unknown; skipped.".format(diap_id))

            continue

        story = resolve_diaphragm_story(

            diap_id, floor_z, project_stories, assignments, warnings

        )

        if not story:

            continue

        if allowed_diap_ids is not None and diap_id not in allowed_diap_ids:
            continue

        if not output_dlod_by_story.get(story, True):

            if allowed_diap_ids is None:
                warnings.append(

                    "Diaphragm {0} at base level '{1}' skipped for DLOD (base_mass_policy).".format(

                        diap_id, story

                    )

                )

            continue

        area_by_story[story] = area_by_story.get(story, 0.0) + area

        diap_meta.append((diap_id, story, area))



    diaphragm_loads = []

    directions, dir_warnings = resolve_seismic_directions(mdl, seismic.directions)

    warnings.extend(dir_warnings)

    num_directions = max(1, len(directions))

    if not directions:

        warnings.append("No seismic output directions were resolved; DLOD generation skipped.")



    for direction in directions:

        for diap_id, story, area in diap_meta:

            fi_story = diap_story_for_fi.get(diap_id, story)
            story_f = fi_by_story.get(fi_story, 0.0)

            story_area = area_by_story.get(story, 0.0)

            if story_area <= common.PRES_ZERO or story_f <= common.PRES_ZERO:

                continue

            share_f = story_f * (area / story_area)

            pressure = share_f / area

            if direction.axis == "x":

                px, py = direction.sign * pressure, 0.0

            elif direction.axis == "y":

                px, py = 0.0, direction.sign * pressure

            else:

                warnings.append("Unsupported seismic axis: " + direction.axis)

                continue



            diaphragm_loads.append(DiaphragmSeismicLoad(

                diaphragm_id=diap_id,

                story_name=story,

                load_case=direction.load_case,

                axis=direction.axis,

                sign=direction.sign,

                area_m2=area,

                fi_kN=share_f,

                pressure_kN_m2=abs(pressure),

            ))



    assigned_f = sum(

        fi_by_story.get(story, 0.0)

        for story in area_by_story

        if output_dlod_by_story.get(story, True)

    )

    total_f = sum(s.fi_kN for s in story_summaries if s.output_dlod)

    unassigned = total_f - assigned_f

    if unassigned > max(1.0e-3, total_f * 1.0e-6):

        warnings.append(

            "Fi for mass levels without diaphragms totals {0:.3f} kN; assign diaphragms or enter loads manually.".format(

                unassigned

            )

        )



    total_mass_weight = sum(
        ml.weight_kN for ml in mass_levels if ml.include_in_total_seismic_weight
    )

    q1 = qi[0] if qi else 0.0
    fi_all = sum(s.fi_kN for s in story_summaries)
    fi_dlod = sum(s.fi_kN for s in story_summaries if s.output_dlod)
    report_policy = (
        "BASE_MASS_NO_DLOD"
        if any(s.mass_role == "BASE_MASS" for s in story_summaries)
        else seismic.base_mass_policy
    )

    return SeismicDistributionResult(

        ci=c0 * z * rt,

        ci_input=seismic.ci,

        c0=c0,

        z=z,

        z_is_default=z_is_default,

        rt=rt,
        design_period_s=design_period_s,
        tc=tc,

        base_level=base_level,

        base_mass_policy=seismic.base_mass_policy,

        total_weight_kN=total_mass_weight,

        base_shear_kN=q1,

        q1_kN=q1,

        fi_all_mass_levels_kN=fi_all,

        fi_dlod_output_kN=fi_dlod,

        report_base_mass_policy=report_policy,

        num_seismic_directions=num_directions,

        stories=story_summaries,

        diaphragm_loads=tuple(diaphragm_loads),

        weight_result=weight_result,

        warnings=tuple(warnings),

    )





def generate_dlod_records(result: SeismicDistributionResult):

    from diaphragm import DiaphragmLoad



    records = []

    for item in result.diaphragm_loads:

        px = item.pressure_kN_m2 * 1.0e3 if item.axis == "x" else 0.0

        py = item.pressure_kN_m2 * 1.0e3 if item.axis == "y" else 0.0

        if item.sign < 0:

            px = -px

            py = -py

        records.append(DiaphragmLoad(

            item.diaphragm_id,

            item.load_case,

            DiaphragmLoad.AREA,

            px,

            py,

            _source="SEISMIC",

        ))

    return records


