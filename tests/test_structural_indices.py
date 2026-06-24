import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file
from stb_practice import build_structural_indices
from stb_practice.structural_indices import (
    StoryIndex,
    _build_shear_panel_stiffness_rows,
    _directional_rigidity_center,
    _story_for_member,
    _story_indices,
)
from stb_project import load_project_for_dat


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class _FakeNode:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class _FakeElem:
    def __init__(self, z0, z1):
        self.n0 = _FakeNode(0.0, 0.0, z0)
        self.n1 = _FakeNode(0.0, 0.0, z1)


class TestStructuralIndices(unittest.TestCase):

    def test_builds_indices_for_uk_diaphragm_sample(self):
        dat_path = _data_path("UK_240416_floors_1to3_diaphragm.dat")
        mdl, _txt = run_from_file(dat_path)
        project = load_project_for_dat(dat_path, required=True)

        result = build_structural_indices(mdl, project)

        self.assertGreaterEqual(len(result.lateral_cases), 1)
        self.assertGreater(len(result.story_drifts), 0)
        self.assertEqual(len(result.eccentricities), len(project.stories))
        self.assertGreater(len(result.rigidity_ratios), 0)
        self.assertTrue("story_drifts" in result.tables)
        self.assertTrue(any(row.is_story_max for row in result.story_drifts))

    def test_rigidity_ratio_rs_is_dimensionless_for_uk_diaphragm_sample(self):
        dat_path = _data_path("UK_240416_floors_1to3_diaphragm.dat")
        mdl, _txt = run_from_file(dat_path)
        project = load_project_for_dat(dat_path, required=True)
        result = build_structural_indices(mdl, project)
        by_key = {}
        for row in result.rigidity_ratios:
            if row.rigidity_ratio is None:
                continue
            key = (row.direction, row.load_case)
            by_key.setdefault(key, []).append(row)
        self.assertGreater(len(by_key), 0)
        for rows in by_key.values():
            mean_inv = rows[0].mean_inverse_ratio
            self.assertIsNotNone(mean_inv)
            for row in rows:
                drift = abs(float(row.drift_m))
                expected_ri = row.height_m / drift
                self.assertAlmostEqual(row.inverse_ratio, expected_ri, places=3)
                self.assertAlmostEqual(
                    row.rigidity_ratio,
                    expected_ri / mean_inv,
                    places=3,
                )
                self.assertGreater(row.rigidity_ratio, 0.1)
                self.assertLess(row.rigidity_ratio, 5.0)
                self.assertGreater(mean_inv, row.rigidity_ratio * 10.0)

    def test_story_for_member_uses_midpoint_at_floor_boundary(self):
        stories = [
            StoryIndex(name="1", elevation=0.0, height=3.035),
            StoryIndex(name="2", elevation=3.035, height=3.01),
        ]
        lower_column = _FakeElem(0.3, 3.035)
        upper_column = _FakeElem(3.035, 6.045)
        self.assertEqual(_story_for_member(lower_column, stories), "1")
        self.assertEqual(_story_for_member(upper_column, stories), "2")

    def test_first_story_center_of_mass_and_rigidity_are_plausible_for_uk_diaphragm_sample(self):
        dat_path = _data_path("UK_240416_floors_1to3_diaphragm.dat")
        mdl, _txt = run_from_file(dat_path)
        project = load_project_for_dat(dat_path, required=True)

        result = build_structural_indices(mdl, project)
        story1 = next(row for row in result.eccentricities if row.story == "1")

        self.assertAlmostEqual(story1.xg, 3.19, places=1)
        self.assertAlmostEqual(story1.yg, 3.84, places=1)
        self.assertIsNotNone(story1.xs)
        self.assertIsNotNone(story1.ys)
        self.assertGreater(story1.ys, -10.0)
        self.assertLess(story1.ys, 10.0)
        self.assertEqual(story1.status, "OK")
        self.assertAlmostEqual(story1.xs, 1.78, places=1)
        self.assertAlmostEqual(story1.ys, 3.78, places=1)
        self.assertIsNotNone(story1.rex_m)
        self.assertIsNotNone(story1.rey_m)
        self.assertLess(story1.rex_m, 10.0)
        self.assertLess(story1.rey_m, 10.0)
        self.assertGreater(story1.rex_m, 0.0)
        self.assertGreater(story1.rey_m, 0.0)
        self.assertIsNotNone(story1.re_x)
        self.assertIsNotNone(story1.re_y)
        self.assertLess(story1.re_x, 0.05)
        self.assertLess(story1.re_y, 0.55)

    def test_shear_panels_included_in_stiffness_rows(self):
        dat_path = _data_path("UK_240416_floors_1to3_diaphragm.dat")
        mdl, _txt = run_from_file(dat_path)
        project = load_project_for_dat(dat_path, required=True)

        result = build_structural_indices(mdl, project)
        panel_rows = [r for r in result.member_stiffnesses if r.status == "shear_panel"]
        self.assertGreater(len(panel_rows), 0)
        self.assertGreater(len(mdl.wshears), 0)
        self.assertEqual(len(panel_rows), len(mdl.wshears))

        stories = _story_indices(project)
        direct = _build_shear_panel_stiffness_rows(mdl, stories)
        self.assertEqual(len(direct), len(mdl.wshears))
        x_panel = next(r for r in direct if r.dxx_kN_m is not None and r.dyy_kN_m is None)
        y_panel = next(r for r in direct if r.dyy_kN_m is not None and r.dxx_kN_m is None)
        self.assertGreater(x_panel.dxx_kN_m, 0.0)
        self.assertGreater(y_panel.dyy_kN_m, 0.0)
        self.assertEqual(x_panel.dxy_kN_m, 0.0)
        self.assertEqual(y_panel.dxy_kN_m, 0.0)

    def test_rigidity_center_uses_directional_stiffness_weights(self):
        from stb_practice.structural_indices import MemberStiffnessRow

        rows = [
            MemberStiffnessRow("1", 1, "", 0.0, 0.0, None, None, None, None, None, None, None, None, 10.0, 0.0, 100.0, "OK"),
            MemberStiffnessRow("1", 2, "", 10.0, 0.0, None, None, None, None, None, None, None, None, 10.0, 0.0, 300.0, "OK"),
        ]
        xs, ys = _directional_rigidity_center(rows)
        self.assertAlmostEqual(xs, 7.5)
        self.assertAlmostEqual(ys, 0.0)

    def test_second_story_center_of_rigidity_is_available_for_uk_diaphragm_sample(self):
        dat_path = _data_path("UK_240416_floors_1to3_diaphragm.dat")
        mdl, _txt = run_from_file(dat_path)
        project = load_project_for_dat(dat_path, required=True)

        result = build_structural_indices(mdl, project)
        story2 = next(row for row in result.eccentricities if row.story == "2")

        self.assertEqual(story2.status, "OK")
        self.assertIsNotNone(story2.xs)
        self.assertIsNotNone(story2.ys)
        self.assertNotAlmostEqual(story2.xs, 0.0)
        self.assertNotAlmostEqual(story2.ys, 0.0)
        self.assertIsNotNone(story2.rex_m)
        self.assertIsNotNone(story2.rey_m)
        self.assertLess(story2.rex_m, 20.0)
        self.assertLess(story2.rey_m, 20.0)


if __name__ == "__main__":
    unittest.main()
