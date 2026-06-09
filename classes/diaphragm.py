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

DIAP_RIGID = "RIGID"
DIAP_SEMI_RIGID = "SEMI_RIGID"
DIAP_FLEXIBLE = "FLEXIBLE"

TIMBER_FLOOR = "TIMBER_FLOOR"
TIMBER_ROOF = "TIMBER_ROOF"
TIMBER_REFERENCE_DRIFT = 1.0 / 150.0
TIMBER_UNIT_SHEAR_STRENGTH = 1.96e3  # [N/m] per floor/roof multiplier.


def normalize_diaphragm_type(value):
    s = str(value).strip().upper()
    if s in ["SEMI", "SEMIRIGID", "SEMI-RIGID", "SEMI_RIGID"]:
        return DIAP_SEMI_RIGID
    if s in ["FLEX", "FLEXIBLE"]:
        return DIAP_FLEXIBLE
    if s == "RIGID":
        return DIAP_RIGID
    raise ValueError("Unknown DIAP type: {0}".format(value))


DIAP_TYPE_CODES = {
    0: DIAP_RIGID,
    1: DIAP_SEMI_RIGID,
    2: DIAP_FLEXIBLE,
}
DIAP_SRC_DMAT = 0
DIAP_SRC_TIMBER_FLOOR = 1
DIAP_SRC_TIMBER_ROOF = 2

DCON_TRGT_AUTO = 0
DCON_TRGT_ELEM = 1
DCON_TRGT_NODE = 2
DCON_TRGT_LABELS = {0: "AUTO", 1: "MEMBER", 2: "NODE"}

DCON_CONN_RIGID = 0
DCON_CONN_OPEN = 1
DCON_CONN_LABELS = {0: CONN_CONNECTED_RIGID, 1: CONN_DISCONNECTED}

DLOD_AREA = 0
DLOD_LINE = 1
DLOD_MEMBER_TRANSFER = 2
DLOD_MASS = 3
DLOD_WEIGHT = 4


def diap_type_from_code(code):
    try:
        return DIAP_TYPE_CODES[int(code)]
    except (KeyError, ValueError, TypeError):
        raise ValueError("Unknown DIAP TYPE code: {0}".format(code))


def diap_type_to_code(diap_type):
    for code, name in DIAP_TYPE_CODES.items():
        if name == diap_type:
            return code
    raise ValueError("Unknown DIAP type: {0}".format(diap_type))


def diap_src_from_code(code):
    c = int(code)
    if c == DIAP_SRC_DMAT:
        return "DMAT"
    if c == DIAP_SRC_TIMBER_FLOOR:
        return TIMBER_FLOOR
    if c == DIAP_SRC_TIMBER_ROOF:
        return TIMBER_ROOF
    raise ValueError("Unknown DIAP SRC code: {0}".format(code))


def diap_src_to_code(source):
    s = str(source).strip().upper()
    if s in ["DMAT", "0"]:
        return DIAP_SRC_DMAT
    if s == TIMBER_FLOOR:
        return DIAP_SRC_TIMBER_FLOOR
    if s == TIMBER_ROOF:
        return DIAP_SRC_TIMBER_ROOF
    raise ValueError("Unknown DIAP SRC: {0}".format(source))


def dcon_trgt_from_code(code):
    try:
        return DCON_TRGT_LABELS[int(code)]
    except (KeyError, ValueError, TypeError):
        raise ValueError("Unknown DCON TRGT code: {0}".format(code))


def dcon_trgt_to_code(target_type):
    t = str(target_type).strip().upper()
    if t == "AUTO":
        return DCON_TRGT_AUTO
    if t in ["MEMBER", "ELEM", "ELEMENT"]:
        return DCON_TRGT_ELEM
    if t in ["NODE", "ND"]:
        return DCON_TRGT_NODE
    raise ValueError("Unknown DCON TRGT: {0}".format(target_type))


def dcon_conn_from_code(code):
    try:
        return DCON_CONN_LABELS[int(code)]
    except (KeyError, ValueError, TypeError):
        raise ValueError("Unknown DCON CONN code: {0}".format(code))


