import math
from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple

import common

from stb_loads.load_cases import resolve_seismic_directions
from stb_loads.mass_level import MassLevelSummary, build_mass_level_summaries, resolve_base_story_name
from stb_loads.story import (
    diaphragm_area_m2,
    diaphragm_floor_z,
    resolve_diaphragm_story,
    sorted_stories,
)
from stb_loads.weight import WeightAggregationResult, aggregate_story_weights
from stb_project import LoadConditionSettings, ProjectDefinition, SeismicLoadSettings, effective_seismic_ci


@dataclass(frozen=True)
class StorySeismicSummary:
    story_name: str
    weight_kN: float
    mass_height_m: float
    beta: float
    ai: float
    qi_kN: float
    fi_kN: float
    is_base_level: bool = False
    output_dlod: bool = True


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
    rt: float
    base_level: str
    base_mass_policy: str
    total_weight_kN: float
    base_shear_kN: float
    stories: Tuple[StorySeismicSummary, ...]
    diaphragm_loads: Tuple[DiaphragmSeismicLoad, ...]
    weight_result: WeightAggregationResult
    warnings: Tuple[str, ...] = field(default_factory=tuple)


def compute_ai_coefficients(
    weights_kN: Sequence[float],
    heights_m: Sequence[float],
) -> Tuple[float, ...]:
    n = len(weights_kN)
    if n == 0:
        return tuple()

    total_wh = sum(w * h for w, h in zip(weights_kN, heights_m))
    if total_wh <= common.PRES_ZERO:
        return tuple(1.0 for _ in range(n))

    betas = []
    for i in range(n):
        wh_upper = sum(weights_kN[j] * heights_m[j] for j in range(i, n))
        betas.append(wh_upper / total_wh)

    ai_raw = [0.5 + 0.5 * b for b in betas]
    total_w = sum(weights_kN)
    if total_w <= common.PRES_ZERO:
        return tuple(1.0 for _ in range(n))

    r = sum(w * a for w, a in zip(weights_kN, ai_raw)) / total_w
    if abs(r) < common.PRES_ZERO:
        return tuple(1.0 for _ in range(n))

    return tuple(a / r for a in ai_raw)


def compute_story_forces(
    weights_kN: Sequence[float],
    ai: Sequence[float],
    ci: float,
) -> Tuple[float, ...]:
    total_w = sum(weights_kN)
    if total_w <= common.PRES_ZERO:
        return tuple(0.0 for _ in weights_kN)

    v = ci * total_w
    denom = sum(a * w for a, w in zip(ai, weights_kN))
    if denom <= common.PRES_ZERO:
        return tuple(0.0 for _ in weights_kN)

    return tuple(v * (a * w) / denom for a, w in zip(ai, weights_kN))


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


def compute_seismic_distribution(
    mdl,
    project: ProjectDefinition,
    load_conditions: LoadConditionSettings = None,
) -> SeismicDistributionResult:
    load_conditions = load_conditions or project.load_conditions
    seismic = load_conditions.seismic
    ci_eff = effective_seismic_ci(seismic)
    if ci_eff <= 0.0:
        raise ValueError("load_conditions.seismic.ci must be positive")

    weight_result = aggregate_story_weights(mdl, project, load_conditions)
    warnings = list(weight_result.warnings)

    project_stories = sorted_stories(project.stories)
    raw_weights = {sw.story_name: sw.weight_kN for sw in weight_result.stories}
    assignments = {d.diaphragm_id: d.story for d in load_conditions.diaphragms}
    diaphragm_stories = set(assignments.values())

    base_level = resolve_base_story_name(seismic, project_stories)
    mass_levels = build_mass_level_summaries(
        raw_weights,
        project_stories,
        seismic,
        diaphragm_stories,
        warnings,
    )

    weights = [ml.weight_kN for ml in mass_levels]
    heights = [ml.mass_height_m for ml in mass_levels]
    names = [ml.story_name for ml in mass_levels]

    ai = compute_ai_coefficients(weights, heights)
    qi = compute_story_forces(weights, ai, ci_eff)
    fi = compute_story_seismic_forces(qi)

    total_wh = sum(w * h for w, h in zip(weights, heights))
    betas = []
    for i in range(len(weights)):
        if total_wh <= common.PRES_ZERO:
            betas.append(0.0)
        else:
            wh_upper = sum(weights[j] * heights[j] for j in range(i, len(weights)))
            betas.append(wh_upper / total_wh)

    story_summaries = tuple(
        StorySeismicSummary(
            story_name=names[i],
            weight_kN=weights[i],
            mass_height_m=heights[i],
            beta=betas[i],
            ai=ai[i],
            qi_kN=qi[i],
            fi_kN=fi[i],
            is_base_level=mass_levels[i].is_base_level,
            output_dlod=mass_levels[i].output_dlod,
        )
        for i in range(len(names))
    )

    fi_by_story = {s.story_name: s.fi_kN for s in story_summaries}
    output_dlod_by_story = {s.story_name: s.output_dlod for s in story_summaries}
    diap_ids = sorted({d.id for d in getattr(mdl, "diaps", [])})

    area_by_story: Dict[str, float] = {}
    diap_meta = []
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
        if not output_dlod_by_story.get(story, True):
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
    if not directions:
        warnings.append("No seismic output directions were resolved; DLOD generation skipped.")

    for direction in directions:
        for diap_id, story, area in diap_meta:
            story_f = fi_by_story.get(story, 0.0)
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

    total_mass_weight = sum(weights)
    base_shear = ci_eff * total_mass_weight
    return SeismicDistributionResult(
        ci=ci_eff,
        ci_input=seismic.ci,
        rt=seismic.rt,
        base_level=base_level,
        base_mass_policy=seismic.base_mass_policy,
        total_weight_kN=total_mass_weight,
        base_shear_kN=base_shear,
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
