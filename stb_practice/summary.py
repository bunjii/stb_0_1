from dataclasses import dataclass
import math
from typing import Optional, Tuple

from stb_project import ProjectDefinition


DEFAULT_TOLERANCE = 1.0e-6
LATERAL_MEMBER_KINDS = ("lateral_resisting_element", "column", "brace")


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float


@dataclass(frozen=True)
class GridSummary:
    name: str
    direction: str
    coordinate: float
    node_ids: Tuple[int, ...]
    element_ids: Tuple[int, ...]


@dataclass(frozen=True)
class StorySummary:
    name: str
    elevation: float
    height: float
    node_ids: Tuple[int, ...]
    element_ids: Tuple[int, ...]


@dataclass(frozen=True)
class MemberClassSummary:
    name: str
    kind: str
    story: str
    use: str
    element_ids: Tuple[int, ...]
    missing_element_ids: Tuple[int, ...]
    count: int
    total_length: float
    total_weight: float


@dataclass(frozen=True)
class MassItem:
    source: str
    element_id: int
    story: str
    x: float
    y: float
    weight: float


@dataclass(frozen=True)
class RigidityItem:
    element_id: int
    member_class: str
    story: str
    x: float
    y: float
    kx: float
    ky: float


@dataclass(frozen=True)
class DirectionalCenter:
    direction: str
    x: Optional[float]
    y: Optional[float]
    total_stiffness: float


@dataclass(frozen=True)
class EccentricitySummary:
    direction: str
    eccentricity: Optional[float]
    elastic_radius: Optional[float]
    eccentricity_ratio: Optional[float]


@dataclass(frozen=True)
class PracticeTables:
    grids: Tuple[dict, ...]
    stories: Tuple[dict, ...]
    member_classes: Tuple[dict, ...]
    masses: Tuple[dict, ...]
    rigidities: Tuple[dict, ...]
    eccentricities: Tuple[dict, ...]


@dataclass(frozen=True)
class PracticeSummary:
    grids: Tuple[GridSummary, ...]
    stories: Tuple[StorySummary, ...]
    member_classes: Tuple[MemberClassSummary, ...]
    center_of_mass: Optional[Point2D]
    center_of_rigidity_x: DirectionalCenter
    center_of_rigidity_y: DirectionalCenter
    eccentricity_x: EccentricitySummary
    eccentricity_y: EccentricitySummary
    mass_items: Tuple[MassItem, ...]
    rigidity_items: Tuple[RigidityItem, ...]
    warnings: Tuple[str, ...]
    tables: PracticeTables


def build_practice_summary(mdl, project: ProjectDefinition, tolerance: float = DEFAULT_TOLERANCE):
    """Build practice-layer summaries from a solved model and its project sidecar.

    The current MVP keeps the calculation transparent: mass is based on member
    self-weight, and rigidity center is based on a member stiffness proxy from
    lateral-resisting members, columns, and braces.
    """

    warnings = []
    grids = tuple(_build_grid_summaries(mdl, project, tolerance))
    stories = tuple(_build_story_summaries(mdl, project, tolerance))
    member_classes = tuple(_build_member_class_summaries(mdl, project, warnings))
    mass_items = tuple(_build_mass_items(mdl, stories))
    rigidity_items = tuple(_build_rigidity_items(mdl, project, stories, warnings))

    center_of_mass = _weighted_center([(m.x, m.y, m.weight) for m in mass_items])
    center_of_rigidity_x = _directional_center("x", rigidity_items)
    center_of_rigidity_y = _directional_center("y", rigidity_items)
    eccentricity_x = _eccentricity("x", center_of_mass, center_of_rigidity_x, rigidity_items)
    eccentricity_y = _eccentricity("y", center_of_mass, center_of_rigidity_y, rigidity_items)

    if center_of_mass is None:
        warnings.append("No positive member self-weight was available for center of mass.")
    if center_of_rigidity_x.x is None:
        warnings.append("No X-direction lateral stiffness source was available for center of rigidity.")
    if center_of_rigidity_y.x is None:
        warnings.append("No Y-direction lateral stiffness source was available for center of rigidity.")

    tables = _build_tables(
        grids,
        stories,
        member_classes,
        mass_items,
        rigidity_items,
        (eccentricity_x, eccentricity_y),
    )

    return PracticeSummary(
        grids=grids,
        stories=stories,
        member_classes=member_classes,
        center_of_mass=center_of_mass,
        center_of_rigidity_x=center_of_rigidity_x,
        center_of_rigidity_y=center_of_rigidity_y,
        eccentricity_x=eccentricity_x,
        eccentricity_y=eccentricity_y,
        mass_items=mass_items,
        rigidity_items=rigidity_items,
        warnings=tuple(warnings),
        tables=tables,
    )