def dcon_conn_to_code(connection_type):
    c = str(connection_type).strip().upper()
    if c == CONN_CONNECTED_RIGID:
        return DCON_CONN_RIGID
    if c == CONN_DISCONNECTED:
        return DCON_CONN_OPEN
    raise ValueError("Unknown DCON CONN: {0}".format(connection_type))


def timber_multiplier_to_gt(multiplier, reference_drift=TIMBER_REFERENCE_DRIFT,
                            unit_shear_strength=TIMBER_UNIT_SHEAR_STRENGTH):
    """Convert Japanese timber floor/roof multiplier to membrane shear stiffness.

    The multiplier is specified as allowable shear force per unit length, not as
    Ex/Ey/Gxy.  Dividing by a reference drift angle gives equivalent G*t [N/m].
    """

    drift = float(reference_drift)
    if drift <= 0.0:
        raise ValueError("REFERENCE_DRIFT must be positive")
    return float(multiplier) * float(unit_shear_strength) / drift


def make_timber_diaphragm_material(_id, _name, _kind, _multiplier,
                                   _reference_drift=TIMBER_REFERENCE_DRIFT,
                                   _nuxy=0.0, _thickness=1.0):
    gt = timber_multiplier_to_gt(_multiplier, _reference_drift)
    t = float(_thickness)
    if t <= 0.0:
        raise ValueError("Equivalent diaphragm thickness must be positive")
    gxy = gt / t
    # Use a neutral isotropic membrane for the auto material; the meaningful
    # timber input is G*t, while Ex/Ey are numerical companions for plane stress.
    e = 2.0 * (1.0 + float(_nuxy)) * gxy
    mat = DiaphragmMaterial(_id, _name, e, e, gxy, _nuxy)
    mat.source = str(_kind).upper()
    mat.multiplier = float(_multiplier)
    mat.reference_drift = float(_reference_drift)
    mat.equivalent_gt = float(gt)
    mat.equivalent_thickness = t
    return mat


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
        self.source = "DMAT"
        self.multiplier = None
        self.reference_drift = None
        self.equivalent_gt = None
        self.equivalent_thickness = None

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

    def __init__(self, _id, _name, _type, _mat=None, _thickness=None, _theta=0.0,
                 _source="DMAT", _hmax=None, _reference_drift=None,
                 _timber_multiplier=None):
        self.id = _id
        self.name = _name
        self.type = normalize_diaphragm_type(_type)
        self.mat = _mat
        self.t = _thickness
        self.theta = _theta
        self.cid = None
        self.source = str(_source).upper() if _source is not None else "DMAT"
        self.hmax = _hmax
        self.reference_drift = _reference_drift
        self.timber_multiplier = _timber_multiplier

    @property
    def uses_membrane_stiffness(self):
        return self.type == DIAP_SEMI_RIGID and self.mat is not None and self.t is not None

    def OutputDiapInfo(self):
        type_code = diap_type_to_code(self.type)
        src_code = diap_src_to_code(self.source)
        if self.source in [TIMBER_FLOOR, TIMBER_ROOF]:
            mag_id = "{0:.6g}".format(self.timber_multiplier)
        elif self.mat is not None:
            mag_id = "{0: >6}".format(self.mat.id)
        else:
            mag_id = ""
        t_mm = "" if self.t is None else "{0:.3f}".format(self.t * 1e3)
        ra = "" if self.reference_drift is None else "{0:.8g}".format(self.reference_drift)
        hmax = "" if self.hmax is None else "{0:.3f}".format(self.hmax * 1e3)
        props = [
            "DIAP",
            "{0: >6}".format(self.id),
            "{0: >10}".format(self.name),
            "{0: >4}".format(type_code),
            "{0: >4}".format(src_code),
            mag_id,
            t_mm,
            "{0:.3f}".format(self.theta),
            ra,
            hmax,
        ]
        return ", ".join(props) + "\n"


