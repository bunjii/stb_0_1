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

from nd import Nd
from diaphragm import (
    ASSOC_BOUNDARY,
    ASSOC_EMBEDDED,
    CONN_CONNECTED_RIGID,
    HOST_EDGE,
    HOST_TRIANGLE,
    edge_shape_weights,
    triangle_shape_weights,
)
from stb_engine import parse_input, solve_model


class TestDiaphragmConnectionGeometry(unittest.TestCase):

    def test_edge_shape_weights(self):
        a = Nd(1, 0.0, 0.0, 0.0)
        b = Nd(2, 2.0, 0.0, 0.0)

        self.assertTrue(np.allclose(edge_shape_weights((1.0, 0.0, 0.0), a, b)[1], [0.5, 0.5]))
        self.assertTrue(np.allclose(edge_shape_weights((0.0, 0.0, 0.0), a, b)[1], [1.0, 0.0]))
        self.assertTrue(np.allclose(edge_shape_weights((2.0, 0.0, 0.0), a, b)[1], [0.0, 1.0]))
        self.assertIsNone(edge_shape_weights((1.0, 0.1, 0.0), a, b, tolerance=0.01))

    def test_triangle_shape_weights(self):
        a = Nd(1, 0.0, 0.0, 0.0)
        b = Nd(2, 3.0, 0.0, 0.0)
        c = Nd(3, 0.0, 3.0, 0.0)

        self.assertTrue(np.allclose(
            triangle_shape_weights((1.0, 1.0, 0.0), a, b, c),
            [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
        ))
        self.assertTrue(np.allclose(triangle_shape_weights((0.0, 0.0, 0.0), a, b, c), [1.0, 0.0, 0.0]))
        self.assertTrue(np.allclose(triangle_shape_weights((1.5, 0.0, 0.0), a, b, c), [0.5, 0.5, 0.0]))
        self.assertIsNone(triangle_shape_weights((4.0, 0.0, 0.0), a, b, c))


def _base_lines(dcon_line=None):
    lines = [
        "MATE, 1, STEEL, 205000, 79000, 78.5, 1.2e-5, 235",
        "SECT, 1, B1, 1, 0, 200, 200",
        "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
        "NODE, 1, 0, 0, 0",
        "NODE, 2, 2, 0, 0",
        "NODE, 3, 0, 2, 0",
        "NODE, 4, 1, 0, 0",
        "NODE, 5, 1, 1, 0",
        "ELEM, 10, 4, 5, 1, 0",
        "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
        "DMEM, 1, 1, 1, 2, 3",
        "CONS, 1, 1, 1, 1, 1, 1, 1",
        "CONS, 2, 1, 1, 1, 1, 1, 1",
        "CONS, 3, 1, 1, 1, 1, 1, 1",
        "CONS, 4, 0, 0, 1, 1, 1, 1",
        "CONS, 5, 1, 1, 1, 1, 1, 1",
        "PLOD, 4, 0, 1.0, 0, 0, 0, 0, 0",
    ]
    if dcon_line is not None:
        lines.append(dcon_line)
    return lines


class TestDiaphragmConnectionMPC(unittest.TestCase):

    def test_boundary_member_mpc_generation(self):
        mdl = parse_input(_base_lines("DCON, 1, 1, 10, 0, 0.01"))

        self.assertEqual(len(mdl.dcons), 1)
        self.assertEqual(len(mdl.dassocs), 1)
        self.assertEqual(mdl.dassocs[0].association_type, ASSOC_BOUNDARY)
        self.assertEqual(mdl.dassocs[0].connection_type, CONN_CONNECTED_RIGID)
        self.assertEqual(len(mdl.mpcs), 2)

        cp = mdl.dassocs[0].generated_constraint_points[0]
        self.assertEqual(cp.host_type, HOST_EDGE)
        self.assertTrue(np.allclose(cp.shape_function_weights, [0.5, 0.5]))
        self.assertEqual(sorted([m.slave_dof % 6 for m in mdl.mpcs]), [0, 1])

    def test_embedded_member_mpc_generation(self):
        lines = _base_lines("DCON, 1, 1, 10, 0, 0.01")
        lines[6] = "NODE, 4, 0.5, 0.5, 0"
        mdl = parse_input(lines)

        self.assertEqual(mdl.dassocs[0].association_type, ASSOC_EMBEDDED)
        cp = mdl.dassocs[0].generated_constraint_points[0]
        self.assertEqual(cp.host_type, HOST_TRIANGLE)
        self.assertTrue(np.allclose(cp.shape_function_weights, [0.5, 0.25, 0.25]))

    def test_disconnected_member_generates_no_mpcs(self):
        mdl = parse_input(_base_lines("DCON, 1, 1, 10, 1, 0.01"))

        self.assertEqual(len(mdl.mpcs), 0)
        self.assertEqual(mdl.dassocs[0].association_type, "none")

    def test_mpc_changes_analysis_behavior(self):
        disconnected = parse_input(_base_lines(None))
        solve_model(disconnected)
        ux_free = disconnected.FindNodeFromId(4).disps[0, 0]

        connected = parse_input(_base_lines("DCON, 1, 1, 10, 0, 0.01"))
        solve_model(connected)
        ux_tied = connected.FindNodeFromId(4).disps[0, 0]

        self.assertGreater(abs(ux_free), 1e-12)
        self.assertAlmostEqual(ux_tied, 0.0, places=12)
        self.assertNotAlmostEqual(ux_free, ux_tied, places=12)

    def test_connected_boundary_reduces_weak_axis_moment_from_line_load(self):
        lines = _base_lines(None)
        # Global horizontal line load on member 10.
        lines.append("ELOD, 10, 0, 1, 2.0, 0.0, 0.0, 2.0, 0.0, 0.0")

        disconnected = parse_input(lines)
        solve_model(disconnected)
        e0 = disconnected.FindElemFromEid(10)
        mz_disconnected = abs(float(e0.forces[5, 0]))
        mz_center_disconnected = abs(float(e0.forces[13, 0]))

        connected = parse_input(lines + ["DCON, 1, 1, 10, 0, 0.01"])
        solve_model(connected)
        e1 = connected.FindElemFromEid(10)
        mz_connected = abs(float(e1.forces[5, 0]))
        mz_center_connected = abs(float(e1.forces[13, 0]))

        self.assertGreater(mz_disconnected, 1e-3)
        self.assertGreater(mz_center_disconnected, 1e-3)
        self.assertLess(mz_connected, mz_disconnected * 0.2)
        self.assertLess(mz_center_connected, mz_center_disconnected * 0.2)


if __name__ == "__main__":
    unittest.main()