def summarize_practice(mdl, project: ProjectDefinition, tolerance: float = DEFAULT_TOLERANCE):
    return build_practice_summary(mdl, project, tolerance=tolerance)


def _build_grid_summaries(mdl, project, tolerance):
    out = []
    for grid in sorted(project.grids, key=lambda g: (g.direction, g.coordinate, g.name)):
        node_ids = []
        element_ids = []
        for n in mdl.nds:
            if _coord_on_grid(n, grid.direction, grid.coordinate, tolerance):
                node_ids.append(n.id)
        for e in mdl.elms:
            if (
                _coord_on_grid(e.n0, grid.direction, grid.coordinate, tolerance)
                and _coord_on_grid(e.n1, grid.direction, grid.coordinate, tolerance)
            ):
                element_ids.append(e.id)
        out.append(GridSummary(
            name=grid.name,
            direction=grid.direction,
            coordinate=grid.coordinate,
            node_ids=tuple(sorted(node_ids)),
            element_ids=tuple(sorted(element_ids)),
        ))
    return out


def _build_story_summaries(mdl, project, tolerance):
    out = []
    for story in sorted(project.stories, key=lambda s: (s.elevation, s.name)):
        z0 = story.elevation - tolerance
        z1 = story.elevation + story.height + tolerance
        node_ids = [n.id for n in mdl.nds if z0 <= n.z <= z1]
        element_ids = [
            e.id for e in mdl.elms
            if _element_midpoint_z(e) >= z0 and _element_midpoint_z(e) <= z1
        ]
        out.append(StorySummary(
            name=story.name,
            elevation=story.elevation,
            height=story.height,
            node_ids=tuple(sorted(node_ids)),
            element_ids=tuple(sorted(element_ids)),
        ))
    return out


def _build_member_class_summaries(mdl, project, warnings):
    out = []
    for member_class in project.member_classes:
        elements = []
        missing_ids = []
        for eid in member_class.element_ids:
            e = mdl.FindElemFromEid(eid)
            if e == -1:
                missing_ids.append(eid)
            else:
                elements.append(e)
        if missing_ids:
            warnings.append(
                "Member class {0} references missing elements: {1}".format(
                    member_class.name,
                    ", ".join(str(eid) for eid in missing_ids),
                )
            )
        out.append(MemberClassSummary(
            name=member_class.name,
            kind=member_class.kind,
            story=member_class.story,
            use=member_class.use,
            element_ids=tuple(e.id for e in elements),
            missing_element_ids=tuple(missing_ids),
            count=len(elements),
            total_length=sum(e.len for e in elements),
            total_weight=sum(max(0.0, getattr(e, "weight", 0.0)) for e in elements),
        ))
    return out


def _build_mass_items(mdl, stories):
    out = []
    for e in mdl.elms:
        weight = max(0.0, getattr(e, "weight", 0.0))
        if weight <= 0.0:
            continue
        x, y, _z = _element_midpoint(e)
        out.append(MassItem(
            source="member_self_weight",
            element_id=e.id,
            story=_story_for_element(e, stories),
            x=x,
            y=y,
            weight=weight,
        ))
    return out


def _build_rigidity_items(mdl, project, stories, warnings):
    class_by_element_id = {}
    for member_class in project.member_classes:
        if member_class.kind not in LATERAL_MEMBER_KINDS:
            continue
        for eid in member_class.element_ids:
            class_by_element_id[eid] = member_class

    if not class_by_element_id:
        for e in mdl.elms:
            if _is_vertical_member(e):
                class_by_element_id[e.id] = None
        if class_by_element_id:
            warnings.append("No lateral member class was defined; vertical members were used as rigidity sources.")

    out = []
    for eid, member_class in sorted(class_by_element_id.items()):
        e = mdl.FindElemFromEid(eid)
        if e == -1:
            continue
        kx, ky = _lateral_stiffness_proxy(e)
        x, y, _z = _element_midpoint(e)
        out.append(RigidityItem(
            element_id=e.id,
            member_class=member_class.name if member_class is not None else "",
            story=member_class.story if member_class is not None else _story_for_element(e, stories),
            x=x,
            y=y,
            kx=kx,
            ky=ky,
        ))
    return out


def _directional_center(direction, rigidity_items):
    stiffness_attr = "kx" if direction == "x" else "ky"
    values = [(r.x, r.y, getattr(r, stiffness_attr)) for r in rigidity_items]
    center = _weighted_center(values)
    total = sum(max(0.0, weight) for _x, _y, weight in values)
    return DirectionalCenter(
        direction=direction,
        x=center.x if center is not None else None,
        y=center.y if center is not None else None,
        total_stiffness=total,
    )


