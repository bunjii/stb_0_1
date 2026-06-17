"""Triangulate a pick selection of nodes into DMEM triangles."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import numpy as np
from scipy.spatial import Delaunay

Point2D = Tuple[float, float]
Triangle = Tuple[int, int, int]


def _min_pairwise_distance(coords: Dict[int, Point2D], node_ids: Sequence[int]) -> float:
    best = None
    for i, a in enumerate(node_ids):
        ax, ay = coords[a]
        for b in node_ids[i + 1 :]:
            bx, by = coords[b]
            d = math.hypot(ax - bx, ay - by)
            if d <= 1.0e-12:
                raise ValueError("Selected nodes {0} and {1} are coincident in plan".format(a, b))
            if best is None or d < best:
                best = d
    if best is None:
        raise ValueError("At least 3 nodes are required for triangulation")
    return best


def project_nodes_2d(
    coords3d: Dict[int, Tuple[float, float, float]],
    node_ids: Sequence[int],
) -> Dict[int, Point2D]:
    pts = [coords3d[n] for n in node_ids]
    ranges = [
        max(p[i] for p in pts) - min(p[i] for p in pts)
        for i in range(3)
    ]
    if ranges[2] <= max(ranges[0], ranges[1]) * 0.02:
        axes = (0, 1)
    elif ranges[1] <= max(ranges[0], ranges[2]) * 0.02:
        axes = (0, 2)
    else:
        axes = (0, 1)
    return {n: (coords3d[n][axes[0]], coords3d[n][axes[1]]) for n in node_ids}


def _build_neighbor_graph(
    node_ids: Sequence[int],
    coords: Dict[int, Point2D],
    spacing: float,
    elem_adj: Dict[int, Set[int]] | None = None,
    tol: float = 0.12,
) -> Dict[int, Set[int]]:
    selected = set(node_ids)
    adj: Dict[int, Set[int]] = {n: set() for n in node_ids}
    limit = spacing * (1.0 + tol)
    for i, a in enumerate(node_ids):
        ax, ay = coords[a]
        for b in node_ids[i + 1 :]:
            bx, by = coords[b]
            d = math.hypot(ax - bx, ay - by)
            linked = d <= limit
            if elem_adj is not None:
                linked = linked or b in elem_adj.get(a, set())
            if linked:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def _boundary_node_ids(
    node_ids: Sequence[int],
    adj: Dict[int, Set[int]],
) -> List[int]:
    if not node_ids:
        return []
    max_deg = max(len(adj.get(n, set())) for n in node_ids)
    if max_deg <= 2:
        return list(node_ids)
    boundary = [n for n in node_ids if len(adj.get(n, set())) < max_deg]
    return boundary if len(boundary) >= 3 else list(node_ids)


def _trace_boundary_ccw(
    node_ids: Sequence[int],
    coords: Dict[int, Point2D],
    adj: Dict[int, Set[int]],
) -> List[int]:
    boundary_ids = _boundary_node_ids(node_ids, adj)
    boundary_set = set(boundary_ids)
    badj = {
        n: {m for m in adj.get(n, set()) if m in boundary_set}
        for n in boundary_ids
    }
    if not boundary_ids:
        raise ValueError("No nodes to trace")
    start = min(boundary_ids, key=lambda n: (coords[n][1], coords[n][0]))
    if not badj.get(start):
        raise ValueError(
            "Selected nodes are not connected in plan; pick a contiguous node region"
        )

    ordered = [start]
    prev = None
    cur = start
    for _ in range(len(boundary_ids) * 6 + 4):
        cx, cy = coords[cur]
        candidates = [n for n in badj[cur] if n != prev]
        if not candidates:
            break
        if prev is None:
            nxt = min(candidates, key=lambda n: (coords[n][1], coords[n][0]))
        else:
            px, py = coords[prev]
            in_angle = math.atan2(cy - py, cx - px)

            def rel_angle(n: int) -> float:
                nx, ny = coords[n]
                a = math.atan2(ny - cy, nx - cx)
                d = a - in_angle
                while d <= 0.0:
                    d += 2.0 * math.pi
                while d > 2.0 * math.pi:
                    d -= 2.0 * math.pi
                return d

            nxt = min(candidates, key=rel_angle)
        if nxt == start and len(ordered) >= 3:
            break
        if nxt in ordered and nxt != start:
            break
        ordered.append(nxt)
        prev, cur = cur, nxt

    if len(ordered) < 3:
        raise ValueError("Could not trace a closed boundary from selected nodes")
    return ordered


def _signed_area2(n1: int, n2: int, n3: int, coords: Dict[int, Point2D]) -> float:
    x1, y1 = coords[n1]
    x2, y2 = coords[n2]
    x3, y3 = coords[n3]
    return (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)


def _order_triangle_ccw(n1: int, n2: int, n3: int, coords: Dict[int, Point2D]) -> Triangle:
    area2 = _signed_area2(n1, n2, n3, coords)
    if abs(area2) <= 1.0e-12:
        raise ValueError("Degenerate triangle with nodes {0}, {1}, {2}".format(n1, n2, n3))
    if area2 < 0.0:
        return (n1, n3, n2)
    return (n1, n2, n3)


def _point_in_polygon(x: float, y: float, polygon: Sequence[Point2D]) -> bool:
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1.0e-30) + x1
        ):
            inside = not inside
    return inside


def triangulate_node_selection(
    coords3d: Dict[int, Tuple[float, float, float]],
    node_ids: Sequence[int],
    elem_adj: Dict[int, Set[int]] | None = None,
) -> List[Triangle]:
    """Return CCW triangles covering the selected node region."""

    nodes = sorted({int(n) for n in node_ids})
    if len(nodes) < 3:
        raise ValueError("At least 3 nodes are required for triangulation")
    if len(nodes) == 3:
        coords = project_nodes_2d(coords3d, nodes)
        return [_order_triangle_ccw(nodes[0], nodes[1], nodes[2], coords)]

    for nid in nodes:
        if nid not in coords3d:
            raise ValueError("Unknown node id: {0}".format(nid))

    coords = project_nodes_2d(coords3d, nodes)
    spacing = _min_pairwise_distance(coords, nodes)
    adj = _build_neighbor_graph(nodes, coords, spacing, elem_adj=elem_adj)
    boundary = _trace_boundary_ccw(nodes, coords, adj)
    boundary_poly = [coords[n] for n in boundary]

    id_list = list(nodes)
    points = np.array([coords[n] for n in id_list], dtype=float)
    tri = Delaunay(points)

    triangles: List[Triangle] = []
    seen: Set[Tuple[int, int, int]] = set()
    for simplex in tri.simplices:
        n1, n2, n3 = (id_list[int(simplex[0])], id_list[int(simplex[1])], id_list[int(simplex[2])])
        cx = (coords[n1][0] + coords[n2][0] + coords[n3][0]) / 3.0
        cy = (coords[n1][1] + coords[n2][1] + coords[n3][1]) / 3.0
        if not _point_in_polygon(cx, cy, boundary_poly):
            continue
        ordered = _order_triangle_ccw(n1, n2, n3, coords)
        key = tuple(sorted(ordered))
        if key in seen:
            continue
        seen.add(key)
        triangles.append(ordered)

    if not triangles:
        raise ValueError("Triangulation produced no DMEM elements for the selected nodes")
    return triangles


def elem_adjacency_for_nodes(lines: Iterable[str], selected: Set[int]) -> Dict[int, Set[int]]:
    from stb_gui.dat_edit import _parse_int, _split_record

    adj: Dict[int, Set[int]] = {n: set() for n in selected}
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "ELEM":
            continue
        parts = rec[1]
        n1 = _parse_int(parts[2], "ELEM node i")
        n2 = _parse_int(parts[3], "ELEM node j")
        if n1 in selected and n2 in selected:
            adj[n1].add(n2)
            adj[n2].add(n1)
    return adj
