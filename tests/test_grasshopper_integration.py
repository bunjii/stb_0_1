import os
import sys
import unittest

from grasshopper.stb_analyze_script import run_stb_analyze
from grasshopper.stb_out_parser import parse_stb_out_lines


_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestGrasshopperIntegration(unittest.TestCase):

    def test_parse_stb_out_records(self):
        results = parse_stb_out_lines([
            "# comments are ignored",
            "NDSP, 0, 10, 1.0e-3, 2.0e-3, 3.0e-3, 4.0e-4, 5.0e-4, 6.0e-4",
            "REAC, 0, 10, 1, 2, 3, 4, 5, 6",
            "EFRC, 0, 20, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14",
        ])

        self.assertEqual(len(results.displacements), 1)
        self.assertEqual(results.displacements[0].node_id, 10)
        self.assertEqual(results.displacements[0].x, 1.0e-3)
        self.assertEqual(len(results.reactions), 1)
        self.assertEqual(results.reactions[0].tz, 3)
        self.assertEqual(len(results.element_forces), 1)
        self.assertEqual(results.element_forces[0].mzc, 14)

    def test_run_uk_diaphragm_model_through_grasshopper_script(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)

        out_path = os.path.join(out_dir, "gh_uk_diaphragm.out")
        dat_path = os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.dat")

        result = run_stb_analyze(
            dat_path=dat_path,
            python_exe=sys.executable,
            repo_root=_STB_ROOT,
            run=True,
            out_path=out_path,
            load_case=0,
        )

        self.assertTrue(result.success, msg=result.stderr)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.isfile(result.out_path))
        self.assertTrue("Solved" in result.stdout)
        self.assertTrue(len(result.node_ids) > 0)
        self.assertEqual(set(result.load_cases), {0})
        self.assertEqual(len(result.node_ids), len(result.translations))
        self.assertEqual(len(result.node_ids), len(result.rotations))


if __name__ == "__main__":
    unittest.main()
