import math

import numpy as np

import common
from dat_format import (
    DCON_FMTS,
    DIAP_FMTS,
    DLOD_AREA_FMTS,
    DLOD_LINE_FMTS,
    DLOD_MASS_FMTS,
    DLOD_MBTR_FMTS,
    DLOD_WGHT_FMTS,
    DMAT_FMTS,
    DMEM_FMTS,
    record_line,
)


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
        self.multiplier: float | None = None
        self.reference_drift: float | None = None
        self.equivalent_gt: float | None = None
        self.equivalent_thickness: float | None = None

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
        values = [
            self.id,
            self.name,
            self.Ex * 1e-6,
            self.Ey * 1e-6,
            self.Gxy * 1e-6,
            self.nuxy,
            self.gamma * 1e-3,
            self.alpha,
        ]
        return record_line("DMAT", DMAT_FMTS, values) + "\n"


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
            mag_id = self.timber_multiplier
        elif self.mat is not None:
            mag_id = self.mat.id
        else:
            mag_id = ""
        values = [
            self.id,
            self.name,
            type_code,
            src_code,
            mag_id,
            "" if self.t is None else self.t * 1e3,
            self.theta,
            "" if self.reference_drift is None else self.reference_drift,
            "" if self.hmax is None else self.hmax * 1e3,
        ]
        return record_line("DIAP", DIAP_FMTS, values) + "\n"


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
        values = [self.diap_id, self.lc, type_code]
        if self.load_type == DiaphragmLoad.AREA:
            fmts = DLOD_AREA_FMTS
            values.extend([self.px * 1e-3, self.py * 1e-3])
        elif self.load_type == DiaphragmLoad.LINE:
            fmts = DLOD_LINE_FMTS
            values.extend([
                self.node_ids[0],
                self.node_ids[1],
                self.px * 1e-3,
                self.py * 1e-3,
            ])
        elif self.load_type == DiaphragmLoad.MEMBER_TRANSFER:
            fmts = DLOD_MBTR_FMTS
            values.extend([self.member_id, self.px * 1e-3, self.py * 1e-3])
        elif self.load_type == DiaphragmLoad.MASS:
            fmts = DLOD_MASS_FMTS
            values.extend([self.mass, self.ax, self.ay])
        else:
            fmts = DLOD_WGHT_FMTS
            values.extend([self.weight * 1e-3, self.ax, self.ay])
        return record_line("DLOD", fmts, values) + "\n"


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
    def __init__(self, _diap_id, _node_ids, _auto_generated=False):
        self.diap_id = _diap_id
        self.node_ids = _node_ids
        self.auto_generated = bool(_auto_generated)


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
        self.auto_generated = False

    def OutputDConInfo(self):
        values = [
            self.diaphragm_id,
            dcon_trgt_to_code(self.target_type),
            "" if self.target_id is None else self.target_id,
            dcon_conn_to_code(self.connection_type),
            self.tolerance,
            "" if self.constraint_spacing is None else self.constraint_spacing,
        ]
        return record_line("DCON", DCON_FMTS, values) + "\n"


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


def dreg_polygon_xy(mdl, diap_id):
    """Return DREG polygon vertices (x, y) and signed area for one diaphragm."""

    for reg in getattr(mdl, "dregs", []):
        if reg.diap_id != diap_id:
            continue
        poly_nodes = []
        for nid in reg.node_ids:
            n = mdl.FindNodeFromId(nid)
            if n != -1:
                poly_nodes.append(n)
        if len(poly_nodes) < 3:
            return [], 0.0
        poly = [(n.x, n.y) for n in poly_nodes]
        area = _polygon_area_2d(poly)
        if area < 0.0:
            poly = list(reversed(poly))
            area = -area
        return poly, area
    return [], 0.0


def diaphragm_floor_nodes(mdl, diap_id, tolerance=common.PRES_LEN):
    """Return all nodes on the diaphragm floor elevation inside DREG."""

    poly, _ = dreg_polygon_xy(mdl, diap_id)
    if len(poly) < 3:
        return []
    z_vals = []
    for reg in getattr(mdl, "dregs", []):
        if reg.diap_id != diap_id:
            continue
        for nid in reg.node_ids:
            n = mdl.FindNodeFromId(nid)
            if n != -1:
                z_vals.append(n.z)
        break
    if not z_vals:
        return []
    z0 = sum(z_vals) / float(len(z_vals))
    out = []
    for n in getattr(mdl, "nds", []):
        if abs(n.z - z0) > tolerance:
            continue
        if _point_in_polygon_2d(n.x, n.y, poly, tolerance):
            out.append(n)
    return out


def append_inplane_rigid_mpc(mdl, node, host_nodes, weights, dof, ndof=6):
    """Tie a slave node UX/UY to diaphragm host nodes (CST interpolation)."""

    slave = node.cid * ndof + dof
    master_dofs = []
    coeffs = []
    self_coeff = 0.0
    for hn, w in zip(host_nodes, weights):
        w = float(w)
        if abs(w) < common.PRES_ZERO:
            continue
        mdof = hn.cid * ndof + dof
        if mdof == slave:
            self_coeff += w
            continue
        master_dofs.append(mdof)
        coeffs.append(w)
    if not master_dofs:
        return
    denom = 1.0 - self_coeff
    if abs(denom) < common.PRES_ZERO:
        return
    scale = 1.0 / denom
    mdl.mpcs.append(MPCConstraint(slave, master_dofs, [c * scale for c in coeffs]))


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


