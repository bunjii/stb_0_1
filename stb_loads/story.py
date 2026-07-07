import math
from typing import Optional, Sequence, Tuple

from stb_project import Story


# Project story elevations are often rounded while model nodes keep source
# coordinates. Treat floor-level loads within 1 cm of a story elevation as
# belonging to the upper story; story_for_z iterates from top to bottom.
DEFAULT_TOLERANCE = 1.0e-2


def sorted_stories(stories: Sequence[Story]) -> Tuple[Story, ...]:
    return tuple(sorted(stories, key=lambda s: (s.elevation, s.name)))


def story_mass_height(story: Story) -> float:
    return story.elevation + story.height * 0.5


def story_for_z(z: float, stories: Sequence[Story], tolerance: float = DEFAULT_TOLERANCE) -> str:
    for story in reversed(sorted_stories(stories)):
        z_min = story.elevation - tolerance
        z_max = story.elevation + story.height + tolerance
        if z_min <= z <= z_max:
            return story.name
    return ""


def story_for_element_midpoint(e, stories: Sequence[Story], tolerance: float = DEFAULT_TOLERANCE) -> str:
    z = 0.5 * (e.n0.z + e.n1.z)
    return story_for_z(z, stories, tolerance)


def resolve_diaphragm_story(
    diap_id: int,
    floor_z: float,
    stories: Sequence[Story],
    assignments: dict,
    warnings: list,
) -> str:
    if diap_id in assignments:
        return assignments[diap_id]
    inferred = story_for_z(floor_z, stories)
    if inferred:
        warnings.append(
            "Diaphragm {0}: story inferred as '{1}' from floor Z={2:.3f} m.".format(
                diap_id, inferred, floor_z
            )
        )
        return inferred
    warnings.append(
        "Diaphragm {0}: could not assign a story (floor Z={1:.3f} m).".format(
            diap_id, floor_z
        )
    )
    return ""


def diaphragm_area_m2(mdl, diap_id) -> float:
    import common
    from diaphragm import dreg_polygon_xy

    _, area = dreg_polygon_xy(mdl, diap_id)
    if area > common.PRES_ZERO:
        return float(area)

    total = 0.0
    for m in getattr(mdl, "dmems", []):
        if m.diap.id == diap_id:
            total += float(m.area)
    return total


def diaphragm_floor_z(mdl, diap_id) -> Optional[float]:
    from diaphragm import diaphragm_floor_nodes

    nodes = diaphragm_floor_nodes(mdl, diap_id)
    if nodes:
        return sum(n.z for n in nodes) / float(len(nodes))

    z_vals = []
    for m in getattr(mdl, "dmems", []):
        if m.diap.id != diap_id:
            continue
        z_vals.extend([m.n0.z, m.n1.z, m.n2.z])
    if not z_vals:
        return None
    return sum(z_vals) / float(len(z_vals))