class DiaphragmLoad:
    """Diaphragm-level horizontal load or seismic mass metadata."""

    AREA = "AREA"
    LINE = "LINE"
    MEMBER_TRANSFER = "MEMBER_TRANSFER"
    MASS = "MASS"
    WEIGHT = "WEIGHT"

    def __init__(self, _diap_id, _lc, _load_type, _px=0.0, _py=0.0,
                 _node_ids=None, _member_id=None, _mass=0.0, _weight=0.0,
                 _ax=0.0, _ay=0.0, _source="USER", _combi=False):
        self.diap_id = _diap_id
        self.lc = _lc
        self.load_type = str(_load_type).upper()
        self.px = float(_px)
        self.py = float(_py)
        self.node_ids = _node_ids if _node_ids is not None else []
        self.member_id = _member_id
        self.mass = float(_mass)
        self.weight = float(_weight)
        self.ax = float(_ax)
        self.ay = float(_ay)
        self.source = str(_source).upper()
        self.combi = _combi
        self.clc = None

    def OutputDLoadInfo(self):
        type_code = dlod_type_to_code(self.load_type)
        props = [
            "DLOD",
            "{0: >6}".format(self.diap_id),
            "{0: >4}".format(self.lc),
            "{0: >4}".format(type_code),
        ]
        if self.load_type == DiaphragmLoad.AREA:
            props.extend([
                "{0:.6g}".format(self.px * 1e-3),
                "{0:.6g}".format(self.py * 1e-3),
            ])
        elif self.load_type == DiaphragmLoad.LINE:
            props.extend([
                "{0: >6}".format(self.node_ids[0]),
                "{0: >6}".format(self.node_ids[1]),
                "{0:.6g}".format(self.px * 1e-3),
                "{0:.6g}".format(self.py * 1e-3),
            ])
        elif self.load_type == DiaphragmLoad.MEMBER_TRANSFER:
            props.extend([
                "{0: >6}".format(self.member_id),
                "{0:.6g}".format(self.px * 1e-3),
                "{0:.6g}".format(self.py * 1e-3),
            ])
        elif self.load_type == DiaphragmLoad.MASS:
            props.extend([
                "{0:.6g}".format(self.mass),
                "{0:.6g}".format(self.ax),
                "{0:.6g}".format(self.ay),
            ])
        else:
            props.extend([
                "{0:.6g}".format(self.weight * 1e-3),
                "{0:.6g}".format(self.ax),
                "{0:.6g}".format(self.ay),
            ])
        return ", ".join(props) + "\n"


def dlod_type_from_code(code):
    c = int(code)
    mapping = {
        DLOD_AREA: DiaphragmLoad.AREA,
        DLOD_LINE: DiaphragmLoad.LINE,
        DLOD_MEMBER_TRANSFER: DiaphragmLoad.MEMBER_TRANSFER,
        DLOD_MASS: DiaphragmLoad.MASS,
        DLOD_WEIGHT: DiaphragmLoad.WEIGHT,
    }
    if c not in mapping:
        raise ValueError("Unknown DLOD TYPE code: {0}".format(code))
    return mapping[c]


def dlod_type_to_code(load_type):
    mapping = {
        DiaphragmLoad.AREA: DLOD_AREA,
        DiaphragmLoad.LINE: DLOD_LINE,
        DiaphragmLoad.MEMBER_TRANSFER: DLOD_MEMBER_TRANSFER,
        DiaphragmLoad.MASS: DLOD_MASS,
        DiaphragmLoad.WEIGHT: DLOD_WEIGHT,
    }
    lt = str(load_type).strip().upper()
    if lt not in mapping:
        raise ValueError("Unknown DLOD TYPE: {0}".format(load_type))
    return mapping[lt]


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
        trgt = dcon_trgt_to_code(self.target_type)
        conn = dcon_conn_to_code(self.connection_type)
        target_id = "" if self.target_id is None else "{0: >6}".format(self.target_id)
        props = [
            "DCON",
            "{0: >6}".format(self.diaphragm_id),
            "{0: >4}".format(trgt),
            target_id,
            "{0: >4}".format(conn),
            "{0:.6g}".format(self.tolerance),
        ]
        if self.constraint_spacing is not None:
            props.append("{0:.6g}".format(self.constraint_spacing))
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


def _polygon_area_2d(points):
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points)):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % len(points)]
        area += x0 * y1 - y0 * x1
    return 0.5 * area


