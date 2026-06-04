import math

import numpy as np

import common


CONN_CONNECTED_RIGID = "CONNECTED_RIGID"
CONN_LOAD_TRANSFER_ONLY = "LOAD_TRANSFER_ONLY"
CONN_CONNECTED_SPRING = "CONNECTED_SPRING"
CONN_DISCONNECTED = "DISCONNECTED"

ASSOC_BOUNDARY = "boundary_member"
ASSOC_EMBEDDED = "embedded_member"
ASSOC_CROSSING = "crossing_member"
ASSOC_NONE = "none"

HOST_EDGE = "diaphragm_edge"
HOST_TRIANGLE = "diaphragm_triangle"


class DiaphragmMaterial:
    """Plane-stress material for diaphragm membrane elements."""

    def __init__(self, _id, _name, _Ex, _Ey, _Gxy, _nuxy, _gamma=0.0, _alpha=0.0):
        self.id = _id
        self.name = _name
        self.Ex = _Ex
        self.Ey = _Ey
        self.Gxy = _Gxy
        self.nuxy = _nuxy
        self.gamma = _gamma
        self.alpha = _alpha
        self.cid = None

    @property
    def nuyx(self):
        if abs(self.Ex) < common.PRES_ZERO:
            return 0.0
        return self.nuxy * self.Ey / self.Ex

    def DPlaneStress(self):
        nuyx = self.nuyx
        den = 1.0 - self.nuxy * nuyx
        if abs(den) < common.PRES_ZERO:
            raise ValueError("Invalid diaphragm material Poisson ratio")

        return np.array([
            [self.Ex / den, self.nuxy * self.Ey / den, 0.0],
            [self.nuxy * self.Ey / den, self.Ey / den, 0.0],
            [0.0, 0.0, self.Gxy],
        ], dtype=np.float64)

    def DRotated(self, theta_deg):
        q = self.DPlaneStress()
        q11, q12, q22, q66 = q[0, 0], q[0, 1], q[1, 1], q[2, 2]

        th = math.radians(theta_deg)
        m = math.cos(th)
        n = math.sin(th)
        m2 = m * m
        n2 = n * n
        m3 = m2 * m
        n3 = n2 * n
        m4 = m2 * m2
        n4 = n2 * n2
        m2n2 = m2 * n2

        return np.array([
            [
                q11 * m4 + 2.0 * (q12 + 2.0 * q66) * m2n2 + q22 * n4,
                (q11 + q22 - 4.0 * q66) * m2n2 + q12 * (m4 + n4),
                (q11 - q12 - 2.0 * q66) * m3 * n - (q22 - q12 - 2.0 * q66) * m * n3,
            ],
            [
                (q11 + q22 - 4.0 * q66) * m2n2 + q12 * (m4 + n4),
                q11 * n4 + 2.0 * (q12 + 2.0 * q66) * m2n2 + q22 * m4,
                (q11 - q12 - 2.0 * q66) * m * n3 - (q22 - q12 - 2.0 * q66) * m3 * n,
            ],
            [
                (q11 - q12 - 2.0 * q66) * m3 * n - (q22 - q12 - 2.0 * q66) * m * n3,
                (q11 - q12 - 2.0 * q66) * m * n3 - (q22 - q12 - 2.0 * q66) * m3 * n,
                (q11 + q22 - 2.0 * q12 - 2.0 * q66) * m2n2 + q66 * (m4 + n4),
            ],
        ], dtype=np.float64)

    def OutputDMatInfo(self):
        props = [
            "DMAT",
            "{0: >6}".format(self.id),
            "{0: >10}".format(self.name),
            "{0: >10.3f}".format(self.Ex * 1e-6),
            "{0: >10.3f}".format(self.Ey * 1e-6),
            "{0: >10.3f}".format(self.Gxy * 1e-6),
            "{0: >10.5f}".format(self.nuxy),
            "{0: >8.1f}".format(self.gamma * 1e-3),
            "{0: 8.1e}".format(self.alpha),
        ]
        return ", ".join(props) + "\n"