def boundary_polygon_node_ids_from_dmems(dmems, diap):
    """Return ordered outer-boundary node IDs derived from DMEM exterior edges."""

    edges = diaphragm_boundary_edges(dmems, diap)
    if len(edges) < 3:
        return []

    adj = {}
    for edge in edges:
        n0, n1 = edge["nodes"]
        adj.setdefault(n0.id, []).append(n1.id)
        adj.setdefault(n1.id, []).append(n0.id)

    start = edges[0]["nodes"][0].id
    ordered = [start]
    prev = None
    cur = start
    for _ in range(len(edges)):
        nbrs = adj.get(cur, [])
        if not nbrs:
            return []
        if len(nbrs) == 1:
            nxt = nbrs[0]
        else:
            nxt = nbrs[0] if nbrs[0] != prev else nbrs[1]
            if nxt == prev:
                nxt = next((n for n in nbrs if n != prev), nbrs[0])
        prev, cur = cur, nxt
        if cur == start:
            break
        ordered.append(cur)

    if len(ordered) < 3:
        return []
    return ordered


def _cyclic_polygon_equivalent(a, b):
    if len(a) != len(b) or len(a) < 3:
        return False
    if set(a) != set(b):
        return False
    n = len(a)
    a = list(a)
    b = list(b)
    candidates = []
    for i in range(n):
        rotated = b[i:] + b[:i]
        candidates.append(rotated)
        candidates.append(list(reversed(rotated)))
    return a in candidates


def ensure_diaphragm_dregs(diaps, dregs, dmems):
    """Ensure each DMEM-backed diaphragm has a DREG polygon; auto-generate if missing."""

    warnings = []
    by_diap = {d.id: d for d in diaps}
    existing = {}
    for reg in dregs:
        existing.setdefault(reg.diap_id, []).append(reg)

    out = list(dregs)
    for diap in diaps:
        mesh = [m for m in dmems if m.diap.id == diap.id]
        if not mesh:
            continue

        derived = boundary_polygon_node_ids_from_dmems(dmems, diap)
        if not derived:
            if not existing.get(diap.id):
                warnings.append(
                    "DIAP {0} ({1}): DMEM mesh has no closed outer boundary; "
                    "DREG is required for area loads and rigid-diaphragm MPC.".format(
                        diap.id, diap.name
                    )
                )
            continue

        regs = existing.get(diap.id, [])
        if not regs:
            out.append(DiaphragmPolygon(diap.id, derived, _auto_generated=True))
            warnings.append(
                "DIAP {0} ({1}): DREG was omitted; outer polygon {2} was derived from DMEM.".format(
                    diap.id, diap.name, derived
                )
            )
            continue

        for reg in regs:
            if _cyclic_polygon_equivalent(list(reg.node_ids), derived):
                continue
            warnings.append(
                "DIAP {0} ({1}): DREG node order {2} differs from DMEM outer boundary {3}; "
                "using explicit DREG.".format(
                    diap.id, diap.name, list(reg.node_ids), derived
                )
            )

    return out, warnings


def collect_diaphragm_input_warnings(diaps, dopns, dcons):
    """Warn about parsed diaphragm fields that are not used by the current solver."""

    warnings = []

    if dopns:
        warnings.append(
            "DOPN records were supplied ({0} opening polygon(s)) but opening cut-outs are "
            "not applied in the current analysis engine.".format(len(dopns))
        )

    for diap in diaps:
        if diap.hmax is not None:
            warnings.append(
                "DIAP {0} ({1}): HMAX={2:.4f} m is stored as metadata only and does not "
                "affect meshing or constraints in the current solver.".format(
                    diap.id, diap.name, diap.hmax
                )
            )

    spacing_count = sum(
        1 for dc in dcons
        if dc.constraint_spacing is not None and not getattr(dc, "auto_generated", False)
    )
    if spacing_count:
        warnings.append(
            "DCON SPACING was supplied on {0} connection(s) but is not used by the "
            "current MPC generator.".format(spacing_count)
        )

    return warnings


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
                        append_inplane_rigid_mpc(
                            mdl, node, cp.host_nodes, cp.shape_function_weights, dof, ndof
                        )

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
                append_inplane_rigid_mpc(
                    mdl, node, cp.host_nodes, cp.shape_function_weights, dof, ndof
                )

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
        coords2d = self.coords2d
        if coords2d is None:
            raise RuntimeError("DMEM {0} coords2d is not initialized".format(self.id))
        x1, y1 = coords2d[0]
        x2, y2 = coords2d[1]
        x3, y3 = coords2d[2]

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
        B = self.B
        T = self.T
        if B is None or T is None:
            raise RuntimeError("DMEM {0} B/T matrices are not initialized".format(self.id))
        self.D = self.diap.mat.DRotated(self.diap.theta)
        self.ek = self.diap.t * self.area * (B.T @ self.D @ B)
        self.ekG = T.T @ self.ek @ T

    def CalcResults(self, num_lcs):
        T = self.T
        B = self.B
        D = self.D
        if T is None or B is None or D is None:
            raise RuntimeError("DMEM {0} matrices are not initialized".format(self.id))
        self.strains = np.zeros((3, num_lcs), dtype=np.float64)
        self.stresses = np.zeros((3, num_lcs), dtype=np.float64)
        self.mforces = np.zeros((3, num_lcs), dtype=np.float64)

        for i in range(num_lcs):
            ug = np.zeros(9, dtype=np.float64)
            for j, n in enumerate([self.n0, self.n1, self.n2]):
                ug[3 * j:3 * j + 3] = n.disps[0:3, i]
            ul = T @ ug
            strain = B @ ul
            stress = D @ strain
            self.strains[:, i] = strain
            self.stresses[:, i] = stress
            self.mforces[:, i] = stress * self.diap.t

    def OutputDMemInfo(self):
        values = [self.id, self.diap.id, self.n0.id, self.n1.id, self.n2.id]
        return record_line("DMEM", DMEM_FMTS, values) + "\n"
