import common
import math

import numpy as np

from load_case_types import (
    LC_TYPE_CUSTOM,
    canonical_name,
    parse_lnme_fields,
)


class Lcase:
    def __init__(self, _lc, _load_type, _label=""):
        self.lc = int(_lc)
        self.load_type = int(_load_type)
        self.label = str(_label or "").strip()

    @property
    def lname(self):
        return canonical_name(self.load_type, self.label)

    def OutputLnameInfo(self):
        from dat_format import record_line

        values = [self.lc, self.load_type]
        fmts = [">6", ">4"]
        if self.load_type == LC_TYPE_CUSTOM or self.label:
            values.append(self.label)
            fmts.append(">10")
        return record_line("LNME", fmts, values) + "\n"

class Lcmb:
    def __init__(self, _lc, _name, _fcs, _lcs):
        self.lc  = _lc
        self.name = _name
        self.fcs = _fcs # factors
        self.lcs = _lcs # lcases

    def OutputLcmbInfo(self):

        props = ["LCMB",
                 "{0: >4}".format(self.lc), 
                 "{0: >8}".format(self.name), 
        ]

        for i in range(len(self.fcs)):
            props.append("{0: >5}".format(self.fcs[i]))
            props.append("{0: >5}".format(self.lcs[i]))

        lns = ', '.join(props) + "\n"

        return lns

class PLd:

    def __init__(self, 
                 _nid: int, 
                 _lc: int, 
                 _px: float, 
                 _py: float, 
                 _pz: float, 
                 _mx: float, 
                 _my: float, 
                 _mz: float,
                 _combi=False):

        self.nid =  _nid
        self.lc  =  _lc 
        self.lds = [_px, _py, _pz, _mx, _my, _mz]
        self.pv  =   common.Vec(_px, _py, _pz) # point load vector
        self.mv  =   common.Vec(_mx, _my, _mz) # moment vector

        self.clc =   None
        self.nd  =   None
        self.combi = _combi

    def FindNd(self, _nds):

        self.nd =  list(filter(lambda n: n.id == self.nid, _nds))[0]

    def OutputLdInfo(self):

        props = ["PLOD",
                 "{0: >6}".format(self.nid), 
                 "{0: >4}".format(self.lc), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N] -> [kN], [Nm] -> [kNm]

        lns = ', '.join(props) + "\n"

        return lns
    
class ELd:

    def __init__(self, 
                 _eid: int, 
                 _lc: int, 
                 _isG: int,
                 _wxi: float, 
                 _wyi: float, 
                 _wzi: float, 
                 _wxj: float, 
                 _wyj: float, 
                 _wzj: float,
                 _combi=False):

        self.eid =  _eid
        self.lc  =  _lc
        self.isGlobal = _isG
        self.lds = [_wxi, _wyi, _wzi, _wxj, _wyj, _wzj] # can be in GCS or ECS

        self.len = math.sqrt(max([abs(_wxi), abs(_wxj)])**2 + max([abs(_wyi), abs(_wyj)])**2 + max([abs(_wzi), abs(_wzj)])**2)

        self.clc =   None
        self.elm =   None
        self.combi = _combi

    def FindElm(self, _elms):

        self.elm =  list(filter(lambda e: e.id == self.eid, _elms))[0]

    def OutputELdInfo(self):

        props = ["ELOD",
                 "{0: >6}".format(self.eid), 
                 "{0: >4}".format(self.lc), 
                 "{0: >4}".format(self.isGlobal), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N] -> [kN], [Nm] -> [kNm]

        lns = ', '.join(props) + "\n"

        return lns