class DiaphragmRegion:
    """High-level diaphragm region metadata."""

    def __init__(self, _id, _name, _type, _mat, _thickness, _theta=0.0):
        self.id = _id
        self.name = _name
        self.type = str(_type).upper()
        self.mat = _mat
        self.t = _thickness
        self.theta = _theta
        self.cid = None

    def OutputDiapInfo(self):
        props = [
            "DIAP",
            "{0: >6}".format(self.id),
            "{0: >10}".format(self.name),
            "{0: >8}".format(self.type),
            "DMAT={0}".format(self.mat.id),
            "T={0:.3f}".format(self.t * 1e3),
            "THETA={0:.3f}".format(self.theta),
        ]
        return ", ".join(props) + "\n"


class DiaphragmPolygon:
    def __init__(self, _diap_id, _node_ids):
        self.diap_id = _diap_id
        self.node_ids = _node_ids


class DiaphragmOpening:
    def __init__(self, _diap_id, _node_ids):
        self.diap_id = _diap_id
        self.node_ids = _node_ids


class DiaphragmConnection:
    """User/API diaphragm-to-frame connection request."""

    def __init__(self, _diap_id, _target_type="AUTO", _target_id=None,
                 _connection_type=CONN_CONNECTED_RIGID, _tolerance=common.PRES_LEN,
                 _constraint_spacing=None, _spring_properties=None):
        self.diaphragm_id = _diap_id
        self.target_type = str(_target_type).upper()
        self.target_id = _target_id
        self.connection_type = str(_connection_type).upper()
        self.tolerance = _tolerance
        self.constraint_spacing = _constraint_spacing
        self.spring_properties = _spring_properties

    def OutputDConInfo(self):
        props = [
            "DCON",
            "{0: >6}".format(self.diaphragm_id),
            "{0: >8}".format(self.target_type),
        ]
        if self.target_type in ["MEMBER", "ELEM", "ELEMENT"] and self.target_id is not None:
            props.append("{0: >6}".format(self.target_id))
        props.append("{0: >16}".format(self.connection_type))
        props.append("TOL={0:.6g}".format(self.tolerance))
        if self.constraint_spacing is not None:
            props.append("SPACING={0:.6g}".format(self.constraint_spacing))
        return ", ".join(props) + "\n"


class DiaphragmMemberAssociation:
    """Resolved geometric association between one member and one diaphragm."""

    def __init__(self, _diap_id, _member_id, _association_type=ASSOC_NONE,
                 _connection_type=CONN_DISCONNECTED, _generated_constraint_points=None):
        self.diaphragm_id = _diap_id
        self.member_id = _member_id
        self.association_type = _association_type
        self.connection_type = _connection_type
        self.generated_constraint_points = (
            _generated_constraint_points if _generated_constraint_points is not None else []
        )


class ConstraintPoint:
    """Internal point on a member constrained to a diaphragm field."""

    def __init__(self, _parent_member_id, _xi, _global_coordinate,
                 _host_type, _host_entity_id, _shape_function_weights,
                 _host_nodes, _target_node=None, _dof_constraints=None):
        self.parent_member_id = _parent_member_id
        self.local_position_on_member = _xi
        self.global_coordinate = _global_coordinate
        self.host_type = _host_type
        self.host_entity_id = _host_entity_id
        self.shape_function_weights = _shape_function_weights
        self.host_nodes = _host_nodes
        self.target_node = _target_node
        self.dof_constraints = _dof_constraints if _dof_constraints is not None else [0, 1]


class MPCConstraint:
    """Linear multi-point constraint: slave_dof = sum(coeff * master_dof)."""

    def __init__(self, _slave_dof, _master_dofs, _coefficients, _constant_term=0.0):
        self.slave_dof = _slave_dof
        self.master_dofs = _master_dofs
        self.coefficients = _coefficients
        self.constant_term = _constant_term


def _node_xyz(n):
    return np.array([n.x, n.y, n.z], dtype=np.float64)


def _point_xyz(p):
    if hasattr(p, "x") and hasattr(p, "y") and hasattr(p, "z"):
        return np.array([p.x, p.y, p.z], dtype=np.float64)
    return np.array(p, dtype=np.float64)


