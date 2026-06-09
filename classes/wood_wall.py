import math

import common
from dat_format import WWLL_FMTS, record_line
from ejnt import EJnt
from elm import Elm1D
from mat import Mat
from sec import Sec
from diaphragm import DiaphragmConnection


WOOD_WALL_MODEL_SHEAR_PANEL = "SHEAR_PANEL"
WOOD_WALL_MODEL_EQ_BRACE = "EQUIVALENT_BRACE"
WOOD_WALL_MODEL_MEMBRANE = "MEMBRANE_WALL"

WWLL_MODEL_BRACE = 0
WWLL_MODEL_PANEL = 1
WWLL_MODEL_MEMBRANE = 2
WWLL_DIR_X = 0
WWLL_DIR_Y = 1
WWLL_LAYO_SINGLE = 0
WWLL_LAYO_X = 1


def wwll_model_from_code(code):
    mapping = {
        WWLL_MODEL_BRACE: WOOD_WALL_MODEL_EQ_BRACE,
        WWLL_MODEL_PANEL: WOOD_WALL_MODEL_SHEAR_PANEL,
        WWLL_MODEL_MEMBRANE: WOOD_WALL_MODEL_MEMBRANE,
    }
    try:
        return mapping[int(code)]
    except (KeyError, ValueError, TypeError):
        raise ValueError("Unknown WWLL MODEL code: {0}".format(code))


def wwll_model_to_code(model):
    mapping = {
        WOOD_WALL_MODEL_EQ_BRACE: WWLL_MODEL_BRACE,
        WOOD_WALL_MODEL_SHEAR_PANEL: WWLL_MODEL_PANEL,
        WOOD_WALL_MODEL_MEMBRANE: WWLL_MODEL_MEMBRANE,
    }
    m = str(model).strip().upper()
    if m not in mapping:
        raise ValueError("Unknown WWLL MODEL: {0}".format(model))
    return mapping[m]


def wwll_dir_from_code(code):
    c = int(code)
    if c == WWLL_DIR_X:
        return "X"
    if c == WWLL_DIR_Y:
        return "Y"
    raise ValueError("Unknown WWLL DIR code: {0}".format(code))


def wwll_dir_to_code(direction):
    d = str(direction).strip().upper()
    if d == "X":
        return WWLL_DIR_X
    if d == "Y":
        return WWLL_DIR_Y
    raise ValueError("Unknown WWLL DIR: {0}".format(direction))


def wwll_layo_from_code(code):
    c = int(code)
    if c == WWLL_LAYO_SINGLE:
        return "SINGLE"
    if c == WWLL_LAYO_X:
        return "X"
    raise ValueError("Unknown WWLL LAYO code: {0}".format(code))


def wwll_layo_to_code(layout):
    return WWLL_LAYO_X if str(layout).strip().upper() == "X" else WWLL_LAYO_SINGLE


def _next_id(seq):
    ids = [x.id for x in seq] if seq else []
    return (max(ids) + 1) if ids else 1


