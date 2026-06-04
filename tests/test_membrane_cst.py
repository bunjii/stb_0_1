import os
import sys
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLASSES_DIR = os.path.join(_STB_ROOT, "classes")
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from diaphragm import DiaphragmMaterial
from stb_engine import parse_input, solve_model, format_results


class TestCSTMembrane(unittest.TestCase):

    def test_isotropic_d_matrix_is_rotation_invariant(self):
        e = 200.0e9
        nu = 0.3
        g = e / (2.0 * (1.0 + nu))
        mat = DiaphragmMaterial(1, "ISO", e, e, g, nu)

        d0 = mat.DRotated(0.0)
        d45 = mat.DRotated(45.0)
        d90 = mat.DRotated(90.0)

        self.assertTrue(np.allclose(d0, d45, rtol=1e-10, atol=1e-4))
        self.assertTrue(np.allclose(d0, d90, rtol=1e-10, atol=1e-4))

    def test_cst_rigid_body_translation_has_zero_strain(self):
        lines = [
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1, 0, 0",
            "NODE, 3, 0, 1, 0",
            "DIAP, 1, F1, SEMI, DMAT=1, T=100, THETA=0",
            "DMEM, 1, 1, 1, 2, 3",
        ]
        mdl = parse_input(lines)
        mem = mdl.dmems[0]
        u = np.array([1.2, -0.4, 1.2, -0.4, 1.2, -0.4])

        self.assertTrue(np.allclose(mem.B @ u, np.zeros(3), atol=1e-12))

    def test_minimal_membrane_model_solves_and_outputs_stress(self):
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
            "PLOD, 2, 0, 1.0, 0, 0, 0, 0, 0",
        ]
        mdl = parse_input(lines)
        solve_model(mdl)
        txt = format_results(mdl)

        self.assertEqual(len(mdl.dmems), 1)
        self.assertTrue(mdl.nds[1].disps[0, 0] > 0.0)
        self.assertTrue(mdl.dmems[0].strains is not None)
        self.assertTrue("MSTR" in txt)


if __name__ == "__main__":
    unittest.main()