def _point_in_polygon_2d(x, y, polygon, tolerance=common.PRES_LEN):
    if len(polygon) < 3:
        return False
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        dx = xj - xi
        dy = yj - yi
        seg_len2 = dx * dx + dy * dy
        if seg_len2 > common.PRES_ZERO:
            r = ((x - xi) * dx + (y - yi) * dy) / seg_len2
            if -tolerance <= r <= 1.0 + tolerance:
                px = xi + max(0.0, min(1.0, r)) * dx
                py = yi + max(0.0, min(1.0, r)) * dy
                if math.hypot(x - px, y - py) <= tolerance:
                    return True
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def build_rigid_diaphragm_mpcs(mdl, ndof=6):
    """Generate ux/uy rigid-diaphragm MPCs for RIGID DIAP regions with DREG."""

    by_diap = {d.id: d for d in getattr(mdl, "diaps", [])}
    out = []
    for reg in getattr(mdl, "dregs", []):
        diap = by_diap.get(reg.diap_id)
        if diap is None or diap.type != DIAP_RIGID:
            continue
        poly_nodes = []
        for nid in reg.node_ids:
            n = mdl.FindNodeFromId(nid)
            if n != -1:
                poly_nodes.append(n)
        if len(poly_nodes) < 3:
            continue

        master = None
        for n in poly_nodes:
            if not (is_node_constrained(n, 0) or is_node_constrained(n, 1)):
                master = n
                break
        if master is None:
            master = poly_nodes[0]

        z0 = sum(n.z for n in poly_nodes) / float(len(poly_nodes))
        poly = [(n.x, n.y) for n in poly_nodes]
        if _polygon_area_2d(poly) < 0.0:
            poly = list(reversed(poly))

        targets = []
        for n in getattr(mdl, "nds", []):
            if n is master:
                continue
            if abs(n.z - z0) > common.PRES_LEN:
                continue
            if _point_in_polygon_2d(n.x, n.y, poly):
                targets.append(n)

        mx = master.cid * ndof
        my = master.cid * ndof + 1
        mrz = master.cid * ndof + 5
        for n in targets:
            dx = n.x - master.x
            dy = n.y - master.y
            if not is_node_constrained(n, 0):
                out.append(MPCConstraint(n.cid * ndof, [mx, mrz], [1.0, -dy]))
            if not is_node_constrained(n, 1):
                out.append(MPCConstraint(n.cid * ndof + 1, [my, mrz], [1.0, dx]))
    return out


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
    mdl.mpcs = build_rigid_diaphragm_mpcs(mdl, ndof)
    dcons = getattr(mdl, "dcons", [])
    if not dcons:
        return [], []

    by_diap = {d.id: d for d in getattr(mdl, "diaps", [])}
    member_overrides = {}
    auto_specs = []
    node_specs = []
    for dc in dcons:
        if dc.target_type == "AUTO":
            auto_specs.append(dc)
        elif dc.target_type in ["MEMBER", "ELEM", "ELEMENT"]:
            member_overrides[(dc.diaphragm_id, dc.target_id)] = dc
        elif dc.target_type in ["NODE", "ND"]:
            node_specs.append(dc)

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

    for dc in node_specs:
        if dc.connection_type == CONN_DISCONNECTED:
            continue
        diap = by_diap.get(dc.diaphragm_id)
        if diap is None:
            continue
        node = mdl.FindNodeFromId(dc.target_id)
        if node == -1:
            continue
        if is_node_constrained(node, 0) or is_node_constrained(node, 1):
            continue

        p = _node_xyz(node)
        host = find_boundary_host(p, mdl.dmems, diap, dc.tolerance)
        if host is None:
            host = find_triangle_host(p, mdl.dmems, diap, dc.tolerance)
        if host is None:
            continue
        cp = ConstraintPoint(
            -1, 0.0, p, host["host_type"], host["host_entity_id"],
            host["weights"], host["host_nodes"], node, [0, 1]
        )
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
                if master_dofs:
                    mdl.mpcs.append(MPCConstraint(slave, master_dofs, coeffs))

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
        if not self.diap.uses_membrane_stiffness:
            self.D = np.zeros((3, 3), dtype=np.float64)
            self.ek = np.zeros((6, 6), dtype=np.float64)
            self.ekG = np.zeros((9, 9), dtype=np.float64)
            return
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
