import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
_CLASSES = os.path.join(_STB_ROOT, "classes")
if _CLASSES not in sys.path:
    sys.path.insert(0, _CLASSES)

from load_case_types import (
    LC_TYPE_DL,
    LC_TYPE_E,
    LC_TYPE_LL_E,
    parse_lnme_fields,
)
from ld import Lcase
from stb_engine import parse_input
from stb_loads.load_cases import resolve_seismic_directions, resolve_seismic_weight_load_cases
from stb_project import load_project_file


def _read_dat(path):
    f = open(path, "r", encoding="utf-8")
    lines = f.read().splitlines()
    f.close()
    return lines


class TestLnmeLoadTypes(unittest.TestCase):

    def test_parse_numeric_type(self):
        load_type, label = parse_lnme_fields("1", "")
        self.assertEqual(load_type, LC_TYPE_DL)
        self.assertEqual(label, "")

    def test_parse_legacy_name(self):
        load_type, label = parse_lnme_fields("DL", "")
        self.assertEqual(load_type, LC_TYPE_DL)

        load_type, label = parse_lnme_fields("EQX", "")
        self.assertEqual(load_type, LC_TYPE_E)
        self.assertEqual(label, "EQX")

    def test_parse_type_with_label(self):
        load_type, label = parse_lnme_fields("6", "EQY")
        self.assertEqual(load_type, LC_TYPE_E)
        self.assertEqual(label, "EQY")

    def test_lcase_round_trip_output(self):
        lc = Lcase(2, LC_TYPE_E, "EQX")
        self.assertEqual(lc.lname, "EQX")
        self.assertIn("2", lc.OutputLnameInfo())
        self.assertIn("6", lc.OutputLnameInfo())
        self.assertIn("EQX", lc.OutputLnameInfo())

    def test_practice_model_resolves_weight_and_direction_lcs(self):
        dat_path = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.dat")
        mdl = parse_input(_read_dat(dat_path))
        weight_lcs, _ = resolve_seismic_weight_load_cases(mdl)
        self.assertEqual(weight_lcs, [1])
        directions, _ = resolve_seismic_directions(mdl)
        self.assertEqual(len(directions), 2)
        self.assertEqual({d.load_case for d in directions}, {2, 3})

    def test_legacy_dat_still_parses(self):
        lines = [
            "NODE, 1, 0, 0, 0",
            "LNME, 1, DL",
            "LNME, 2, EQX",
        ]
        mdl = parse_input(lines)
        self.assertEqual(mdl.lcases[0].load_type, LC_TYPE_DL)
        self.assertEqual(mdl.lcases[1].load_type, LC_TYPE_E)
        self.assertEqual(mdl.lcases[1].label, "EQX")

    def test_wi_uses_type_1_and_3(self):
        lines = [
            "NODE, 1, 0, 0, 3",
            "NODE, 2, 0, 1, 3",
            "MATE, 1, M, 9500, 633, 5, 0, 20",
            "SECT, 1, S, 1, 0, 120, 240",
            "ELEM, 1, 1, 2, 1, 0",
            "LNME, 1, 1",
            "LNME, 2, 3",
            "PLOD, 1, 1, 0, 0, -10, 0, 0, 0",
            "PLOD, 2, 2, 0, 0, -2, 0, 0, 0",
        ]
        mdl = parse_input(lines)
        from stb_loads.weight import aggregate_story_weights
        from stb_project import validate_project_dict

        project = validate_project_dict({
            "schema": 1,
            "model": {"dat": "x.dat"},
            "building": {"name": "t", "location": "", "use": "", "structure": "", "calculation_route": "", "designer": {}},
            "grids": [],
            "stories": [{"name": "1", "elevation": 0.0, "height": 3.0}],
            "member_classes": [],
            "load_conditions": {"seismic": {"ci": 0.3}},
            "report": {"title": "", "mode": "practice", "language": "ja", "format": "markdown"},
        })
        result = aggregate_story_weights(mdl, project)
        self.assertEqual(result.weight_load_cases, (1, 2))
        self.assertAlmostEqual(result.total_weight_kN, 12.0, places=3)

    def test_uk_model_uses_lnme_type_1_for_glc0(self):
        dat_path = os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.dat")
        if not os.path.isfile(dat_path):
            self.skipTest("UK sample missing")
        mdl = parse_input(_read_dat(dat_path))
        weight_lcs, _ = resolve_seismic_weight_load_cases(mdl)
        self.assertIn(0, weight_lcs)
        directions, _ = resolve_seismic_directions(mdl)
        self.assertEqual(len(directions), 1)
        self.assertEqual(directions[0].load_case, 1)


if __name__ == "__main__":
    unittest.main()
