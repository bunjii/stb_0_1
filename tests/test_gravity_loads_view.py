import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
_CLASSES = os.path.join(_STB_ROOT, "classes")
if _CLASSES not in sys.path:
    sys.path.insert(0, _CLASSES)

from stb_engine import parse_input
from stb_gui.loads_view import build_dead_loads_view, build_live_loads_view, LOAD_VERIFY_TABS
from stb_project import load_project_file


def _read_dat(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


class TestGravityLoadsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dat_path = os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.dat")
        cls.project_path = os.path.join(
            _STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.project.json"
        )
        if not os.path.isfile(cls.dat_path):
            raise unittest.SkipTest("UK sample missing")
        cls.project = load_project_file(cls.project_path)
        cls.mdl = parse_input(_read_dat(cls.dat_path))

    def test_tab_order_and_labels(self):
        ids = [t["id"] for t in LOAD_VERIFY_TABS]
        self.assertEqual(ids, ["dead", "live", "snow", "seismic", "wind"])
        self.assertEqual(LOAD_VERIFY_TABS[3]["label"], "地震荷重")

    def test_dead_load_view_lc0(self):
        view = build_dead_loads_view(self.mdl, self.project, "data/UK_240416_floors_1to3_diaphragm.dat")
        self.assertEqual(view["kind"], "dead")
        self.assertEqual(view["active_tab"], "dead")
        self.assertFalse(view["can_apply_dlod"])
        self.assertIn(0, view["load_cases"])
        lc0 = next(r for r in view["lc_rows"] if r["load_case"] == "0")
        # Applied dead load must match the vertical reaction whatever the
        # sample model contains.
        self.assertAlmostEqual(lc0["wi_kN"], lc0["reaction_tz_kN"], places=6)
        self.assertTrue(lc0["equilibrium_ok"])
        # Snapshot of the current sample; update deliberately when it changes.
        self.assertAlmostEqual(lc0["wi_kN"], 252.362, places=2)
        self.assertTrue(all(c["ok"] for c in view["checks"]))

    def test_live_load_view_lc2(self):
        view = build_live_loads_view(self.mdl, self.project, "data/UK_240416_floors_1to3_diaphragm.dat")
        self.assertEqual(view["kind"], "live")
        self.assertIn(2, view["load_cases"])
        lc2 = next(r for r in view["lc_rows"] if r["load_case"] == "2")
        self.assertGreater(lc2["wi_kN"], 0.0)
        self.assertTrue(lc2["equilibrium_ok"])


if __name__ == "__main__":
    unittest.main()
