import json
import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file
from stb_project import (
    ProjectSchemaError,
    load_project_file,
    load_project_for_dat,
    project_path_for_dat,
    validate_project_dict,
)


def _minimal_project():
    return {
        "schema": 1,
        "model": {"dat": "model.dat"},
        "building": {
            "name": "Sample house",
            "location": "Tokyo",
            "use": "residential",
            "structure": "wood",
            "calculation_route": "route-1",
            "designer": {
                "name": "Designer",
                "qualification": "",
                "license_number": "",
                "contact": "",
            },
        },
        "grids": [
            {"name": "X1", "direction": "x", "coordinate": 0.0},
            {"name": "X2", "direction": "x", "coordinate": 3.64},
            {"name": "Y1", "direction": "y", "coordinate": 0.0},
        ],
        "stories": [
            {"name": "1", "elevation": 0.0, "height": 3.0},
        ],
        "member_classes": [
            {
                "name": "columns",
                "kind": "column",
                "element_ids": [1, 2],
                "story": "1",
                "use": "wood column",
                "notes": "",
            },
        ],
        "report": {
            "title": "Calculation draft",
            "mode": "practice",
            "language": "ja",
            "format": "markdown",
            "include_manual_items": True,
            "include_warnings": True,
        },
    }


class TestProjectSchema(unittest.TestCase):

    def test_validate_minimal_project(self):
        project = validate_project_dict(_minimal_project())

        self.assertEqual(project.schema, 1)
        self.assertEqual(project.dat_path, "model.dat")
        self.assertEqual(project.building.name, "Sample house")
        self.assertEqual(project.grids[1].name, "X2")
        self.assertEqual(project.member_classes[0].kind, "column")
        self.assertEqual(project.report.mode, "practice")

    def test_seismic_rt_must_be_positive(self):
        data = _minimal_project()
        data["load_conditions"] = {"seismic": {"ci": 0.2, "rt": 0.0}}
        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(data)

    def test_seismic_base_mass_policy_round_trip(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {
                "ci": 0.2,
                "base_level": "1",
                "base_mass_policy": "LUMP_TO_ABOVE_DIAPHRAGM",
            }
        }
        project = validate_project_dict(data)
        self.assertEqual(project.load_conditions.seismic.base_level, "1")
        self.assertEqual(
            project.load_conditions.seismic.base_mass_policy,
            "LUMP_TO_ABOVE_DIAPHRAGM",
        )

    def test_seismic_rt_round_trip(self):
        data = _minimal_project()
        data["load_conditions"] = {"seismic": {"ci": 0.2, "rt": 0.85}}
        project = validate_project_dict(data)
        self.assertAlmostEqual(project.load_conditions.seismic.rt, 0.85)
        reparsed = validate_project_dict(project.to_dict())
        self.assertAlmostEqual(reparsed.load_conditions.seismic.rt, 0.85)

    def test_to_dict_round_trip(self):
        project = validate_project_dict(_minimal_project())
        reparsed = validate_project_dict(project.to_dict())

        self.assertEqual(reparsed.to_dict(), project.to_dict())

    def test_rejects_unknown_member_kind(self):
        data = _minimal_project()
        data["member_classes"][0]["kind"] = "wall"

        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(data)

    def test_rejects_duplicate_grid_names_per_direction(self):
        data = _minimal_project()
        data["grids"].append({"name": "X1", "direction": "x", "coordinate": 9.1})

        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(data)

    def test_sidecar_path_and_optional_loading_do_not_affect_dat(self):
        dat_path = os.path.join(_STB_ROOT, "data", "input01.dat")

        self.assertTrue(project_path_for_dat(dat_path).endswith("input01.project.json"))
        self.assertEqual(load_project_for_dat(dat_path), None)

        mdl, txt = run_from_file(dat_path)
        self.assertEqual(len(mdl.nds), 8)
        self.assertTrue("NDSP" in txt)

    def test_load_project_file(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        project_path = os.path.join(out_dir, "sample.project.json")

        f = open(project_path, "w", encoding="utf-8")
        json.dump(_minimal_project(), f)
        f.close()

        project = load_project_file(project_path)

        self.assertEqual(project.source_path, project_path)
        self.assertEqual(project.building.structure, "wood")


if __name__ == "__main__":
    unittest.main()

