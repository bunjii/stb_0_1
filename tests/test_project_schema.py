import json
import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input, read_input_file, run_from_file
from stb_project import (
    ProjectSchemaError,
    apply_load_combinations_to_model,
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

    def test_seismic_empty_base_mass_policy_uses_default(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {
                "ci": 0.2,
                "base_mass_policy": "",
            }
        }
        project = validate_project_dict(data)
        self.assertEqual(
            project.load_conditions.seismic.base_mass_policy,
            "LUMP_TO_ABOVE_DIAPHRAGM",
        )

    def test_seismic_metadata_without_ci_is_valid(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {
                "base_mass_policy": "IGNORE_AT_BASE",
                "base_level": "1",
            }
        }
        project = validate_project_dict(data)
        self.assertEqual(project.load_conditions.seismic.ci, 0.0)
        self.assertEqual(
            project.load_conditions.seismic.base_mass_policy,
            "IGNORE_AT_BASE",
        )

    def test_seismic_directions_require_positive_ci_or_c0(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {
                "ci": 0.0,
                "directions": [
                    {
                        "name": "X+",
                        "axis": "x",
                        "load_case": 1,
                        "sign": 1,
                    }
                ],
            }
        }
        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(data)

    def test_seismic_masses_base_and_diaphragm_roles(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {"ci": 0.2, "base_level": "1"},
            "seismic_masses": [
                {
                    "name": "1F_floor",
                    "story": "1",
                    "mass_role": "BASE_MASS",
                    "application_level": "base",
                },
                {
                    "name": "2F_floor",
                    "story": "2",
                    "mass_role": "DIAPHRAGM_MASS",
                    "application_diaphragm": 10,
                },
            ],
        }
        project = validate_project_dict(data)
        masses = project.load_conditions.seismic_masses
        self.assertEqual(len(masses), 2)
        self.assertEqual(masses[0].mass_role, "BASE_MASS")
        self.assertFalse(masses[0].generate_diaphragm_load)
        self.assertEqual(masses[1].application_diaphragm, 10)

    def test_seismic_masses_diaphragm_requires_application_diaphragm(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {"ci": 0.2},
            "seismic_masses": [
                {
                    "name": "2F_floor",
                    "story": "2",
                    "mass_role": "DIAPHRAGM_MASS",
                },
            ],
        }
        with self.assertRaises(ProjectSchemaError) as ctx:
            validate_project_dict(data)
        self.assertIn("application_diaphragm", str(ctx.exception))

    def test_seismic_rt_round_trip(self):
        data = _minimal_project()
        data["load_conditions"] = {"seismic": {"ci": 0.2, "rt": 0.85}}
        project = validate_project_dict(data)
        self.assertAlmostEqual(project.load_conditions.seismic.rt, 0.85)
        reparsed = validate_project_dict(project.to_dict())
        self.assertAlmostEqual(reparsed.load_conditions.seismic.rt, 0.85)

    def test_seismic_non_modal_inputs_round_trip(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {
                "ci": 0.2,
                "design_period_s": 0.42,
                "height_m": 8.6,
                "steel_ratio_alpha": 0.25,
                "tc": 0.6,
            }
        }
        project = validate_project_dict(data)
        s = project.load_conditions.seismic
        self.assertAlmostEqual(s.design_period_s, 0.42)
        self.assertAlmostEqual(s.height_m, 8.6)
        self.assertAlmostEqual(s.steel_ratio_alpha, 0.25)
        self.assertAlmostEqual(s.tc, 0.6)

    def test_load_combinations_round_trip(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {"ci": 0.2},
            "load_combinations": [
                {
                    "load_case": 10,
                    "name": "L+S",
                    "duration": "SHORT_TERM",
                    "factors": [1.0, 0.7],
                    "load_cases": [1, 2],
                }
            ],
        }

        project = validate_project_dict(data)
        combo = project.load_conditions.load_combinations[0]
        self.assertEqual(combo.load_case, 10)
        self.assertEqual(combo.duration, "SHORT_TERM")
        self.assertEqual(combo.factors, (1.0, 0.7))
        reparsed = validate_project_dict(project.to_dict())
        self.assertEqual(reparsed.load_conditions.load_combinations[0], combo)

    def test_load_combinations_reject_mismatched_terms(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {"ci": 0.2},
            "load_combinations": [
                {
                    "load_case": 10,
                    "name": "bad",
                    "duration": "LONG_TERM",
                    "factors": [1.0, 0.7],
                    "load_cases": [1],
                }
            ],
        }

        with self.assertRaises(ProjectSchemaError):
            validate_project_dict(data)

    def test_apply_project_load_combinations_to_model(self):
        data = _minimal_project()
        data["load_conditions"] = {
            "seismic": {"ci": 0.2},
            "load_combinations": [
                {
                    "load_case": 10,
                    "name": "PX",
                    "duration": "LONG_TERM",
                    "factors": [2.0],
                    "load_cases": [0],
                }
            ],
        }
        project = validate_project_dict(data)
        mdl = parse_input(read_input_file(os.path.join(_STB_ROOT, "data", "input01.dat")))

        applied = apply_load_combinations_to_model(mdl, project)

        self.assertTrue(applied)
        self.assertEqual(mdl.lcmbs[0].lc, 10)
        self.assertEqual(mdl.lcmbs[0].duration, "LONG_TERM")
        self.assertTrue(any(l.lc == 10 and l.combi for l in mdl.lds))

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