def edge_shape_weights(point, node_a, node_b, tolerance=common.PRES_LEN):
    """Return interpolation on edge AB as (r, [1-r, r], distance), or None."""

    p = _point_xyz(point)
    a = _node_xyz(node_a)
    b = _node_xyz(node_b)
    ab = b - a
    l2 = float(np.dot(ab, ab))
    if l2 < common.PRES_ZERO:
        return None

    r = float(np.dot(p - a, ab) / l2)
    rc = max(0.0, min(1.0, r))
    proj = a + rc * ab
    dist = float(np.linalg.norm(p - proj))
    if r < -tolerance or r > 1.0 + tolerance or dist > tolerance:
        return None

    rc = 0.0 if rc < tolerance else (1.0 if 1.0 - rc < tolerance else rc)
    return rc, [1.0 - rc, rc], dist


def triangle_shape_weights(point, node_a, node_b, node_c, tolerance=common.PRES_LEN):
    """Return CST area coordinates [NA, NB, NC] for a point, or None."""

    p = _point_xyz(point)
    a = _node_xyz(node_a)
    b = _node_xyz(node_b)
    c = _node_xyz(node_c)

    normal = np.cross(b - a, c - a)
    nlen = float(np.linalg.norm(normal))
    if nlen < common.PRES_ZERO:
        return None
    normal = normal / nlen
    plane_dist = float(abs(np.dot(p - a, normal)))
    if plane_dist > tolerance:
        return None

    # Area coordinates in 3D, projected to the triangle plane.
    pp = p - np.dot(p - a, normal) * normal
    v0 = b - a
    v1 = c - a
    v2 = pp - a
    d00 = float(np.dot(v0, v0))
    d01 = float(np.dot(v0, v1))
    d11 = float(np.dot(v1, v1))
    d20 = float(np.dot(v2, v0))
    d21 = float(np.dot(v2, v1))
    denom = d00 * d11 - d01 * d01
    if abs(denom) < common.PRES_ZERO:
        return None

    nb = (d11 * d20 - d01 * d21) / denom
    nc = (d00 * d21 - d01 * d20) / denom
    na = 1.0 - nb - nc
    weights = [float(na), float(nb), float(nc)]
    if min(weights) < -tolerance or max(weights) > 1.0 + tolerance:
        return None

    weights = [0.0 if abs(w) < tolerance else (1.0 if abs(w - 1.0) < tolerance else w)
               for w in weights]
    total = sum(weights)
    if abs(total) < common.PRES_ZERO:
        return None
    weights = [float(w / total) for w in weights]
    return weights


def diaphragm_boundary_edges(dmems, diap):
    """Extract exterior mesh edges for one diaphragm as edge records."""

    edge_map = {}
    for m in dmems:
        if m.diap is not diap and m.diap.id != diap.id:
            continue
        nodes = [m.n0, m.n1, m.n2]
        for i0, i1 in [(0, 1), (1, 2), (2, 0)]:
            n0, n1 = nodes[i0], nodes[i1]
            key = tuple(sorted([n0.id, n1.id]))
            if key not in edge_map:
                edge_map[key] = {"count": 0, "nodes": (n0, n1), "membrane": m}
            edge_map[key]["count"] += 1

    edges = []
    eid = 0
    for data in edge_map.values():
        if data["count"] == 1:
            eid += 1
            edges.append({
                "id": eid,
                "nodes": data["nodes"],
                "membrane": data["membrane"],
            })
    return edges


def find_boundary_host(point, dmems, diap, tolerance=common.PRES_LEN):
    best = None
    for edge in diaphragm_boundary_edges(dmems, diap):
        n0, n1 = edge["nodes"]
        hit = edge_shape_weights(point, n0, n1, tolerance)
        if hit is None:
            continue
        r, weights, dist = hit
        if best is None or dist < best["distance"]:
            best = {
                "host_type": HOST_EDGE,
                "host_entity_id": edge["id"],
                "host_nodes": [n0, n1],
                "weights": weights,
                "r": r,
                "distance": dist,
            }
    return best


