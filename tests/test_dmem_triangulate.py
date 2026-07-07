import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui.dmem_triangulate import triangulate_node_selection


class TestDmemTriangulate(unittest.TestCase):

    def test_three_nodes_single_triangle(self):
        coords = {
            1: (0.0, 0.0, 0.0),
            2: (1.0, 0.0, 0.0),
            3: (0.0, 1.0, 0.0),
        }
        tris = triangulate_node_selection(coords, [1, 2, 3])
        self.assertEqual(len(tris), 1)
        self.assertEqual(set(tris[0]), {1, 2, 3})

    def test_rectangular_grid_produces_two_triangles(self):
        coords = {
            1: (0.0, 0.0, 3.0),
            2: (1.0, 0.0, 3.0),
            3: (0.0, 1.0, 3.0),
            4: (1.0, 1.0, 3.0),
        }
        tris = triangulate_node_selection(coords, [1, 2, 3, 4])
        self.assertEqual(len(tris), 2)
        for tri in tris:
            self.assertEqual(len(set(tri)), 3)

    def test_three_by_three_grid_produces_eight_triangles(self):
        coords = {}
        nid = 1
        for j in range(3):
            for i in range(3):
                coords[nid] = (float(i), float(j), 3.0)
                nid += 1
        tris = triangulate_node_selection(coords, list(range(1, 10)))
        self.assertEqual(len(tris), 8)

    def test_three_by_two_grid_produces_four_triangles(self):
        coords = {}
        nid = 1
        for j in range(2):
            for i in range(3):
                coords[nid] = (float(i), float(j), 3.0)
                nid += 1
        tris = triangulate_node_selection(coords, list(range(1, 7)))
        self.assertEqual(len(tris), 4)


if __name__ == "__main__":
    unittest.main()
