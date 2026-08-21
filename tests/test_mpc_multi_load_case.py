"""Regression tests for MPC (rigid diaphragm) models with several load cases.

spsolve returns a sparse matrix when the right-hand side is sparse and has more
than one column. Expanding the reduced solution back through the MPC transform
used to feed that sparse result straight into np.asarray, which produced a 0-d
object array and made the solve fail for every rigid-diaphragm model with two
or more load cases.
"""

import os
import sys
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input, read_input_file, solve_model

# Square single-storey frame with a rigid floor diaphragm and three load cases.
_FLOOR_NODE_IDS = [11, 12, 13, 14]

_LINES = [
    "MATE, 1, STEEL, 205000, 79000, 78.5, 1.2e-5, 235",
    "SECT, 1, C1, 1, 0, 300, 300",
    "NODE, 1, 0, 0, 0",
    "NODE, 2, 4, 0, 0",
    "NODE, 3, 4, 4, 0",
    "NODE, 4, 0, 4, 0",
    "NODE, 11, 0, 0, 3",
    "NODE, 12, 4, 0, 3",
    "NODE, 13, 4, 4, 3",
    "NODE, 14, 0, 4, 3",
    "ELEM, 1, 1, 11, 1, 0.0",
    "ELEM, 2, 2, 12, 1, 0.0",
    "ELEM, 3, 3, 13, 1, 0.0",
    "ELEM, 4, 4, 14, 1, 0.0",
    "CONS, 1, 1, 1, 1, 1, 1, 1",
    "CONS, 2, 1, 1, 1, 1, 1, 1",
    "CONS, 3, 1, 1, 1, 1, 1, 1",
    "CONS, 4, 1, 1, 1, 1, 1, 1",
    "DIAP, 1, F1, 0, 0, , , 0.0, , ",
    "DREG, 1, 11, 12, 13, 14",
    "PLOD, 11, 0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0",
    "PLOD, 12, 1, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0",
    "PLOD, 13, 2, 7.0, 3.0, 0.0, 0.0, 0.0, 0.0",
]


def _solved_model(lines):
    mdl = parse_input(lines)
    solve_model(mdl)
    return mdl


class TestMpcMultiLoadCase(unittest.TestCase):

    def test_rigid_diaphragm_solves_with_multiple_load_cases(self):
        mdl = _solved_model(_LINES)

        self.assertGreater(len(mdl.mpcs), 0, "model should generate rigid-diaphragm MPCs")
        self.assertEqual(mdl.max_clc, 3)

        by_id = {n.id: n for n in mdl.nds}
        for nid in _FLOOR_NODE_IDS:
            disps = by_id[nid].disps
            self.assertEqual(disps.shape, (6, 3))
            self.assertTrue(np.all(np.isfinite(disps)))

        # A load case acting only in Y must not leave the floor undeflected in Y.
        self.assertGreater(abs(by_id[12].disps[1, 1]), 0.0)

    def test_single_load_case_still_solves(self):
        mdl = _solved_model([l for l in _LINES if not l.startswith("PLOD, 12")
                             and not l.startswith("PLOD, 13")])

        self.assertGreater(len(mdl.mpcs), 0)
        self.assertEqual(mdl.max_clc, 1)
        by_id = {n.id: n for n in mdl.nds}
        self.assertEqual(by_id[11].disps.shape, (6, 1))

    def test_diaphragm_stays_rigid_in_every_load_case(self):
        mdl = _solved_model(_LINES)
        by_id = {n.id: n for n in mdl.nds}
        nodes = [by_id[nid] for nid in _FLOOR_NODE_IDS]

        for lc in range(mdl.max_clc):
            scale = max(abs(n.disps[0, lc]) + abs(n.disps[1, lc]) for n in nodes)
            for a in nodes:
                for b in nodes:
                    dx = b.x - a.x
                    dy = b.y - a.y
                    dux = b.disps[0, lc] - a.disps[0, lc]
                    duy = b.disps[1, lc] - a.disps[1, lc]
                    # In-plane rigid motion keeps every chord unstretched.
                    stretch = dux * dx + duy * dy
                    span = max(abs(dx) + abs(dy), 1.0)
                    self.assertAlmostEqual(
                        stretch / (span * max(scale, 1.0e-30)), 0.0, places=6,
                        msg="chord {0}-{1} stretched in load case {2}".format(a.id, b.id, lc),
                    )

    def test_repo_rigid_diaphragm_model_solves(self):
        path = os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_rigid_diaphragm.dat")
        if not os.path.isfile(path):
            self.skipTest("sample model not present")

        mdl = _solved_model(read_input_file(path))

        self.assertGreater(len(mdl.mpcs), 0)
        self.assertGreater(mdl.max_clc, 1)
        for n in mdl.nds:
            self.assertEqual(n.disps.shape, (6, mdl.max_clc))
            self.assertTrue(np.all(np.isfinite(n.disps)))


if __name__ == "__main__":
    unittest.main()
