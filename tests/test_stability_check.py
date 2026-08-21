"""Tests for the stability check across both of its eigensolver paths.

CheckStability uses a dense symmetric eigensolve below DENSE_EIGEN_MAX_DOF and
a shift-invert Lanczos pass (reusing the solve's LU) above it. Every model in
data/ is under that threshold, so the sparse path would otherwise ship
untested. Each case here runs both paths and requires them to agree.
"""

import os
import sys
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
if os.path.join(_STB_ROOT, "classes") not in sys.path:
    sys.path.insert(0, os.path.join(_STB_ROOT, "classes"))

import solve as solve_module

from stb_engine import parse_input, read_input_file, solve_model

_BASE_MODEL = os.path.join(_STB_ROOT, "data", "UK_240416.dat")

# Forces the dense path / forces the shift-invert path on any model size.
_PATHS = [("dense", 10 ** 9), ("sparse", 0)]


class _ForcePath(object):
    """Pin DENSE_EIGEN_MAX_DOF so a given eigensolver path is exercised."""

    def __init__(self, threshold):
        self.threshold = threshold

    def __enter__(self):
        self.saved = solve_module.DENSE_EIGEN_MAX_DOF
        solve_module.DENSE_EIGEN_MAX_DOF = self.threshold

    def __exit__(self, *exc):
        solve_module.DENSE_EIGEN_MAX_DOF = self.saved
        return False


class TestStabilityCheck(unittest.TestCase):

    def setUp(self):
        if not os.path.isfile(_BASE_MODEL):
            self.skipTest("sample model not present")
        self.base = read_input_file(_BASE_MODEL)

    def _solve(self, lines, threshold):
        with _ForcePath(threshold):
            mdl = parse_input(lines)
            solve_model(mdl)
        return mdl

    def test_sound_model_is_accepted_by_both_paths(self):
        results = {}
        for name, threshold in _PATHS:
            mdl = self._solve(self.base, threshold)
            results[name] = np.concatenate([n.disps.ravel() for n in mdl.nds])

        # The check must not perturb the solution, only accept or reject it.
        np.testing.assert_array_equal(results["dense"], results["sparse"])

    def test_near_mechanism_is_rejected_by_both_paths(self):
        # A loaded node hanging off a hair-thin member: stiffness many orders
        # of magnitude below the rest of the structure, but not exactly zero.
        lines = self.base + [
            "SECT, 9001, TINY, 1, 0, 0.06, 0.06",
            "NODE, 9001, 0, 0, 99",
            "ELEM, 9001, 9001, 1, 9001, 0.0",
            "PLOD, 9001, 0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0",
        ]

        for name, threshold in _PATHS:
            with self.assertRaises(Exception) as ctx:
                self._solve(lines, threshold)
            self.assertIn("unstable or ill-conditioned", str(ctx.exception),
                          msg="{0} path missed the mechanism".format(name))

    def test_sound_model_skips_the_eigensolve(self):
        # The condition estimate exists to keep sound models off the eigensolver.
        # Without this test a mis-set threshold could quietly restore the old
        # cost while every other test still passed.
        calls = []
        original = solve_module.Solve.LowStiffnessModes

        def counting(self, _kG, _lu=None):
            calls.append(1)
            return original(self, _kG, _lu)

        solve_module.Solve.LowStiffnessModes = counting
        try:
            self._solve(self.base, 0)
        finally:
            solve_module.Solve.LowStiffnessModes = original

        self.assertEqual(calls, [], "sound model should not reach the eigensolver")

    def test_unrestrained_node_reports_singular_matrix(self):
        lines = self.base + [
            "NODE, 9002, 0, 0, 99",
            "PLOD, 9002, 0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0",
        ]

        for name, threshold in _PATHS:
            with self.assertRaises(Exception) as ctx:
                self._solve(lines, threshold)
            self.assertIn("singular", str(ctx.exception),
                          msg="{0} path missed the free node".format(name))


if __name__ == "__main__":
    unittest.main()
