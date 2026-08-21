import os
import subprocess
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

_HEAVY_MODULES = (
    "numpy",
    "scipy",
    "fastapi",
    "uvicorn",
    "stb_engine",
    "stb_loads",
    "stb_practice",
    "shapely",
)


class TestGuiStartupImports(unittest.TestCase):

    def test_server_module_import_stays_lightweight(self):
        code = (
            "import sys\n"
            "import stb_gui.server\n"
            "heavy = [m for m in %r if m in sys.modules]\n"
            "assert not heavy, heavy\n"
        ) % (_HEAVY_MODULES,)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_STB_ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": _STB_ROOT},
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )

    def test_model_json_import_does_not_load_numpy(self):
        code = (
            "import sys\n"
            "import stb_gui.model_json\n"
            "assert 'numpy' not in sys.modules\n"
            "stb_gui.model_json.list_model_files()\n"
            "assert 'numpy' not in sys.modules\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_STB_ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": _STB_ROOT},
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
