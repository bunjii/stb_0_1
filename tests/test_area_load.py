import os
import sys
import math
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
_CLASSES_DIR = os.path.join(_STB_ROOT, "classes")
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from stb_engine import run_from_file
from ld import ALd


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class _FakeNode:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class _FakeElm:
    def __init__(self, eid, n0, n1):
        self.id = eid
        self.n0 = n0
        self.n1 = n1
        self.len = math.dist((n0.x, n0.y, n0.z), (n1.x, n1.y, n1.z))


def _make_panel(elm_order):
    """Build a rectangular panel (4 m x 3 m, area 12) and run the tributary
    distribution. `elm_order` lets the members be passed in arbitrary order."""

    a = _FakeNode(0.0, 0.0, 0.0)
    b = _FakeNode(4.0, 0.0, 0.0)
    c = _FakeNode(4.0, 3.0, 0.0)
    d = _FakeNode(0.0, 3.0, 0.0)

    elms = {
        0: _FakeElm(0, a, b),  # length 4
        1: _FakeElm(1, b, c),  # length 3
        2: _FakeElm(2, c, d),  # length 4
        3: _FakeElm(3, d, a),  # length 3
    }

    al = ALd(0, 0.0, 0.0, -5000.0, 0, 1, 2, 3)
    al.elms = [elms[i] for i in elm_order]
    al.SetMemberAreaLoads(grid_n=300)
    return al


class TestAreaLoadTributary(unittest.TestCase):

    def test_total_area_preserved(self):
        al = _make_panel([0, 1, 2, 3])
        self.assertAlmostEqual(sum(al.elms_areas), 12.0, places=4)

    def test_area_split_matches_45deg_rule(self):
        al = _make_panel([0, 1, 2, 3])
        by_id = {e.id: a for e, a in zip(al.elms, al.elms_areas)}
        # long edges (len 4) -> trapezoid 3.75 m2 ; short edges (len 3) -> triangle 2.25 m2
        self.assertAlmostEqual(by_id[0], 3.75, delta=0.05)
        self.assertAlmostEqual(by_id[2], 3.75, delta=0.05)
        self.assertAlmostEqual(by_id[1], 2.25, delta=0.05)
        self.assertAlmostEqual(by_id[3], 2.25, delta=0.05)

    def test_centroids_symmetric(self):
        al = _make_panel([0, 1, 2, 3])
        by_id = {e.id: (dc, e.len) for e, dc in zip(al.elms, al.elms_dc)}
        for eid, (dc, L) in by_id.items():
            self.assertAlmostEqual(dc, 0.5 * L, delta=0.05)

    def test_robust_to_element_ordering(self):
        ref = _make_panel([0, 1, 2, 3])
        shuffled = _make_panel([2, 0, 3, 1])
        ref_by_id = {e.id: a for e, a in zip(ref.elms, ref.elms_areas)}
        shuf_by_id = {e.id: a for e, a in zip(shuffled.elms, shuffled.elms_areas)}
        # results are independent of input ordering up to the grid resolution
        for eid in ref_by_id:
            self.assertAlmostEqual(ref_by_id[eid], shuf_by_id[eid], delta=0.05)


class TestAreaLoadEquilibrium(unittest.TestCase):
    """End-to-end: the sum of support reactions must equal the total applied
    pressure resultant (exact global equilibrium), for both a vertical and a
    horizontal (axial-exercising) pressure case."""

    @classmethod
    def setUpClass(cls):
        cls.mdl, _ = run_from_file(_data_path("area_load_panel.dat"))

    def _reaction_sum(self, lc, dof):
        total = 0.0
        for c in self.mdl.cons:
            total += c.nd.reacts[lc, dof]
        return total

    def test_vertical_pressure_resultant(self):
        # LC 0: pz = -5 kN/m2 over 16 m2 -> |Fz| = 80 kN
        self.assertAlmostEqual(abs(self._reaction_sum(0, 2)), 80.0e3, delta=1.0)
        # no spurious horizontal resultant
        self.assertAlmostEqual(self._reaction_sum(0, 0), 0.0, delta=1.0)
        self.assertAlmostEqual(self._reaction_sum(0, 1), 0.0, delta=1.0)

    def test_horizontal_pressure_resultant(self):
        # LC 1: px = 3 kN/m2 over 16 m2 -> |Fx| = 48 kN (axial component preserved)
        self.assertAlmostEqual(abs(self._reaction_sum(1, 0)), 48.0e3, delta=1.0)
        self.assertAlmostEqual(self._reaction_sum(1, 1), 0.0, delta=1.0)
        self.assertAlmostEqual(self._reaction_sum(1, 2), 0.0, delta=1.0)


class TestAreaLoadViewerWloads(unittest.TestCase):
    """Force diagrams use local_wloads; ALOD must be included like GLOD."""

    @classmethod
    def setUpClass(cls):
        from stb_engine import run_from_file
        cls.mdl, _ = run_from_file(_data_path("area_load_panel.dat"))

    def test_local_wloads_includes_alds(self):
        from stb_gui.model_json import _elem_local_wloads
        e = next(x for x in self.mdl.elms if x.alds is not None)
        w = _elem_local_wloads(e, self.mdl, 0)
        a = e.alds[:, 0]
        self.assertAlmostEqual(w[2], a[2], places=3)
        self.assertLess(w[2], 0.0)


if __name__ == "__main__":
    unittest.main()
