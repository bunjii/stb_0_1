import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file
from stb_practice import build_structural_indices
from stb_project import load_project_for_dat


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class TestStructuralIndices(unittest.TestCase):

    def test_builds_indices_for_uk_diaphragm_sample(self):
        dat_path = _data_path("UK_240416_floors_1to3_diaphragm.dat")
        mdl, _txt = run_from_file(dat_path)
        project = load_project_for_dat(dat_path, required=True)

        result = build_structural_indices(mdl, project)

        self.assertGreaterEqual(len(result.lateral_cases), 1)
        self.assertGreater(len(result.story_drifts), 0)
        self.assertEqual(len(result.eccentricities), len(project.stories))
        self.assertGreater(len(result.rigidity_ratios), 0)
        self.assertTrue("story_drifts" in result.tables)
        self.assertTrue(any(row.is_story_max for row in result.story_drifts))


if __name__ == "__main__":
    unittest.main()
