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
            "DIAP, 10, 2F_MAIN, 1, 1, 2.0, 1000, 0, 0.006666666666666667, 1820",
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
            "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
            "DREG, 1, 1, 2, 3",
            "DMEM, 1, 1, 1, 2, 3",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 0, 1, 1, 1, 1, 1",
            "CONS, 3, 1, 0, 1, 1, 1, 1",
            "DLOD, 1, 0, 0, 6.0, 0.0",
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
            "DIAP, 1, R1, 0, 0, , , 0, ,",
            "DREG, 1, 1, 2, 3, 4",
        ])

        self.assertEqual(mdl.diaps[0].type, "RIGID")
        self.assertEqual(len(mdl.mpcs), 6)

    def test_auto_dreg_from_dmem_when_dreg_omitted(self):
        lines = [
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1, 0, 0",
            "NODE, 3, 1, 1, 0",
            "NODE, 4, 0, 1, 0",
            "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
            "DMEM, 1, 1, 1, 2, 3",
            "DMEM, 2, 1, 1, 3, 4",
        ]
        mdl = parse_input(lines)
        self.assertEqual(len(mdl.dregs), 1)
        self.assertTrue(mdl.dregs[0].auto_generated)
        self.assertEqual(set(mdl.dregs[0].node_ids), {1, 2, 3, 4})
        self.assertTrue(any("DREG was omitted" in w for w in mdl.input_warnings))

    def test_dreg_mismatch_with_dmem_emits_warning(self):
        lines = [
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1, 0, 0",
            "NODE, 3, 1, 1, 0",
            "NODE, 4, 0, 1, 0",
            "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
            "DREG, 1, 1, 2, 3",
            "DMEM, 1, 1, 1, 2, 3",
            "DMEM, 2, 1, 1, 3, 4",
        ]
        mdl = parse_input(lines)
        self.assertTrue(any("differs from DMEM outer boundary" in w for w in mdl.input_warnings))

    def test_hmax_emits_unused_field_warning(self):
        mdl = parse_input([
            "DIAP, 10, 2F_MAIN, 1, 1, 2.0, 1000, 0, 0.006666666666666667, 1820",
        ])
        self.assertTrue(any("HMAX=" in w and "metadata only" in w for w in mdl.input_warnings))

    def test_dopn_emits_unused_field_warning(self):
        mdl = parse_input([
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1, 0, 0",
            "NODE, 3, 0, 1, 0",
            "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
            "DOPN, 1, 1, 2, 3",
        ])
        self.assertTrue(any("DOPN records were supplied" in w for w in mdl.input_warnings))

    def test_dcon_spacing_emits_unused_field_warning(self):
        mdl = parse_input([
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
            "DCON, 1, 1, 10, 0, 0.01, 0.5",
        ])
        self.assertTrue(any("DCON SPACING" in w for w in mdl.input_warnings))


if __name__ == "__main__":
    unittest.main()
