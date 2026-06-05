import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import build_wood_check_summary
from stb_engine import run_from_file
from stb_project import load_project_file, validate_project_dict


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class TestWoodChecks(unittest.TestCase):

    def test_builds_wood_check_summary_for_sample_project(self):
        project = load_project_file(_data_path("practice_wood_single_story.project.json"))
        mdl, _txt = run_from_file(_data_path(project.dat_path))

        summary = build_wood_check_summary(mdl, project)

        self.assertEqual(len(summary.element_checks), 10)
        self.assertEqual(summary.tables.member_classes[0]["name"], "roof_beams")
        self.assertEqual(summary.tables.member_classes[0]["checked_count"], 4)
        self.assertEqual(summary.tables.member_classes[1]["checked_count"], 4)
        self.assertEqual(summary.tables.member_classes[2]["checked_count"], 2)
        self.assertTrue(summary.max_ratio > 0.0)
        self.assertTrue(summary.status in ("OK", "NG"))

        beam = [c for c in summary.element_checks if c.kind == "beam"][0]
        self.assertTrue(beam.bending_ratio >= 0.0)
        self.assertTrue(beam.shear_ratio >= 0.0)
        self.assertTrue(beam.deflection_ratio is not None)
        self.assertEqual(beam.governing_load_case, beam.demand.load_case)

    def test_schema_accepts_wood_check_settings(self):
        project = validate_project_dict({
            "schema": 1,
            "model": {"dat": "model.dat"},
            "building": {
                "name": "Wood check sample",
                "location": "",
                "use": "",
                "structure": "wood",
                "calculation_route": "",
                "designer": {
                    "name": "",
                    "qualification": "",
                    "license_number": "",
                    "contact": "",
                },
            },
            "grids": [
                {"name": "X1", "direction": "x", "coordinate": 0.0},
                {"name": "Y1", "direction": "y", "coordinate": 0.0},
            ],
            "stories": [
                {"name": "1", "elevation": 0.0, "height": 3.0},
            ],
            "member_classes": [
                {
                    "name": "columns",
                    "kind": "column",
                    "element_ids": [1],
                    "story": "1",
                    "use": "wood column",
                    "notes": "",
                },
            ],
            "design_checks": {
                "wood": {
                    "enabled": True,
                    "load_cases": [1, 2],
                    "deflection_limit_ratio": 250.0,
                    "allowable_stresses": {
                        "bending": 8.0,
                        "shear": 0.8,
                        "compression": 6.0,
                        "tension": 4.0,
                    },
                },
            },
            "report": {
                "title": "Wood check report",
                "mode": "practice",
                "language": "ja",
                "format": "markdown",
                "include_manual_items": True,
                "include_warnings": True,
            },
        })

        self.assertTrue(project.design_checks.wood.enabled)
        self.assertEqual(project.design_checks.wood.load_cases, (1, 2))
        self.assertAlmostEqual(project.design_checks.wood.allowable_stresses.bending, 8.0)
        self.assertEqual(validate_project_dict(project.to_dict()).to_dict(), project.to_dict())


if __name__ == "__main__":
    unittest.main()
