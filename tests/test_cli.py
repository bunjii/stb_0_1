import os
import sys
import subprocess
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_stb(args):
    cmd = [sys.executable, "-m", "stb_cli"] + args
    return subprocess.run(
        cmd,
        cwd=_STB_ROOT,
        capture_output=True,
        text=True,
    )


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class TestStbCli(unittest.TestCase):

    def test_version(self):
        r = _run_stb(["version"])
        self.assertEqual(r.returncode, 0)
        self.assertTrue("stb 0.1.0" in r.stdout)

    def test_validate_input01(self):
        r = _run_stb(["validate", _data_path("input01.dat"), "-v"])
        self.assertEqual(r.returncode, 0)
        self.assertTrue("nodes:" in r.stdout)

    def test_validate_missing_file(self):
        r = _run_stb(["validate", "data/no_such_file.dat"])
        self.assertEqual(r.returncode, 1)
        self.assertTrue("not found" in r.stderr)

    def test_solve_input01_to_file(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        out_path = os.path.join(out_dir, "cli_out.dat")

        r = _run_stb([
            "solve",
            _data_path("input01.dat"),
            "-o",
            out_path,
            "-q",
            "-v",
        ])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(os.path.isfile(out_path))
        f = open(out_path, "r")
        txt = f.read()
        f.close()
        self.assertTrue("NDSP" in txt)

    def test_solve_invalid_input(self):
        r = _run_stb(["solve", _data_path("input01.dat") + ".missing", "-q"])
        self.assertEqual(r.returncode, 1)

    def test_solve_parse_error(self):
        bad = os.path.join(_STB_ROOT, "tests", "_tmp_out", "bad_elem.dat")
        out_dir = os.path.dirname(bad)
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        f = open(bad, "w")
        f.write("ELEM,0,1,2,0\n")
        f.close()

        r = _run_stb(["solve", bad, "-q"])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
