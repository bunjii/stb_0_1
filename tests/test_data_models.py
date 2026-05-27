import os
import sys
import glob
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file


class TestDataModels(unittest.TestCase):

    def test_all_data_dat_files_solve(self):
        pattern = os.path.join(_STB_ROOT, "data", "*.dat")
        paths = sorted(glob.glob(pattern))

        self.assertTrue(len(paths) > 0)

        for path in paths:
            mdl, txt = run_from_file(path)
            self.assertTrue(mdl.lcs != None and len(mdl.lcs) > 0,
                            msg="no load cases: " + path)
            self.assertTrue("NDSP" in txt, msg="no results: " + path)


if __name__ == "__main__":
    unittest.main()
