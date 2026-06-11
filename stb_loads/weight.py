import math

from dataclasses import dataclass, field

from typing import Dict, Sequence, Tuple



import common



from stb_loads.load_cases import resolve_seismic_weight_load_cases

from stb_loads.story import (

    diaphragm_area_m2,

    diaphragm_floor_z,

    resolve_diaphragm_story,

    sorted_stories,

    story_for_z,

)

from stb_project import LoadConditionSettings, ProjectDefinition





@dataclass(frozen=True)

class StoryWeightSummary:

    story_name: str

    elevation: float

    height: float

    mass_height: float

    weight_kN: float





@dataclass

class WeightAggregationResult:

    stories: Tuple[StoryWeightSummary, ...]

    total_weight_kN: float

    weight_load_cases: Tuple[int, ...] = ()

    warnings: Tuple[str, ...] = field(default_factory=tuple)





def aggregate_story_weights(

    mdl,

    project: ProjectDefinition,

    load_conditions: LoadConditionSettings = None,

) -> WeightAggregationResult:

    load_conditions = load_conditions or project.load_conditions

    seismic = load_conditions.seismic

    stories = sorted_stories(project.stories)

    if not stories:

        raise ValueError("project.stories is required for seismic weight aggregation")



    weights: Dict[str, float] = {s.name: 0.0 for s in stories}

    warnings = []



    weight_lcs, lc_warnings = resolve_seismic_weight_load_cases(mdl, seismic)

    warnings.extend(lc_warnings)



    for lc in weight_lcs:

        _add_gld_weights(mdl, lc, stories, weights)

        _add_pld_weights(mdl, lc, stories, weights)

        _add_eld_weights(mdl, lc, stories, weights)

        _add_ald_weights(mdl, lc, stories, weights)

        _add_dlod_weights(mdl, project, lc, stories, weights, warnings)



    summaries = []

    for story in stories:

        w = max(0.0, weights.get(story.name, 0.0))

        summaries.append(StoryWeightSummary(

            story_name=story.name,

            elevation=story.elevation,

            height=story.height,

            mass_height=story.elevation + story.height * 0.5,

            weight_kN=w,

        ))



    total = sum(s.weight_kN for s in summaries)

    if total <= common.PRES_ZERO:

        if weight_lcs:

            warnings.append(

                "No vertical weight was aggregated from LNME TYPE 1/3 load cases {0}.".format(

                    ", ".join(str(lc) for lc in weight_lcs)

                )

            )

        else:

            warnings.append("No seismic weight load cases (LNME TYPE 1 or 3) were resolved.")



    return WeightAggregationResult(

        stories=tuple(summaries),

        total_weight_kN=total,

        weight_load_cases=tuple(weight_lcs),

        warnings=tuple(warnings),

    )





def _add_gld_weights(mdl, lc, stories, weights: Dict[str, float]):

    glds = [g for g in getattr(mdl, "glds", []) if g.lc == lc and not g.combi]

    if not glds:

        return



    for e in getattr(mdl, "elms", []):

        if getattr(e, "auto_generated", False):

            continue

        element_weight = e.sec.A * e.sec.mat.gamma * e.len

        for g in glds:

            gz = g.gz

            if abs(gz) < common.PRES_ZERO:

                continue

            # element_weight is N at 1g; convert to kN.
            weight_kn = element_weight * (abs(gz) / common.GRAVITY) * 1.0e-3

            if _is_horizontal_member(e):

                story = story_for_z(0.5 * (e.n0.z + e.n1.z), stories)

                if story:

                    weights[story] += weight_kn

            else:

                for n in (e.n0, e.n1):

                    story = story_for_z(n.z, stories)

                    if story:

                        weights[story] += weight_kn * 0.5





def _is_horizontal_member(e) -> bool:

    dx = e.n1.x - e.n0.x

    dy = e.n1.y - e.n0.y

    dz = e.n1.z - e.n0.z

    horizontal = math.sqrt(dx * dx + dy * dy)

    return abs(dz) <= horizontal





def _add_pld_weights(mdl, lc, stories, weights: Dict[str, float]):

    for ld in getattr(mdl, "lds", []):

        if ld.lc != lc or ld.combi:

            continue

        if ld.nd is None:

            continue

        pz = ld.lds[2]

        if pz >= 0.0:

            continue

        story = story_for_z(ld.nd.z, stories)

        if story:

            weights[story] += (-pz) * 1.0e-3





def _add_eld_weights(mdl, lc, stories, weights: Dict[str, float]):

    for el in getattr(mdl, "elds", []):

        if el.lc != lc or el.combi:

            continue

        if el.elm is None:

            continue

        e = el.elm

        L = e.len

        if L <= common.PRES_ZERO:

            continue



        wzi, wzj = el.lds[2], el.lds[5]

        if el.isGlobal:

            end_forces = _global_eld_vertical_end_forces(L, wzi, wzj)

        else:

            end_forces = _local_eld_vertical_end_forces(e, L, wzi, wzj)



        n0_story = story_for_z(e.n0.z, stories)

        n1_story = story_for_z(e.n1.z, stories)

        if n0_story:

            weights[n0_story] += abs(end_forces[0]) * 1.0e-3

        if n1_story:

            weights[n1_story] += abs(end_forces[1]) * 1.0e-3





def _global_eld_vertical_end_forces(L, wzi, wzj):

    f0 = L / 20.0 * (7.0 * wzi + 3.0 * wzj)

    f1 = L / 20.0 * (3.0 * wzi + 7.0 * wzj)

    return f0, f1





def _local_eld_vertical_end_forces(e, L, wzi, wzj):

    import numpy as np



    lds = e.tm[0:6, 0:6] @ np.array([0.0, 0.0, wzi, 0.0, 0.0, wzj])

    f0 = L / 20.0 * (7.0 * lds[2] + 3.0 * lds[5])

    f1 = L / 20.0 * (3.0 * lds[2] + 7.0 * lds[5])

    return f0, f1





def _add_ald_weights(mdl, lc, stories, weights: Dict[str, float]):

    for al in getattr(mdl, "alds", []):

        if al.lc != lc or al.combi:

            continue

        pz = al.lds[2]

        if abs(pz) < common.PRES_ZERO:

            continue

        if al.elms is None or al.elms_areas is None:

            continue



        total_force_n = 0.0

        z_vals = []

        for e, area in zip(al.elms, al.elms_areas):

            total_force_n += area * pz

            z_vals.extend([e.n0.z, e.n1.z])

        if not z_vals:

            continue

        z_centroid = sum(z_vals) / float(len(z_vals))

        story = story_for_z(z_centroid, stories)

        if story:

            weights[story] += abs(total_force_n) * 1.0e-3





def _add_dlod_weights(mdl, project, lc, stories, weights, warnings):

    assignments = {

        d.diaphragm_id: d.story

        for d in project.load_conditions.diaphragms

    }



    for dl in getattr(mdl, "dloads", []):

        if dl.lc != lc or dl.combi:

            continue

        if dl.load_type not in ("MASS", "WEIGHT"):

            continue



        area = diaphragm_area_m2(mdl, dl.diap_id)

        if area <= common.PRES_ZERO:

            continue



        floor_z = diaphragm_floor_z(mdl, dl.diap_id)

        if floor_z is None:

            continue



        story = resolve_diaphragm_story(

            dl.diap_id, floor_z, stories, assignments, warnings

        )

        if not story:

            continue



        if dl.load_type == "WEIGHT":

            force_kN = dl.weight * area * 1.0e-3

        else:

            force_kN = dl.mass * common.GRAVITY * 1.0e-3 * area

        weights[story] += force_kN


