import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLASSES_DIR = os.path.join(_STB_ROOT, "classes")
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from diaphragm import TIMBER_UNIT_SHEAR_STRENGTH
from stb_engine import parse_input, solve_model


class TestDiaphragmFeatures(unittest.TestCase):

    def test_timber_floor_multiplier_creates_equivalent_material(self):
        mdl = parse_input([
            "DIAP, 10, 2F_MAIN, SEMI, TIMBER_FLOOR, FLOOR_MAG=2.0, THETA=0, HMAX=1820",
        ])

        self.assertEqual(len(mdl.dmats), 1)
        self.assertEqual(mdl.diaps[0].type, "SEMI_RIGID")
        self.assertEqual(mdl.diaps[0].source, "TIMBER_FLOOR")
        self.assertAlmostEqual(mdl.diaps[0].hmax, 1.82)
        self.assertAlmostEqual(
            mdl.dmats[0].equivalent_gt,
            2.0 * TIMBER_UNIT_SHEAR_STRENGTH / (1.0 / 150.0),
        )

    def test_diaphragm_area_load_is_added_to_membrane_nodes(self):
        lines = [
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1, 0, 0",
            "NODE, 3, 0, 1, 0",
            "DIAP, 1, F1, SEMI, DMAT=1, T=100, THETA=0",
            "DMEM, 1, 1, 1, 2, 3",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 0, 1, 1, 1, 1, 1",
            "CONS, 3, 1, 0, 1, 1, 1, 1",
            "DLOD, 1, 0, AREA, PX=6.0, PY=0.0",
        ]
        mdl = parse_input(lines)
        solve_model(mdl)

        self.assertEqual(len(mdl.dloads), 1)
        self.assertGreater(mdl.nds[1].disps[0, 0], 0.0)

    def test_rigid_diaphragm_region_generates_horizontal_mpcs(self):
        mdl = parse_input([
            "NODE, 1, 0, 0, 3",
            "NODE, 2, 4, 0, 3",
            "NODE, 3, 4, 3, 3",
            "NODE, 4, 0, 3, 3",
            "DIAP, 1, R1, RIGID",
            "DREG, 1, 1, 2, 3, 4",
        ])

        self.assertEqual(mdl.diaps[0].type, "RIGID")
        self.assertEqual(len(mdl.mpcs), 6)


if __name__ == "__main__":
    unittest.main()