def find_triangle_host(point, dmems, diap, tolerance=common.PRES_LEN):
    for m in dmems:
        if m.diap is not diap and m.diap.id != diap.id:
            continue
        weights = triangle_shape_weights(point, m.n0, m.n1, m.n2, tolerance)
        if weights is not None:
            return {
                "host_type": HOST_TRIANGLE,
                "host_entity_id": m.id,
                "host_nodes": [m.n0, m.n1, m.n2],
                "weights": weights,
            }
    return None


def is_node_constrained(node, dof):
    cons = getattr(node, "cons", None)
    if cons is None:
        return False
    return bool(cons.csts[dof])


def build_diaphragm_mpcs(mdl, ndof=6):
    """Resolve DCON requests into associations and ux/uy MPC constraints."""

    mdl.dassocs = []
    mdl.mpcs = []
    dcons = getattr(mdl, "dcons", [])
    if not dcons:
        return [], []

    by_diap = {d.id: d for d in getattr(mdl, "diaps", [])}
    member_overrides = {}
    auto_specs = []
    for dc in dcons:
        if dc.target_type == "AUTO":
            auto_specs.append(dc)
        elif dc.target_type in ["MEMBER", "ELEM", "ELEMENT"]:
            member_overrides[(dc.diaphragm_id, dc.target_id)] = dc

    specs = []
    for dc in auto_specs:
        for e in mdl.elms:
            specs.append((dc, e))
    for dc in dcons:
        if dc.target_type in ["MEMBER", "ELEM", "ELEMENT"]:
            e = mdl.FindElemFromEid(dc.target_id)
            if e != -1:
                specs.append((dc, e))

    seen = set()
    for dc, e in specs:
        key = (dc.diaphragm_id, e.id)
        if key in seen:
            continue
        seen.add(key)

        override = member_overrides.get(key)
        if override is not None:
            dc = override

        diap = by_diap.get(dc.diaphragm_id)
        if diap is None:
            continue

        cps = []
        if dc.connection_type != CONN_DISCONNECTED:
            for xi, node in [(0.0, e.n0), (1.0, e.n1)]:
                if is_node_constrained(node, 0) or is_node_constrained(node, 1):
                    continue
                p = _node_xyz(node)
                host = find_boundary_host(p, mdl.dmems, diap, dc.tolerance)
                if host is None:
                    host = find_triangle_host(p, mdl.dmems, diap, dc.tolerance)
                if host is None:
                    continue
                cp = ConstraintPoint(
                    e.id, xi, p, host["host_type"], host["host_entity_id"],
                    host["weights"], host["host_nodes"], node, [0, 1]
                )
                cps.append(cp)

                if dc.connection_type == CONN_CONNECTED_RIGID:
                    for dof in [0, 1]:
                        slave = node.cid * ndof + dof
                        master_dofs = []
                        coeffs = []
                        for hn, w in zip(cp.host_nodes, cp.shape_function_weights):
                            mdof = hn.cid * ndof + dof
                            if mdof == slave:
                                continue
                            if abs(w) < common.PRES_ZERO:
                                continue
                            master_dofs.append(mdof)
                            coeffs.append(float(w))
                        if not master_dofs:
                            continue
                        mdl.mpcs.append(MPCConstraint(slave, master_dofs, coeffs))

        if not cps:
            assoc_type = ASSOC_NONE
        elif all(cp.host_type == HOST_EDGE for cp in cps):
            assoc_type = ASSOC_BOUNDARY
        elif all(cp.host_type == HOST_TRIANGLE for cp in cps):
            assoc_type = ASSOC_EMBEDDED
        else:
            assoc_type = ASSOC_CROSSING
        mdl.dassocs.append(DiaphragmMemberAssociation(
            dc.diaphragm_id, e.id, assoc_type, dc.connection_type, cps
        ))

    return mdl.dassocs, mdl.mpcs


