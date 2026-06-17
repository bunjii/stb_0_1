"""Diaphragm tributary-height wind load aggregation (DIAPHRAGM_DIRECT)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import common

from stb_loads.mass_level import resolve_base_story_name
from stb_loads.story import diaphragm_floor_z, sorted_stories
from stb_project import ProjectDefinition, Story, WindLoadCaseSettings, WindSurfaceSettings


_WALL_SURFACE_ROLES = frozenset({"WINDWARD", "LEEWARD", "SIDE"})
_PARAPET_SURFACE_ROLE = "PARAPET"
_ROOF_SURFACE_ROLE = "ROOF"
_INTEGRATION_SEGMENTS = 16


@dataclass(frozen=True)
class DiaphragmLevel:
    diaphragm_id: int
    story: str
    z_level: float


@dataclass(frozen=True)
class TributaryZone:
    diaphragm_id: int
    story: str
    diaphragm_level: float
    lower_adjacent_level: Optional[float]
    upper_adjacent_level: Optional[float]
    tributary_z_bottom: float
    tributary_z_top: float

    @property
    def tributary_height(self) -> float:
        return max(0.0, self.tributary_z_top - self.tributary_z_bottom)


@dataclass(frozen=True)
class FoundationZone:
    z_bottom: float
    z_top: float

    @property
    def height(self) -> float:
        return max(0.0, self.z_top - self.z_bottom)


@dataclass
class DiaphragmTributaryAccumulator:
    wind_case_id: int
    diaphragm_id: int
    story: str
    diaphragm_level: float
    lower_adjacent_level: Optional[float]
    upper_adjacent_level: Optional[float]
    tributary_z_bottom: float
    tributary_z_top: float
    tributary_area_m2: float = 0.0
    weighted_pressure_sum: float = 0.0
    f_story_kN: float = 0.0
    windward_force_kN: float = 0.0
    leeward_force_kN: float = 0.0
    output_to_dlod: bool = True

    @property
    def tributary_height(self) -> float:
        return max(0.0, self.tributary_z_top - self.tributary_z_bottom)

    @property
    def exposed_width(self) -> float:
        h = self.tributary_height
        if h <= common.PRES_ZERO:
            return 0.0
        return self.tributary_area_m2 / h

    @property
    def wind_pressure_w_N_m2(self) -> float:
        if self.tributary_area_m2 <= common.PRES_ZERO:
            return 0.0
        return self.weighted_pressure_sum / self.tributary_area_m2


@dataclass
class BaseWindAccumulator:
    wind_case_id: int
    z_bottom: float
    z_top: float
    tributary_area_m2: float = 0.0
    weighted_pressure_sum: float = 0.0
    f_wind_to_base_kN: float = 0.0

    @property
    def height(self) -> float:
        return max(0.0, self.z_top - self.z_bottom)

    @property
    def wind_pressure_w_N_m2(self) -> float:
        if self.tributary_area_m2 <= common.PRES_ZERO:
            return 0.0
        return self.weighted_pressure_sum / self.tributary_area_m2


def _story_z_map(stories: Sequence[Story]) -> Dict[str, float]:
    return {s.name: float(s.elevation) for s in stories}


def build_diaphragm_levels(mdl, project: ProjectDefinition, warnings: List[str]) -> Tuple[DiaphragmLevel, ...]:
    story_z = _story_z_map(project.stories)
    levels: List[DiaphragmLevel] = []
    for assign in project.load_conditions.diaphragms:
        z = diaphragm_floor_z(mdl, assign.diaphragm_id)
        if z is None:
            z = story_z.get(assign.story)
            if z is not None:
                warnings.append(
                    "Diaphragm {0}: floor Z inferred from story '{1}' elevation ({2:.3f} m).".format(
                        assign.diaphragm_id, assign.story, z,
                    )
                )
        if z is None:
            warnings.append(
                "Diaphragm {0}: could not resolve floor level; skipped in tributary aggregation.".format(
                    assign.diaphragm_id
                )
            )
            continue
        levels.append(DiaphragmLevel(
            diaphragm_id=assign.diaphragm_id,
            story=assign.story,
            z_level=float(z),
        ))
    levels.sort(key=lambda item: (item.z_level, item.diaphragm_id))
    return tuple(levels)


def resolve_base_support_context(project: ProjectDefinition) -> Tuple[float, bool]:
    stories = sorted_stories(project.stories)
    if not stories:
        return 0.0, False
    seismic = project.load_conditions.seismic
    base_fixed = bool(
        (seismic.base_level and str(seismic.base_level).strip())
        or seismic.base_elevation is not None
    )
    if seismic.base_elevation is not None:
        return float(seismic.base_elevation), base_fixed
    if seismic.base_level:
        story_z = _story_z_map(stories)
        name = str(seismic.base_level).strip()
        if name in story_z:
            return story_z[name], base_fixed
    return float(stories[0].elevation), base_fixed


def foundation_zone(z_base: float, lowest_diaphragm_z: float) -> FoundationZone:
    return FoundationZone(z_bottom=z_base, z_top=0.5 * (z_base + lowest_diaphragm_z))


def tributary_zone_for_diaphragm(
    index: int,
    levels: Sequence[DiaphragmLevel],
    z_base: float,
    base_fixed: bool,
) -> TributaryZone:
    item = levels[index]
    z_i = item.z_level
    z_below = levels[index - 1].z_level if index > 0 else z_base
    z_above = levels[index + 1].z_level if index + 1 < len(levels) else None

    if index == 0 and base_fixed:
        z_trib_bottom = 0.5 * (z_base + z_i)
    else:
        z_trib_bottom = 0.5 * (z_below + z_i)

    if index + 1 >= len(levels):
        z_trib_top = z_i
    else:
        z_trib_top = 0.5 * (z_i + z_above)

    return TributaryZone(
        diaphragm_id=item.diaphragm_id,
        story=item.story,
        diaphragm_level=z_i,
        lower_adjacent_level=z_below,
        upper_adjacent_level=z_above,
        tributary_z_bottom=z_trib_bottom,
        tributary_z_top=z_trib_top,
    )


def _clip_z_range(z_bottom: float, z_top: float, zone_lo: float, zone_hi: float) -> Optional[Tuple[float, float]]:
    lo = max(z_bottom, zone_lo)
    hi = min(z_top, zone_hi)
    if hi - lo <= common.PRES_ZERO:
        return None
    return lo, hi


def integrate_wall_force_in_z_range(
    z_lo: float,
    z_hi: float,
    width: float,
    cf: float,
    pressure_at_z,
    n_segments: int = _INTEGRATION_SEGMENTS,
) -> Tuple[float, float, float]:
    """Return force_kN, tributary_area_m2, weighted_w_sum (w * area)."""
    if z_hi - z_lo <= common.PRES_ZERO or width <= common.PRES_ZERO:
        return 0.0, 0.0, 0.0

    total_force = 0.0
    total_area = 0.0
    weighted_w = 0.0
    dz = (z_hi - z_lo) / float(n_segments)
    for i in range(n_segments):
        seg_lo = z_lo + i * dz
        seg_hi = z_lo + (i + 1) * dz
        seg_h = seg_hi - seg_lo
        z_ref = 0.5 * (seg_lo + seg_hi)
        w = pressure_at_z(z_ref, cf)
        area = width * seg_h
        total_force += w * area / 1000.0
        total_area += area
        weighted_w += w * area
    return total_force, total_area, weighted_w


def _is_wall_surface(surface: WindSurfaceSettings) -> bool:
    role = str(surface.surface_role or "WINDWARD").upper()
    return role in _WALL_SURFACE_ROLES


def _is_parapet_surface(surface: WindSurfaceSettings) -> bool:
    return str(surface.surface_role or "").upper() == _PARAPET_SURFACE_ROLE


def _accumulate_segment(
    force_kN: float,
    area_m2: float,
    weighted_w: float,
    surface_role: str,
    target: DiaphragmTributaryAccumulator,
) -> None:
    if area_m2 <= common.PRES_ZERO:
        return
    target.f_story_kN += force_kN
    target.tributary_area_m2 += area_m2
    target.weighted_pressure_sum += weighted_w
    role = str(surface_role or "").upper()
    if role == "LEEWARD":
        target.leeward_force_kN += force_kN
    elif role == "WINDWARD":
        target.windward_force_kN += force_kN


def aggregate_case_by_tributary(
    case: WindLoadCaseSettings,
    surfaces: Sequence[WindSurfaceSettings],
    levels: Sequence[DiaphragmLevel],
    z_base: float,
    base_fixed: bool,
    pressure_at_z,
    emit_dlod: bool,
) -> Tuple[
    Dict[int, DiaphragmTributaryAccumulator],
    Optional[BaseWindAccumulator],
    List[dict],
    float,
]:
    """Return per-diaphragm buckets, optional base bucket, surface contribution rows, gross wall force."""
    diap_buckets: Dict[int, DiaphragmTributaryAccumulator] = {}
    if levels:
        for idx, _level in enumerate(levels):
            zone = tributary_zone_for_diaphragm(idx, levels, z_base, base_fixed)
            diap_buckets[zone.diaphragm_id] = DiaphragmTributaryAccumulator(
                wind_case_id=case.case_id,
                diaphragm_id=zone.diaphragm_id,
                story=zone.story,
                diaphragm_level=zone.diaphragm_level,
                lower_adjacent_level=zone.lower_adjacent_level,
                upper_adjacent_level=zone.upper_adjacent_level,
                tributary_z_bottom=zone.tributary_z_bottom,
                tributary_z_top=zone.tributary_z_top,
                output_to_dlod=emit_dlod,
            )

    base_bucket: Optional[BaseWindAccumulator] = None
    if base_fixed and levels:
        fz = foundation_zone(z_base, levels[0].z_level)
        base_bucket = BaseWindAccumulator(
            wind_case_id=case.case_id,
            z_bottom=fz.z_bottom,
            z_top=fz.z_top,
        )

    top_diap_id = levels[-1].diaphragm_id if levels else None
    contributions: List[dict] = []
    gross_wall_force_kN = 0.0

    for surf in surfaces:
        if surf.wind_case_id != case.case_id:
            continue
        cf = surf.cf if surf.cf is not None else case.cf_default

        if _is_parapet_surface(surf):
            if top_diap_id is None:
                continue
            bucket = diap_buckets[top_diap_id]
            force, area, weighted_w = integrate_wall_force_in_z_range(
                surf.z_bottom, surf.z_top, surf.width, cf, pressure_at_z,
            )
            gross_wall_force_kN += force
            _accumulate_segment(force, area, weighted_w, surf.surface_role, bucket)
            contributions.append({
                "wind_case_id": case.case_id,
                "diaphragm_id": top_diap_id,
                "story": bucket.story,
                "surface_id": surf.surface_id,
                "surface_name": surf.name,
                "surface_role": surf.surface_role,
                "cf": cf,
                "z_bottom": surf.z_bottom,
                "z_top": surf.z_top,
                "tributary_area_m2": area,
                "pressure_w_N_m2": weighted_w / area if area > common.PRES_ZERO else 0.0,
                "force_kN": force,
            })
            continue

        if str(surf.surface_role or "").upper() == _ROOF_SURFACE_ROLE:
            continue

        if not _is_wall_surface(surf):
            continue

        for idx, level in enumerate(levels):
            zone = tributary_zone_for_diaphragm(idx, levels, z_base, base_fixed)
            clip = _clip_z_range(surf.z_bottom, surf.z_top, zone.tributary_z_bottom, zone.tributary_z_top)
            if clip is not None:
                z_lo, z_hi = clip
                force, area, weighted_w = integrate_wall_force_in_z_range(
                    z_lo, z_hi, surf.width, cf, pressure_at_z,
                )
                gross_wall_force_kN += force
                bucket = diap_buckets[zone.diaphragm_id]
                _accumulate_segment(force, area, weighted_w, surf.surface_role, bucket)
                contributions.append({
                    "wind_case_id": case.case_id,
                    "diaphragm_id": zone.diaphragm_id,
                    "story": zone.story,
                    "surface_id": surf.surface_id,
                    "surface_name": surf.name,
                    "surface_role": surf.surface_role,
                    "cf": cf,
                    "z_bottom": z_lo,
                    "z_top": z_hi,
                    "tributary_area_m2": area,
                    "pressure_w_N_m2": weighted_w / area if area > common.PRES_ZERO else 0.0,
                    "force_kN": force,
                })

            if idx == len(levels) - 1 and surf.z_top > level.z_level + common.PRES_ZERO:
                para_clip = _clip_z_range(surf.z_bottom, surf.z_top, level.z_level, surf.z_top)
                if para_clip is not None:
                    z_lo, z_hi = para_clip
                    if clip is not None and z_lo <= clip[1] + common.PRES_ZERO:
                        z_lo = max(z_lo, clip[1])
                    if z_hi - z_lo <= common.PRES_ZERO:
                        continue
                    force, area, weighted_w = integrate_wall_force_in_z_range(
                        z_lo, z_hi, surf.width, cf, pressure_at_z,
                    )
                    gross_wall_force_kN += force
                    bucket = diap_buckets[level.diaphragm_id]
                    _accumulate_segment(force, area, weighted_w, surf.surface_role, bucket)
                    bucket.tributary_z_top = max(bucket.tributary_z_top, z_hi)
                    contributions.append({
                        "wind_case_id": case.case_id,
                        "diaphragm_id": level.diaphragm_id,
                        "story": level.story,
                        "surface_id": surf.surface_id,
                        "surface_name": surf.name,
                        "surface_role": surf.surface_role,
                        "cf": cf,
                        "z_bottom": z_lo,
                        "z_top": z_hi,
                        "tributary_area_m2": area,
                        "pressure_w_N_m2": weighted_w / area if area > common.PRES_ZERO else 0.0,
                        "force_kN": force,
                    })

        if base_bucket is not None:
            clip = _clip_z_range(surf.z_bottom, surf.z_top, base_bucket.z_bottom, base_bucket.z_top)
            if clip is not None:
                z_lo, z_hi = clip
                force, area, weighted_w = integrate_wall_force_in_z_range(
                    z_lo, z_hi, surf.width, cf, pressure_at_z,
                )
                gross_wall_force_kN += force
                base_bucket.f_wind_to_base_kN += force
                base_bucket.tributary_area_m2 += area
                base_bucket.weighted_pressure_sum += weighted_w
                contributions.append({
                    "wind_case_id": case.case_id,
                    "diaphragm_id": None,
                    "story": "BASE",
                    "surface_id": surf.surface_id,
                    "surface_name": surf.name,
                    "surface_role": surf.surface_role,
                    "cf": cf,
                    "z_bottom": z_lo,
                    "z_top": z_hi,
                    "tributary_area_m2": area,
                    "pressure_w_N_m2": weighted_w / area if area > common.PRES_ZERO else 0.0,
                    "force_kN": force,
                })

    return diap_buckets, base_bucket, contributions, gross_wall_force_kN


def gross_wall_area_m2(surfaces: Sequence[WindSurfaceSettings], case_id: int) -> float:
    total = 0.0
    for surf in surfaces:
        if surf.wind_case_id != case_id:
            continue
        if str(surf.surface_role or "").upper() == _ROOF_SURFACE_ROLE:
            continue
        if _is_wall_surface(surf) or _is_parapet_surface(surf):
            total += max(0.0, surf.z_top - surf.z_bottom) * surf.width
    return total


def validate_tributary_conservation(
    case_id: int,
    surfaces: Sequence[WindSurfaceSettings],
    diap_buckets: Dict[int, DiaphragmTributaryAccumulator],
    base_bucket: Optional[BaseWindAccumulator],
    gross_wall_force_kN: float,
    tolerance: float = 0.05,
) -> Tuple[bool, dict]:
    gross_area = gross_wall_area_m2(surfaces, case_id)
    diap_area = sum(b.tributary_area_m2 for b in diap_buckets.values())
    base_area = base_bucket.tributary_area_m2 if base_bucket is not None else 0.0
    area_ok = abs(gross_area - (diap_area + base_area)) <= max(tolerance, gross_area * 1.0e-3)

    diap_force = sum(b.f_story_kN for b in diap_buckets.values())
    base_force = base_bucket.f_wind_to_base_kN if base_bucket is not None else 0.0
    force_ok = abs(gross_wall_force_kN - (diap_force + base_force)) <= max(tolerance, abs(gross_wall_force_kN) * 1.0e-3)

    return area_ok and force_ok, {
        "gross_wall_area_m2": gross_area,
        "diaphragm_tributary_area_m2": diap_area,
        "base_tributary_area_m2": base_area,
        "gross_wall_force_kN": gross_wall_force_kN,
        "diaphragm_force_kN": diap_force,
        "base_force_kN": base_force,
        "area_conservation_ok": area_ok,
        "force_conservation_ok": force_ok,
    }
