import json
import os
import shutil
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui.project_view import default_project_dict_for_dat, save_project_json_for_model
from stb_project import validate_project_dict
from stb_project.floor_loads import sync_project_floor_dlod_lines
from stb_project.load_names import sync_project_lnme_lines


class TestProjectFloorLoadSync(unittest.TestCase):

    def test_sync_project_lnme_and_floor_dlod_lines(self):
        raw = default_project_dict_for_dat("data/model.dat")
        raw["load_conditions"] = {
            "floor_loads": [
                {
                    "diaphragm_id": 10,
                    "role": "LL",
                    "load_case": 8,
                    "name": "LL",
                    "pressure_kN_m2": 1.8,
                },
                {
                    "diaphragm_id": 10,
                    "role": "LL_E",
                    "load_case": 9,
                    "name": "LL(E)",
                    "pressure_kN_m2": 0.8,
                },
            ],
        }
        project = validate_project_dict(raw)
        lines = [
            "# --- LOAD NAME(LNME) ---",
            "LNME,      8,    7, OLD",
            "# --- DIAPHRAGM LOAD(DLOD) ---",
            "DIAP,     10,  FLOOR,    1,    1,      1.0,     1000,        0,  0.006666667,      910",
            "DLOD,     10,    8,    4,      9.9,      0.0,      0.0",
        ]

        updated = sync_project_lnme_lines(lines, project)
        updated = sync_project_floor_dlod_lines(updated, project)
        text = "\n".join(updated)

        self.assertIn("PROJECT LNME (auto)", text)
        self.assertIn("LNME,      8,    2,         LL", text)
        self.assertIn("LNME,      9,    3,      LL(E)", text)
        self.assertIn("PROJECT FLOOR DLOD (auto)", text)
        self.assertIn("DLOD,     10,    8,    4,        1.8,        0.0,        0.0", text)
        self.assertIn("DLOD,     10,    9,    4,        0.8,        0.0,        0.0", text)
        self.assertNotIn("9.9", text)

    def test_save_project_json_syncs_dat(self):
        rel = "data/_tmp_project_floor_load_sync.dat"
        dat_path = os.path.join(_STB_ROOT, rel)
        project_path = os.path.splitext(dat_path)[0] + ".project.json"
        src = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.dat")
        try:
            shutil.copyfile(src, dat_path)
            raw = default_project_dict_for_dat(rel)
            raw["load_conditions"] = {
                "diaphragms": [{"id": 10, "story": "2"}],
                "floor_loads": [
                    {
                        "story": "2",
                        "diaphragm_id": 10,
                        "role": "LL",
                        "load_case": 8,
                        "name": "LL",
                        "pressure_kN_m2": 1.8,
                    },
                    {
                        "story": "2",
                        "diaphragm_id": 10,
                        "role": "LL_E",
                        "load_case": 9,
                        "name": "LL(E)",
                        "pressure_kN_m2": 0.8,
                    },
                ],
            }

            view = save_project_json_for_model(rel, raw)
            self.assertTrue(view["found"])
            with open(dat_path, "r", encoding="utf-8") as f:
                text = f.read()
            self.assertIn("PROJECT LNME (auto)", text)
            self.assertIn("PROJECT FLOOR DLOD (auto)", text)
            self.assertIn("LNME,      8,    2,         LL", text)
            self.assertIn("LNME,      9,    3,      LL(E)", text)
            self.assertIn("DLOD,     10,    8,    4,        1.8,        0.0,        0.0", text)
            self.assertIn("DLOD,     10,    9,    4,        0.8,        0.0,        0.0", text)
            self.assertTrue(os.path.isfile(project_path))
        finally:
            for path in (dat_path, project_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_save_project_json_regenerates_seismic_dlod_from_floor_loads(self):
        rel = "data/_tmp_project_floor_load_seismic_sync.dat"
        dat_path = os.path.join(_STB_ROOT, rel)
        project_path = os.path.splitext(dat_path)[0] + ".project.json"
        src_dat = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.dat")
        src_project = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        try:
            shutil.copyfile(src_dat, dat_path)
            with open(src_project, "r", encoding="utf-8") as f:
                raw = json.load(f)
            raw["model"]["dat"] = os.path.basename(dat_path)
            raw["load_conditions"]["floor_loads"] = [
                {
                    "story": "1",
                    "diaphragm_id": 10,
                    "role": "LL_E",
                    "load_case": 1,
                    "name": "LL(E)",
                    "pressure_kN_m2": 0.8,
                },
            ]

            save_project_json_for_model(rel, raw)
            with open(dat_path, "r", encoding="utf-8") as f:
                text = f.read()

            self.assertIn("PROJECT FLOOR DLOD (auto)", text)
            self.assertIn("DLOD,     10,    1,    4,        0.8,        0.0,        0.0", text)
            self.assertIn("SEISMIC DLOD (auto)", text)
            self.assertNotIn("DLOD,     10,    2,    0,      0.151,        0.0", text)
            self.assertNotIn("DLOD,     10,    3,    0,        0.0,      0.151", text)
        finally:
            for path in (dat_path, project_path):
                if os.path.exists(path):
                    os.remove(path)


if __name__ == "__main__":
    unittest.main()