class WoodRatedWall:
    """High-level wood rated wall definition (multiplier-based input)."""

    def __init__(self, _id, _name, _multiplier, _length, _height, _direction,
                 _reference_drift=1.0 / 120.0,
                 _model=WOOD_WALL_MODEL_EQ_BRACE,
                 _n1=None, _n2=None, _n3=None, _n4=None,
                 _brace_layout="X", _diap_id=None, _dcon_tol=common.PRES_LEN):
        self.id = int(_id)
        self.name = str(_name).strip()
        self.multiplier = float(_multiplier)
        self.length = float(_length)     # [m]
        self.height = float(_height)     # [m]
        self.direction = str(_direction).strip().upper()
        self.reference_drift = float(_reference_drift)
        self.model_requested = str(_model).strip().upper()
        self.model_active = self.model_requested
        self.n1 = int(_n1) if _n1 is not None else None
        self.n2 = int(_n2) if _n2 is not None else None
        self.n3 = int(_n3) if _n3 is not None else None
        self.n4 = int(_n4) if _n4 is not None else None
        self.brace_layout = str(_brace_layout).strip().upper()
        self.diap_id = int(_diap_id) if _diap_id is not None else None
        self.dcon_tol = float(_dcon_tol)
        self.generated_elem_ids = []
        self.generated_shear_panel_ids = []
        self.generated_mat_id = None
        self.generated_sec_id = None

        if self.multiplier <= 0.0:
            raise ValueError("WOOD_RATED_WALL multiplier must be positive")
        if self.length <= 0.0 or self.height <= 0.0:
            raise ValueError("WOOD_RATED_WALL length/height must be positive")
        if self.reference_drift <= 0.0:
            raise ValueError("WOOD_RATED_WALL RA must be positive")
        if self.direction not in ["X", "Y"]:
            raise ValueError("WOOD_RATED_WALL direction must be X or Y")

    @property
    def qa_kN(self):
        # Qa = 1.96 * m * L  [kN]
        return 1.96 * self.multiplier * self.length

    @property
    def delta(self):
        # Delta = RA * H [m]
        return self.reference_drift * self.height

    @property
    def k_n_per_m(self):
        # K = Qa / Delta, Qa in N.
        return (self.qa_kN * 1e3) / self.delta

    @property
    def diagonal_length(self):
        return math.sqrt(self.length ** 2 + self.height ** 2)

    def equivalent_brace_ea(self, brace_count=1):
        d = self.diagonal_length
        ea_total = self.k_n_per_m * d ** 3 / max(self.length ** 2, common.PRES_ZERO)
        return ea_total / max(brace_count, 1)

    def output_info(self):
        values = [
            self.id,
            self.name,
            wwll_model_to_code(self.model_requested),
            self.multiplier,
            self.length,
            self.height,
            wwll_dir_to_code(self.direction),
            self.reference_drift,
            "" if self.n1 is None else self.n1,
            "" if self.n2 is None else self.n2,
            "" if self.n3 is None else self.n3,
            "" if self.n4 is None else self.n4,
            "" if self.diap_id is None else self.diap_id,
            wwll_layo_to_code(self.brace_layout),
        ]
        return record_line("WWLL", WWLL_FMTS, values) + "\n"

    def generate_mvp_equivalent_braces(self, nds, mats, secs, elms, ejnts, dcons):
        if self.model_requested == WOOD_WALL_MODEL_MEMBRANE:
            raise ValueError("MEMBRANE_WALL is reserved for future implementation")
        if self.model_requested == WOOD_WALL_MODEL_SHEAR_PANEL:
            raise ValueError("use generate_shear_panel() for SHEAR_PANEL model")

        if not all(v is not None for v in [self.n1, self.n2, self.n3, self.n4]):
            raise ValueError("WOOD_RATED_WALL requires N1,N2,N3,N4 in MVP")

        by_node = {n.id: n for n in nds}
        n1 = by_node.get(self.n1)
        n2 = by_node.get(self.n2)
        n3 = by_node.get(self.n3)
        n4 = by_node.get(self.n4)
        if any(n is None for n in [n1, n2, n3, n4]):
            raise ValueError("WOOD_RATED_WALL node id not found")

        brace_pairs = [(n1, n3), (n2, n4)] if self.brace_layout == "X" else [(n1, n3)]
        ea_each = self.equivalent_brace_ea(len(brace_pairs))

        if mats:
            e = mats[0].E
            g = mats[0].G
            gamma = mats[0].gamma
            alpha = mats[0].alpha
            fy = mats[0].fy
        else:
            e = 9.5e9
            g = e / 2.6
            gamma = 5.0e3
            alpha = 3.0e-6
            fy = 20.0e6

        a = max(ea_each / max(e, common.PRES_ZERO), 1e-8)
        side = math.sqrt(a)

        mid = _next_id(mats)
        sid = _next_id(secs)
        mat = Mat(mid, "WRW_MAT_{0}".format(self.id), e, g, gamma, alpha, fy)
        sec = Sec(sid, "WRW_SEC_{0}".format(self.id), mat, 0, [side, side])
        mat.auto_generated = True
        sec.auto_generated = True
        mats.append(mat)
        secs.append(sec)
        self.generated_mat_id = mid
        self.generated_sec_id = sid

        eid = _next_id(elms)
        for na, nb in brace_pairs:
            eobj = Elm1D(eid, na, nb, sec, 0.0)
            eobj.auto_generated = True
            eobj.generated_from = "WOOD_RATED_WALL"
            eobj.generated_from_id = self.id
            elms.append(eobj)
            self.generated_elem_ids.append(eid)
            # near-pin both ends to represent axial-only brace behavior.
            ej = EJnt(eid, [1e-6, 1e-6, 1e-6, 1e-6])
            ej.auto_generated = True
            ejnts.append(ej)
            if self.diap_id is not None:
                dc = DiaphragmConnection(
                    self.diap_id, "MEMBER", eid, "CONNECTED_RIGID", self.dcon_tol
                )
                dc.auto_generated = True
                dcons.append(dc)
            eid += 1

    def generate_shear_panel(self, nds, wshears, dcons):
        if self.model_requested == WOOD_WALL_MODEL_MEMBRANE:
            raise ValueError("MEMBRANE_WALL is reserved for future implementation")
        if not all(v is not None for v in [self.n1, self.n2, self.n3, self.n4]):
            raise ValueError("WOOD_RATED_WALL requires N1,N2,N3,N4 for SHEAR_PANEL")

        by_node = {n.id: n for n in nds}
        n1 = by_node.get(self.n1)
        n2 = by_node.get(self.n2)
        n3 = by_node.get(self.n3)
        n4 = by_node.get(self.n4)
        if any(n is None for n in [n1, n2, n3, n4]):
            raise ValueError("WOOD_RATED_WALL node id not found")

        self.model_active = WOOD_WALL_MODEL_SHEAR_PANEL
        pid = _next_id(wshears)
        panel = WoodShearPanel(pid, self.id, self.name, n1, n2, n3, n4, self.direction, self.k_n_per_m)
        panel.auto_generated = True
        wshears.append(panel)
        self.generated_shear_panel_ids.append(pid)

        if self.diap_id is not None:
            # Tie wall top nodes to diaphragm using existing MPC pipeline.
            for nid in [self.n3, self.n4]:
                dc = DiaphragmConnection(
                    self.diap_id, "NODE", nid, "CONNECTED_RIGID", self.dcon_tol
                )
                dc.auto_generated = True
                dcons.append(dc)


class WoodShearPanel:
    """Equivalent shear panel on a wall rectangle."""

    def __init__(self, _id, _wall_id, _name, _n1, _n2, _n3, _n4, _direction, _k_n_per_m):
        self.id = int(_id)
        self.wall_id = int(_wall_id)
        self.name = str(_name)
        self.n1 = _n1
        self.n2 = _n2
        self.n3 = _n3
        self.n4 = _n4
        self.direction = str(_direction).upper()
        self.k = float(_k_n_per_m)  # [N/m]
        self.auto_generated = False

    def dof(self):
        if self.direction == "X":
            return 0
        if self.direction == "Y":
            return 1
        raise ValueError("WoodShearPanel direction must be X or Y")

    def nodes(self):
        return [self.n1, self.n2, self.n3, self.n4]

    def stiffness_weights(self):
        # delta = average(top) - average(bottom)
        return [-0.5, -0.5, 0.5, 0.5]