def _eccentricity(direction, center_of_mass, center_of_rigidity, rigidity_items):
    if center_of_mass is None or center_of_rigidity.x is None or center_of_rigidity.y is None:
        return EccentricitySummary(direction=direction, eccentricity=None, elastic_radius=None, eccentricity_ratio=None)

    if direction == "x":
        stiffnesses = [(r.y, r.kx) for r in rigidity_items]
        eccentricity = abs(center_of_mass.y - center_of_rigidity.y)
        center_coordinate = center_of_rigidity.y
    else:
        stiffnesses = [(r.x, r.ky) for r in rigidity_items]
        eccentricity = abs(center_of_mass.x - center_of_rigidity.x)
        center_coordinate = center_of_rigidity.x

    elastic_radius = _elastic_radius(stiffnesses, center_coordinate)
    ratio = eccentricity / elastic_radius if elastic_radius and elastic_radius > 0.0 else None
    return EccentricitySummary(
        direction=direction,
        eccentricity=eccentricity,
        elastic_radius=elastic_radius,
        eccentricity_ratio=ratio,
    )


def _elastic_radius(values, center_coordinate):
    total_stiffness = sum(max(0.0, stiffness) for _coord, stiffness in values)
    if total_stiffness <= 0.0:
        return None
    inertia = sum(max(0.0, stiffness) * (coord - center_coordinate) ** 2 for coord, stiffness in values)
    if inertia <= 0.0:
        return 0.0
    return math.sqrt(inertia / total_stiffness)


def _weighted_center(values):
    total = sum(max(0.0, weight) for _x, _y, weight in values)
    if total <= 0.0:
        return None
    x = sum(x * max(0.0, weight) for x, _y, weight in values) / total
    y = sum(y * max(0.0, weight) for _x, y, weight in values) / total
    return Point2D(x=x, y=y)


def _coord_on_grid(node, direction, coordinate, tolerance):
    value = node.x if direction == "x" else node.y
    return abs(value - coordinate) <= tolerance


def _element_midpoint(e):
    return (
        0.5 * (e.n0.x + e.n1.x),
        0.5 * (e.n0.y + e.n1.y),
        0.5 * (e.n0.z + e.n1.z),
    )


def _element_midpoint_z(e):
    return _element_midpoint(e)[2]


def _story_for_element(e, stories):
    z = _element_midpoint_z(e)
    for story in stories:
        if story.elevation - DEFAULT_TOLERANCE <= z <= story.elevation + story.height + DEFAULT_TOLERANCE:
            return story.name
    return ""


def _is_vertical_member(e):
    dx = e.n1.x - e.n0.x
    dy = e.n1.y - e.n0.y
    dz = e.n1.z - e.n0.z
    horizontal = math.sqrt(dx * dx + dy * dy)
    return abs(dz) > horizontal


def _lateral_stiffness_proxy(e):
    if getattr(e, "ekG", None) is not None:
        kx = abs(e.ekG[0, 0]) + abs(e.ekG[6, 6])
        ky = abs(e.ekG[1, 1]) + abs(e.ekG[7, 7])
        return float(kx), float(ky)

    length = max(getattr(e, "len", 0.0), DEFAULT_TOLERANCE)
    e_mod = e.sec.mat.E
    kx = 12.0 * e_mod * e.sec.Iy / length ** 3
    ky = 12.0 * e_mod * e.sec.Iz / length ** 3
    return kx, ky


def _build_tables(grids, stories, member_classes, mass_items, rigidity_items, eccentricities):
    return PracticeTables(
        grids=tuple({
            "name": g.name,
            "direction": g.direction,
            "coordinate": g.coordinate,
            "node_ids": list(g.node_ids),
            "element_ids": list(g.element_ids),
        } for g in grids),
        stories=tuple({
            "name": s.name,
            "elevation": s.elevation,
            "height": s.height,
            "node_ids": list(s.node_ids),
            "element_ids": list(s.element_ids),
        } for s in stories),
        member_classes=tuple({
            "name": c.name,
            "kind": c.kind,
            "story": c.story,
            "use": c.use,
            "element_ids": list(c.element_ids),
            "missing_element_ids": list(c.missing_element_ids),
            "count": c.count,
            "total_length": c.total_length,
            "total_weight": c.total_weight,
        } for c in member_classes),
        masses=tuple({
            "source": m.source,
            "element_id": m.element_id,
            "story": m.story,
            "x": m.x,
            "y": m.y,
            "weight": m.weight,
        } for m in mass_items),
        rigidities=tuple({
            "element_id": r.element_id,
            "member_class": r.member_class,
            "story": r.story,
            "x": r.x,
            "y": r.y,
            "kx": r.kx,
            "ky": r.ky,
        } for r in rigidity_items),
        eccentricities=tuple({
            "direction": e.direction,
            "eccentricity": e.eccentricity,
            "elastic_radius": e.elastic_radius,
            "eccentricity_ratio": e.eccentricity_ratio,
        } for e in eccentricities),
    )