class CSTMembrane3:
    """Three-node constant-strain plane-stress membrane element."""

    def __init__(self, _id, _diap, _n0, _n1, _n2):
        self.id = _id
        self.diap = _diap
        self.n0 = _n0
        self.n1 = _n1
        self.n2 = _n2
        self.cid = None

        self.area = None
        self.ex = None
        self.ey = None
        self.ez = None
        self.coords2d = None
        self.B = None
        self.D = None
        self.ek = None
        self.T = None
        self.ekG = None
        self.strains = None
        self.stresses = None
        self.mforces = None

        self.CalcMatrices()

    def _node_array(self, n):
        return np.array([n.x, n.y, n.z], dtype=np.float64)

    def CalcLocalAxes(self):
        p0 = self._node_array(self.n0)
        p1 = self._node_array(self.n1)
        p2 = self._node_array(self.n2)

        v01 = p1 - p0
        v02 = p2 - p0
        L = np.linalg.norm(v01)
        if L < common.PRES_ZERO:
            raise ValueError("DMEM {0} has coincident first/second nodes".format(self.id))

        ex = v01 / L
        ez = np.cross(v01, v02)
        ez_len = np.linalg.norm(ez)
        if ez_len < common.PRES_ZERO:
            raise ValueError("DMEM {0} has zero area".format(self.id))
        ez = ez / ez_len
        ey = np.cross(ez, ex)
        ey = ey / np.linalg.norm(ey)

        self.ex = ex
        self.ey = ey
        self.ez = ez

        x1, y1 = 0.0, 0.0
        x2, y2 = float(np.dot(p1 - p0, ex)), float(np.dot(p1 - p0, ey))
        x3, y3 = float(np.dot(p2 - p0, ex)), float(np.dot(p2 - p0, ey))
        self.coords2d = np.array([[x1, y1], [x2, y2], [x3, y3]], dtype=np.float64)

    def CalcBMatrix(self):
        x1, y1 = self.coords2d[0]
        x2, y2 = self.coords2d[1]
        x3, y3 = self.coords2d[2]

        det2A = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if abs(det2A) < common.PRES_ZERO:
            raise ValueError("DMEM {0} has zero local area".format(self.id))

        self.area = abs(det2A) * 0.5

        b1, b2, b3 = y2 - y3, y3 - y1, y1 - y2
        c1, c2, c3 = x3 - x2, x1 - x3, x2 - x1
        self.B = (1.0 / det2A) * np.array([
            [b1, 0.0, b2, 0.0, b3, 0.0],
            [0.0, c1, 0.0, c2, 0.0, c3],
            [c1, b1, c2, b2, c3, b3],
        ], dtype=np.float64)

    def CalcTransformation(self):
        T = np.zeros((6, 9), dtype=np.float64)
        for i in range(3):
            gc = 3 * i
            lc = 2 * i
            T[lc, gc:gc + 3] = self.ex
            T[lc + 1, gc:gc + 3] = self.ey
        self.T = T

    def CalcMatrices(self):
        self.CalcLocalAxes()
        self.CalcBMatrix()
        self.CalcTransformation()
        self.D = self.diap.mat.DRotated(self.diap.theta)
        self.ek = self.diap.t * self.area * (self.B.T @ self.D @ self.B)
        self.ekG = self.T.T @ self.ek @ self.T

    def CalcResults(self, num_lcs):
        self.strains = np.zeros((3, num_lcs), dtype=np.float64)
        self.stresses = np.zeros((3, num_lcs), dtype=np.float64)
        self.mforces = np.zeros((3, num_lcs), dtype=np.float64)

        for i in range(num_lcs):
            ug = np.zeros(9, dtype=np.float64)
            for j, n in enumerate([self.n0, self.n1, self.n2]):
                ug[3 * j:3 * j + 3] = n.disps[0:3, i]
            ul = self.T @ ug
            strain = self.B @ ul
            stress = self.D @ strain
            self.strains[:, i] = strain
            self.stresses[:, i] = stress
            self.mforces[:, i] = stress * self.diap.t

    def OutputDMemInfo(self):
        props = [
            "DMEM",
            "{0: >6}".format(self.id),
            "{0: >6}".format(self.diap.id),
            "{0: >6}".format(self.n0.id),
            "{0: >6}".format(self.n1.id),
            "{0: >6}".format(self.n2.id),
        ]
        return ", ".join(props) + "\n"
