"""Mass-level weight redistribution for seismic Ai / Fi distribution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

import common

from stb_loads.story import sorted_stories, story_mass_height
from stb_project import SeismicLoadSettings, SeismicMassEntry, Story


@dataclass(frozen=True)
class MassLevelSummary:
    story_name: str
    weight_kN: float
    mass_height_m: float
    is_base_level: bool = False
    output_dlod: bool = True
    mass_role: Optional[str] = None
    mass_entry_name: Optional[str] = None
    application_diaphragm: Optional[int] = None
    include_in_total_seismic_weight: bool = True
    include_in_alpha_denominator: bool = True


def resolve_base_story_name(
    seismic: SeismicLoadSettings,
    stories: Sequence[Story],
    tolerance: float = 1.0e-6,
) -> str:
    ordered = sorted_stories(stories)
    if not ordered:
        raise ValueError("project.stories is required to resolve base_level")

    if seismic.base_level:
        name = str(seismic.base_level).strip()
        names = {s.name for s in ordered}
        if name not in names:
            raise ValueError(
                "load_conditions.seismic.base_level '{0}' is not in project.stories".format(name)
            )
        return name

    if seismic.base_elevation is not None:
        z = float(seismic.base_elevation)
        for story in ordered:
            if abs(story.elevation - z) <= tolerance:
                return story.name
        for story in ordered:
            z_min = story.elevation - tolerance
            z_max = story.elevation + story.height + tolerance
            if z_min <= z < z_max:
                return story.name
        raise ValueError(
            "load_conditions.seismic.base_elevation {0} does not match any project.story".format(z)
        )

    return ordered[0].name


def _lump_target_story(
    base_idx: int,
    stories: Sequence[Story],
    diaphragm_stories: Set[str],
) -> Optional[str]:
    for i in range(base_idx + 1, len(stories)):
        name = stories[i].name
        if name in diaphragm_stories:
            return name
    if base_idx + 1 < len(stories):
        return stories[base_idx + 1].name
    if stories[base_idx].name in diaphragm_stories:
        return stories[base_idx].name
    return None


def build_mass_level_summaries(
    raw_weights: Dict[str, float],
    stories: Sequence[Story],
    seismic: SeismicLoadSettings,
    diaphragm_stories: Set[str],
    warnings: List[str],
) -> Tuple[MassLevelSummary, ...]:
    ordered = sorted_stories(stories)
    base_name = resolve_base_story_name(seismic, ordered)
    base_idx = next(i for i, s in enumerate(ordered) if s.name == base_name)
    policy = seismic.base_mass_policy or "LUMP_TO_ABOVE_DIAPHRAGM"

    effective = {s.name: max(0.0, float(raw_weights.get(s.name, 0.0))) for s in ordered}
    w_base = effective.get(base_name, 0.0)
    lump_target = None

    if policy == "IGNORE_AT_BASE":
        if w_base > common.PRES_ZERO:
            warnings.append(
                "Base level '{0}': {1:.3f} kN excluded from seismic mass (IGNORE_AT_BASE).".format(
                    base_name, w_base
                )
            )
        effective[base_name] = 0.0

    elif policy == "LUMP_TO_ABOVE_DIAPHRAGM":
        effective[base_name] = 0.0
        if w_base > common.PRES_ZERO:
            lump_target = _lump_target_story(base_idx, ordered, diaphragm_stories)
            if lump_target is None:
                warnings.append(
                    "Base level '{0}': {1:.3f} kN could not be lumped (no diaphragm level above).".format(
                        base_name, w_base
                    )
                )
            else:
                effective[lump_target] = effective.get(lump_target, 0.0) + w_base
                if lump_target != base_name:
                    warnings.append(
                        "Base level '{0}': {1:.3f} kN lumped to mass level '{2}'.".format(
                            base_name, w_base, lump_target
                        )
                    )

    elif policy == "DISTRIBUTE_TO_ADJACENT_LEVELS":
        effective[base_name] = 0.0
        if w_base > common.PRES_ZERO and base_idx + 1 < len(ordered):
            above_name = ordered[base_idx + 1].name
            h0 = ordered[base_idx].height
            h1 = ordered[base_idx + 1].height
            denom = h0 + h1
            frac_above = (h1 / denom) if denom > common.PRES_ZERO else 1.0
            moved = w_base * frac_above
            effective[above_name] = effective.get(above_name, 0.0) + moved
            retained = w_base - moved
            warnings.append(
                "Base level '{0}': {1:.3f} kN distributed ({2:.3f} kN to '{3}', {4:.3f} kN not in DLOD mass).".format(
                    base_name, w_base, moved, above_name, retained
                )
            )
        elif w_base > common.PRES_ZERO:
            warnings.append(
                "Base level '{0}': {1:.3f} kN could not be distributed (no story above).".format(
                    base_name, w_base
                )
            )

    elif policy == "APPLY_TO_1F_DIAPHRAGM":
        if w_base > common.PRES_ZERO and base_name not in diaphragm_stories:
            warnings.append(
                "Base level '{0}': APPLY_TO_1F_DIAPHRAGM set but no diaphragm is assigned to this level.".format(
                    base_name
                )
            )

    elif policy == "APPLY_TO_WALL_NODES":
        if w_base > common.PRES_ZERO:
            warnings.append(
                "Base level '{0}': {1:.3f} kN included in Wi; apply Fi at wall nodes manually (APPLY_TO_WALL_NODES).".format(
                    base_name, w_base
                )
            )

    else:
        raise ValueError("Unsupported base_mass_policy: " + str(policy))

    out: List[MassLevelSummary] = []
    for story in ordered:
        weight = effective.get(story.name, 0.0)
        is_base = story.name == base_name
        output_dlod = True

        if is_base:
            if policy == "APPLY_TO_1F_DIAPHRAGM":
                output_dlod = story.name in diaphragm_stories
            elif policy == "LUMP_TO_ABOVE_DIAPHRAGM":
                output_dlod = (
                    lump_target == story.name
                    and story.name in diaphragm_stories
                )
            elif policy in (
                "IGNORE_AT_BASE",
                "DISTRIBUTE_TO_ADJACENT_LEVELS",
                "APPLY_TO_WALL_NODES",
            ):
                output_dlod = False

        if weight <= common.PRES_ZERO:
            continue

        out.append(MassLevelSummary(
            story_name=story.name,
            weight_kN=weight,
            mass_height_m=story_mass_height(story),
            is_base_level=is_base,
            output_dlod=output_dlod,
        ))

    if not out:
        raise ValueError("No seismic mass levels remain after base_mass_policy '{0}'".format(policy))

    return tuple(out)


def _story_by_name(stories: Sequence[Story]) -> Dict[str, Story]:
    return {s.name: s for s in stories}


def build_mass_levels_from_seismic_masses(
    entries: Sequence[SeismicMassEntry],
    raw_weights: Dict[str, float],
    stories: Sequence[Story],
    warnings: List[str],
) -> Tuple[MassLevelSummary, ...]:
    if not entries:
        raise ValueError("seismic_masses is empty")

    ordered = sorted_stories(stories)
    story_map = _story_by_name(ordered)
    resolved: List[MassLevelSummary] = []
    base_mass_weight = 0.0

    for entry in entries:
        if entry.story and entry.story not in story_map:
            raise ValueError(
                "seismic_masses entry '{0}': story '{1}' is not in project.stories".format(
                    entry.name, entry.story
                )
            )

        if entry.weight is not None:
            weight = max(0.0, float(entry.weight))
        elif entry.story:
            weight = max(0.0, float(raw_weights.get(entry.story, 0.0)))
        else:
            raise ValueError(
                "seismic_masses entry '{0}': story or weight is required".format(entry.name)
            )

        if not entry.include_in_total_seismic_weight and not entry.include_in_alpha_denominator:
            if weight > common.PRES_ZERO:
                warnings.append(
                    "Seismic mass '{0}': weight excluded from seismic totals.".format(entry.name)
                )
            continue

        if weight <= common.PRES_ZERO:
            continue

        story_name = entry.story or entry.name
        if entry.story:
            mass_height = story_mass_height(story_map[entry.story])
            is_base = entry.mass_role == "BASE_MASS"
        else:
            mass_height = 0.0
            is_base = entry.mass_role == "BASE_MASS"

        if entry.mass_role == "BASE_MASS":
            base_mass_weight += weight

        resolved.append(MassLevelSummary(
            story_name=story_name,
            weight_kN=weight,
            mass_height_m=mass_height,
            is_base_level=is_base,
            output_dlod=entry.generate_diaphragm_load,
            mass_role=entry.mass_role,
            mass_entry_name=entry.name,
            application_diaphragm=entry.application_diaphragm,
            include_in_total_seismic_weight=entry.include_in_total_seismic_weight,
            include_in_alpha_denominator=entry.include_in_alpha_denominator,
        ))

    if base_mass_weight > common.PRES_ZERO:
        warnings.append(
            "1階床重量は BASE_MASS として総地震重量には含めましたが、1階DLODには出力していません。"
        )

    if not resolved:
        raise ValueError("No seismic mass levels remain after applying seismic_masses")

    resolved.sort(key=lambda ml: ml.mass_height_m)
    return tuple(resolved)