class ALd:
    def __init__(self, _lc, _px, _py, _pz, _e1, _e2, _e3, _e4, _combi=False):
        self.lc = _lc
        self.lds = [_px, _py, _pz]
        self.eids = [_e1, _e2, _e3, _e4]
        self.combi = _combi

        self.clc = None  # will be set by mdl

        self.nds = None  # kept for backward-compat (no longer used for corner point loads)
        self.elms = None # will be set by mdl
        self.nds_areas = None # kept for backward-compat
        self.elms_areas = None # tributary area [m^2] per boundary member (aligned to self.elms)
        self.elms_dc = None    # tributary-area centroid distance [m] from member.n0 (aligned to self.elms)
        self.elms_b0 = None    # tributary width [m] at member.n0 (aligned to self.elms)
        self.elms_b1 = None    # tributary width [m] at member.n1 (aligned to self.elms)
        self.elms_t = None     # sampled position t=[0..1] for tributary-width profile
        self.elms_b = None     # sampled tributary-width profile [m] aligned to self.elms_t

    # ------------------------------------------------------------------
    # Area-load distribution (tributary-area method).
    #
    # The panel pressure is distributed onto its boundary members using a
    # nearest-edge (medial-axis) tributary partition of the panel surface.
    # For each member we store the tributary area and the position of its
    # centroid along the member axis. The solver converts these into an
    # equivalent linearly-varying member load that exactly reproduces the
    # tributary resultant and its point of application (hence exact global
    # equilibrium and support reactions), including the member-axial
    # pressure component.
    # ------------------------------------------------------------------
    def SetMemberAreaLoads(self, grid_n: int = 240):

        elms = self.elms

        if elms is None or len(elms) < 3:
            raise ValueError("ALOD panel needs at least 3 boundary members")

        # 1. Order the boundary members into a closed loop of vertices.
        loop = ALd._BuildBoundaryLoop(elms)
        if loop is None:
            raise ValueError(
                f"ALOD elements {[e.id for e in elms]} do not form a single closed loop")

        # ordered start vertices of each edge (= polygon vertices)
        verts_3d = np.array([[seg["v0"].x, seg["v0"].y, seg["v0"].z] for seg in loop])
        n_edge = len(loop)

        # 2. Project the (possibly non-planar) panel onto its best-fit plane.
        centroid = verts_3d.mean(axis=0)
        rel = verts_3d - centroid
        # least-significant singular vector is the plane normal
        _, _, vt = np.linalg.svd(rel, full_matrices=True)
        normal = vt[2]
        e1 = verts_3d[1] - verts_3d[0]
        e1 = e1 - np.dot(e1, normal) * normal
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(normal, e1)

        verts_2d = np.column_stack([rel @ e1, rel @ e2])

        # 3. Exact polygon area (shoelace) used to normalise the tributary areas.
        poly_area = ALd._PolygonArea(verts_2d)
        if poly_area < common.PRES_ZERO:
            raise ValueError("ALOD panel has (near) zero area")

        # 4. Nearest-edge tributary partition -> per-edge area, centroid, end widths.
        areas, dcs, b0s, b1s, ts, bs = ALd._TributaryByEdge(verts_2d, grid_n)

        # normalise so the assigned areas sum exactly to the true panel area
        total = sum(areas)
        if total > common.PRES_ZERO:
            scale = poly_area / total
            areas = [a * scale for a in areas]

        # 5. Map each edge result back to its member (centroid measured from member.n0).
        self.elms = [seg["elm"] for seg in loop]
        self.elms_areas = areas
        self.elms_dc = []
        self.elms_b0 = []
        self.elms_b1 = []
        self.elms_t = []
        self.elms_b = []
        for k, seg in enumerate(loop):
            e = seg["elm"]
            dc_from_v0 = dcs[k]              # measured from edge start vertex (seg["v0"])
            b0_from_v0 = b0s[k]
            b1_from_v0 = b1s[k]
            t_from_v0 = ts[k]
            b_from_v0 = bs[k]
            if seg["v0"] is e.n0:
                self.elms_dc.append(dc_from_v0)
                self.elms_b0.append(b0_from_v0)
                self.elms_b1.append(b1_from_v0)
                self.elms_t.append(t_from_v0)
                self.elms_b.append(b_from_v0)
            else:                            # edge runs n1 -> n0, flip the coordinate
                self.elms_dc.append(e.len - dc_from_v0)
                self.elms_b0.append(b1_from_v0)
                self.elms_b1.append(b0_from_v0)
                self.elms_t.append(np.array([1.0 - t for t in t_from_v0[::-1]], dtype=np.float64))
                self.elms_b.append(np.array(b_from_v0[::-1], dtype=np.float64))

        # corner point loads are no longer used
        self.nds = None
        self.nds_areas = None

        return

    @staticmethod
    def _BuildBoundaryLoop(elms):
        """Order the given members into a single closed polygon loop.

        Returns a list of dicts {"elm", "v0", "v1"} where consecutive edges
        share a vertex (v1 of edge k == v0 of edge k+1), or None if the
        members do not form exactly one closed loop.
        """

        remaining = list(elms)
        first = remaining.pop(0)
        loop = [{"elm": first, "v0": first.n0, "v1": first.n1}]
        current = first.n1
        start = first.n0

        while remaining:
            nxt = None
            for e in remaining:
                if e.n0 is current:
                    nxt = {"elm": e, "v0": e.n0, "v1": e.n1}
                    break
                if e.n1 is current:
                    nxt = {"elm": e, "v0": e.n1, "v1": e.n0}
                    break
            if nxt is None:
                return None
            remaining.remove(nxt["elm"])
            loop.append(nxt)
            current = nxt["v1"]

        # the loop must close back onto the starting vertex
        if current is not start:
            return None

        return loop

    @staticmethod
    def _PolygonArea(pts_2d):
        x = pts_2d[:, 0]
        y = pts_2d[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    @staticmethod
    def _PointsInPolygon(px, py, poly):
        """Vectorised ray-casting point-in-polygon test for a simple polygon."""

        n = len(poly)
        inside = np.zeros(px.shape, dtype=bool)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i, 0], poly[i, 1]
            xj, yj = poly[j, 0], poly[j, 1]
            cond = ((yi > py) != (yj > py)) & (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-300) + xi)
            inside ^= cond
            j = i
        return inside

    @staticmethod
    def _TributaryByEdge(verts_2d, grid_n):
        """Partition the polygon by nearest boundary edge (medial-axis / 45-deg
        tributary rule) and return per-edge (area, centroid-distance-from-v0)."""

        n_edge = len(verts_2d)

        min_x, min_y = verts_2d.min(axis=0)
        max_x, max_y = verts_2d.max(axis=0)
        span = max(max_x - min_x, max_y - min_y)
        h = span / grid_n
        cell_area = h * h

        # cell-centre grid covering the bounding box
        xs = np.arange(min_x + 0.5 * h, max_x, h)
        ys = np.arange(min_y + 0.5 * h, max_y, h)
        gx, gy = np.meshgrid(xs, ys)
        gx = gx.ravel()
        gy = gy.ravel()

        inside = ALd._PointsInPolygon(gx, gy, verts_2d)
        gx = gx[inside]
        gy = gy[inside]

        pts = np.column_stack([gx, gy])

        # distance from every interior cell to every edge segment (clamped)
        dist = np.empty((n_edge, pts.shape[0]), dtype=np.float64)
        tparam = np.empty((n_edge, pts.shape[0]), dtype=np.float64)  # length along edge from v0
        for k in range(n_edge):
            a = verts_2d[k]
            b = verts_2d[(k + 1) % n_edge]
            ab = b - a
            L2 = np.dot(ab, ab)
            ap = pts - a
            t = (ap @ ab) / L2
            tc = np.clip(t, 0.0, 1.0)
            proj = a + np.outer(tc, ab)
            dvec = pts - proj
            dist[k] = np.sqrt(np.sum(dvec * dvec, axis=1))
            tparam[k] = t * np.sqrt(L2)  # projected length along edge from v0

        owner = np.argmin(dist, axis=0)

        n_bin = max(24, grid_n // 10)
        areas = []
        dcs = []
        b0s = []
        b1s = []
        ts = []
        bs = []
        for k in range(n_edge):
            a = verts_2d[k]
            b = verts_2d[(k + 1) % n_edge]
            Lk = float(np.linalg.norm(b - a))
            mask = owner == k
            cnt = int(np.count_nonzero(mask))
            areas.append(cnt * cell_area)
            if cnt > 0:
                dcs.append(float(np.mean(tparam[k][mask])))
            else:
                dcs.append(0.5 * Lk)

            # Tributary width along the edge from cell strips (zero at convex corners).
            widths = np.zeros(n_bin, dtype=np.float64)
            if cnt > 0:
                tk = tparam[k][mask]
                bins = np.linspace(0.0, Lk, n_bin + 1)
                for bi in range(n_bin):
                    lo, hi = bins[bi], bins[bi + 1]
                    in_bin = (tk >= lo) & (tk < hi if bi < n_bin - 1 else tk <= hi)
                    if np.any(in_bin):
                        widths[bi] = np.count_nonzero(in_bin) * cell_area / max(hi - lo, 1e-12)
            b0s.append(float(widths[0]))
            b1s.append(float(widths[-1]))
            ts.append(np.array([(bi + 0.5) / n_bin for bi in range(n_bin)], dtype=np.float64))
            bs.append(widths)

        return areas, dcs, b0s, b1s, ts, bs

    def OutputALdInfo(self):
        props = ["ALOD",
                 "{0: >6}".format(self.lc), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N/m2] -> [kN/m2]

        for eid in self.eids:
            props.append("{0: >4}".format(eid)) 

        lns = ', '.join(props) + "\n"

        return lns

class GLd:

    def __init__(self, 
                 _lc:   int, 
                 _gx: float,
                 _gy: float, 
                 _gz: float,
                 _combi=False):
        
        self.lc = _lc
        self.gx = _gx
        self.gy = _gy
        self.gz = _gz 

        self.clc =   None
        self.combi = _combi
        
    def OutputGLdInfo(self):

        props = ["GLOD",
                 "{0: >6}".format(self.lc), 
                 "{0: >9.6f}".format(self.gx),
                 "{0: >9.6f}".format(self.gy),
                 "{0: >9.6f}".format(self.gz)
        ]

        lns = ', '.join(props) + "\n"

        return lns