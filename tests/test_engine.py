import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file, run_from_lines, StbParseError, StbSolveError
from stb_engine.errors import StbError
from stb_engine.run import parse_input


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class TestStbEngine(unittest.TestCase):

    def test_run_from_file_input01(self):
        mdl, txt = run_from_file(_data_path("input01.dat"))

        self.assertTrue(mdl != None)
        self.assertEqual(len(mdl.nds), 8)
        self.assertEqual(len(mdl.elms), 8)
        self.assertTrue(mdl.date_analysis != None)
        self.assertTrue("# --- NODAL DISPLACEMENT ---" in txt)
        self.assertTrue("NDSP" in txt)
        self.assertTrue("REAC" in txt)
        self.assertTrue("EFRC" in txt)

    def test_run_from_file_writes_output(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        out_path = os.path.join(out_dir, "engine.out")

        mdl, txt = run_from_file(_data_path("input01.dat"), out_path)

        self.assertTrue(os.path.isfile(out_path))
        f = open(out_path, "r")
        saved = f.read()
        f.close()
        self.assertEqual(saved, txt)
        self.assertTrue(mdl.lcs != None)

    def test_parse_error_on_invalid_input(self):
        raised = False
        try:
            parse_input(["ELEM,0,1,2,0"])
        except StbParseError:
            raised = True

        self.assertTrue(raised)

    def test_solve_error_on_loaded_mechanism(self):
        lines = [
            "MATE, 1, M, 205000, 79000, 78.5, 1.2e-5, 235",
            "SECT, 1, S, 1, 0, 100, 100",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 0, 0, 3",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "PLOD, 2, 1, 1, 0, 0, 0, 0, 0",
        ]

        with self.assertRaises(StbSolveError):
            run_from_lines(lines)

    def test_stb_error_base(self):
        self.assertTrue(issubclass(StbParseError, StbError))


if __name__ == "__main__":
    unittest.main()
