import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import common

from stb_loads.load_cases import resolve_seismic_weight_load_case_factors
from stb_loads.story import sorted_stories, story_for_z
from stb_project import LoadConditionSettings, ProjectDefinition


def _ensure_classes_path() -> None:
    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)


def _fem_vertical_load_matrix(mdl):
    """Same nodal Z load matrix as static analysis (before support constraints)."""
    _ensure_classes_path()
    from solve import Solve

    solver = Solve.__new__(Solve)
    solver.mdl = mdl
    solver.ndof = 6
    solver.num_row = solver.ndof * len(mdl.nds)
    solver.num_lcs = mdl.max_clc
    return solver.CreateLoadMx(apply_constraints=False), solver.ndof


def _lc_column(mdl, lc: int):
    try:
        return mdl.lcs.index(lc)
    except ValueError:
        return None


def _fem_story_weights_by_lc(
    mdl,
    stories: Sequence,
    weight_lcs: Sequence[int],
) -> Dict[int, Dict[str, float]]:
    """Assign each nodal vertical FEM load (kN, downward positive) to a story."""
    lm, ndof = _fem_vertical_load_matrix(mdl)
    z_dof = 2
    by_lc: Dict[int, Dict[str, float]] = {
        lc: {s.name: 0.0 for s in stories} for lc in weight_lcs
    }
    for lc in weight_lcs:
        col = _lc_column(mdl, lc)
        if col is None:
            continue
        weights = by_lc[lc]
        for n in mdl.nds:
            fz_n = float(lm[n.cid * ndof + z_dof, col])
            if abs(fz_n) < common.PRES_ZERO:
                continue
            story = story_for_z(n.z, stories)
            if story:
                weights[story] += (-fz_n) * 1.0e-3
    return by_lc


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

    warnings: List[str] = []
    weight_lc_factors, lc_warnings = resolve_seismic_weight_load_case_factors(mdl, seismic)
    warnings.extend(lc_warnings)
    weight_lcs = sorted(weight_lc_factors.keys())

    weights: Dict[str, float] = {s.name: 0.0 for s in stories}
    if weight_lcs:
        by_lc = _fem_story_weights_by_lc(mdl, stories, weight_lcs)
        for lc in weight_lcs:
            factor = float(weight_lc_factors.get(lc, 1.0))
            for name, w in by_lc.get(lc, {}).items():
                weights[name] += max(0.0, w * factor)

    summaries = []
    for story in stories:
        w = max(0.0, weights.get(story.name, 0.0))
        summaries.append(
            StoryWeightSummary(
                story_name=story.name,
                elevation=story.elevation,
                height=story.height,
                mass_height=story.elevation + story.height * 0.5,
                weight_kN=w,
            )
        )

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


def aggregate_weight_for_load_case(
    mdl,
    project,
    lc: int,
    load_conditions=None,
) -> float:
    """Sum Wi (kN) for one load LC from the FEM load matrix."""
    load_conditions = load_conditions or project.load_conditions
    stories = sorted_stories(project.stories)
    by_lc = _fem_story_weights_by_lc(mdl, stories, [lc])
    return sum(max(0.0, w) for w in by_lc.get(lc, {}).values())


def aggregate_story_weights_for_lcs(
    mdl,
    project: ProjectDefinition,
    load_lcs: Sequence[int],
    load_conditions: LoadConditionSettings = None,
) -> WeightAggregationResult:
    """Story Wi totals for an explicit list of load cases (FEM nodal loads)."""
    load_conditions = load_conditions or project.load_conditions
    stories = sorted_stories(project.stories)
    if not stories:
        raise ValueError("project.stories is required for weight aggregation")

    warnings: List[str] = []
    weights: Dict[str, float] = {s.name: 0.0 for s in stories}
    if load_lcs:
        by_lc = _fem_story_weights_by_lc(mdl, stories, load_lcs)
        for lc in load_lcs:
            for name, w in by_lc.get(lc, {}).items():
                weights[name] += max(0.0, w)

    summaries = []
    for story in stories:
        w = max(0.0, weights.get(story.name, 0.0))
        summaries.append(
            StoryWeightSummary(
                story_name=story.name,
                elevation=story.elevation,
                height=story.height,
                mass_height=story.elevation + story.height * 0.5,
                weight_kN=w,
            )
        )

    total = sum(s.weight_kN for s in summaries)
    if total <= common.PRES_ZERO and load_lcs:
        warnings.append(
            "No vertical weight was aggregated for load cases {0}.".format(
                ", ".join(str(lc) for lc in load_lcs)
            )
        )

    return WeightAggregationResult(
        stories=tuple(summaries),
        total_weight_kN=total,
        weight_load_cases=tuple(load_lcs),
        warnings=tuple(warnings),
    )
