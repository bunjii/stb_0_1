import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file
from stb_practice import build_practice_summary
from stb_project import validate_project_dict


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


def _project():
    return validate_project_dict({
        "schema": 1,
        "model": {"dat": "input01.dat"},
        "building": {
            "name": "Practice sample",
            "location": "",
            "use": "",
            "structure": "steel",
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
            {"name": "X2", "direction": "x", "coordinate": 4.0},
            {"name": "Y1", "direction": "y", "coordinate": 0.0},
            {"name": "Y2", "direction": "y", "coordinate": 4.0},
        ],
        "stories": [
            {"name": "1", "elevation": 0.0, "height": 4.0},
        ],
        "member_classes": [
            {
                "name": "columns",
                "kind": "column",
                "element_ids": [4, 5, 6, 7],
                "story": "1",
                "use": "lateral frame",
                "notes": "",
            },
            {
                "name": "roof beams",
                "kind": "beam",
                "element_ids": [0, 1, 2, 3],
                "story": "1",
                "use": "roof beam",
                "notes": "",
            },
        ],
        "report": {
            "title": "Practice report",
            "mode": "practice",
            "language": "ja",
            "format": "markdown",
            "include_manual_items": True,
            "include_warnings": True,
        },
    })


class TestPracticeSummary(unittest.TestCase):

    def test_builds_practice_layer_from_solved_model(self):
        mdl, _txt = run_from_file(_data_path("input01.dat"))

        summary = build_practice_summary(mdl, _project())

        self.assertEqual(len(summary.grids), 4)
        self.assertEqual(summary.stories[0].element_ids, tuple(range(8)))
        self.assertEqual(summary.member_classes[0].name, "columns")
        self.assertEqual(summary.member_classes[0].count, 4)
        self.assertAlmostEqual(summary.member_classes[0].total_length, 16.0)
        self.assertTrue(summary.center_of_mass is not None)
        self.assertAlmostEqual(summary.center_of_mass.x, 2.0)
        self.assertAlmostEqual(summary.center_of_mass.y, 2.0)
        self.assertTrue(summary.center_of_rigidity_x.x is not None)
        self.assertTrue(summary.center_of_rigidity_y.y is not None)
        self.assertAlmostEqual(summary.eccentricity_x.eccentricity, 0.0)
        self.assertAlmostEqual(summary.eccentricity_y.eccentricity, 0.0)
        self.assertEqual(len(summary.tables.member_classes), 2)
        self.assertEqual(summary.tables.eccentricities[0]["direction"], "x")

    def test_reports_missing_member_class_elements(self):
        raw = _project().to_dict()
        raw["member_classes"][0]["element_ids"].append(999)
        project = validate_project_dict(raw)
        mdl, _txt = run_from_file(_data_path("input01.dat"))

        summary = build_practice_summary(mdl, project)

        self.assertEqual(summary.member_classes[0].missing_element_ids, (999,))
        self.assertTrue(any("missing elements" in w for w in summary.warnings))


if __name__ == "__main__":
    unittest.main()
