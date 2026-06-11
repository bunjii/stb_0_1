import copy
import json
import os
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input, solve_model
from stb_loads import (
    apply_wind_to_dat,
    compute_er,
    compute_q_N_m2,
    compute_w_N_m2,
    compute_wind_distribution,
    generate_wind_dlod_records,
)
from stb_loads.story import diaphragm_area_m2
from stb_loads.wind import (
    story_force_kN,
    uniform_diaphragm_area_load_kN_m2,
    compute_story_torsion_mz_knm,
    total_dlod_output_kN,
)
from stb_loads.wind_equilibrium import compute_wind_equilibrium
from stb_project import (
    GUST_GF_AT_10M,
    GUST_GF_AT_40M,
    LoadConditionSettings,
    ProjectDefinition,
    Story,
    WindLoadCaseSettings,
    WindLoadSettings,
    WindSurfaceSettings,
    compute_gust_factor_auto,
    roughness_params,
    validate_project_dict,
)


class TestWindCoefficients(unittest.TestCase):

    def test_roughness_table(self):
        rp = roughness_params("III")
        self.assertAlmostEqual(rp.zb, 5.0)
        self.assertAlmostEqual(rp.zg, 450.0)
        self.assertAlmostEqual(rp.alpha, 0.20)

    def test_er_at_or_below_zb(self):
        er = compute_er(4.0, "III")
        expected = 1.7 * (5.0 / 450.0) ** 0.20
        self.assertAlmostEqual(er, expected, places=6)

    def test_er_above_zb(self):
        er = compute_er(20.0, "III")
        expected = 1.7 * (20.0 / 450.0) ** 0.20
        self.assertAlmostEqual(er, expected, places=6)

    def test_gf_direct_input(self):
        case = WindLoadCaseSettings(
            case_id=1, name="WX+", direction="X_PLUS", v0=34.0,
            roughness_category="III", load_case=4, gf=2.5,
        )
        from stb_project import resolve_wind_gf
        gf, auto = resolve_wind_gf(case, 9.0)
        self.assertAlmostEqual(gf, 2.5)
        self.assertFalse(auto)

    def test_gf_auto_at_10m(self):
        self.assertAlmostEqual(compute_gust_factor_auto(8.0, "III"), GUST_GF_AT_10M["III"])

    def test_gf_auto_at_40m(self):
        self.assertAlmostEqual(compute_gust_factor_auto(45.0, "IV"), GUST_GF_AT_40M["IV"])

    def test_gf_auto_interpolation(self):
        g25 = compute_gust_factor_auto(25.0, "III")
        g10 = GUST_GF_AT_10M["III"]
        g40 = GUST_GF_AT_40M["III"]
        expected = g10 + (25.0 - 10.0) / 30.0 * (g40 - g10)
        self.assertAlmostEqual(g25, expected, places=6)

    def test_q_and_w(self):
        er = compute_er(9.045, "III")
        gf = 2.5
        q = compute_q_N_m2(34.0, er, gf)
        self.assertAlmostEqual(q, 0.6 * (er ** 2) * gf * 34.0 ** 2, places=3)
        w = compute_w_N_m2(1.0, q)
        self.assertAlmostEqual(w, q, places=6)

    def test_story_force_from_area(self):
        w = 1000.0
        area = 12.0
        self.assertAlmostEqual(story_force_kN(w, area), 12.0, places=6)


def _minimal_wind_project(diaphragm_input_mode="DIAPHRAGM_UNIFORM"):
    return LoadConditionSettings(
        wind=WindLoadSettings(
            cases=(
                WindLoadCaseSettings(
                    case_id=1,
                    name="WX+",
                    direction="X_PLUS",
                    v0=34.0,
                    roughness_category="III",
                    load_case=4,
                    gf=2.5,
                    cf_default=1.0,
                    building_height_H=9.045,
                    diaphragm_input_mode=diaphragm_input_mode,
                ),
            ),
            surfaces=(
                WindSurfaceSettings(
                    surface_id=1,
                    name="west_wall",
                    wind_case_id=1,
                    face_direction="X_PLUS",
                    z_bottom=0.0,
                    z_top=9.045,
                    width=5.46,
                    cf=1.0,
                    surface_role="WINDWARD",
                ),
            ),
        ),
        diaphragms=(
            __import__("stb_project").DiaphragmAssignment(10, "2"),
            __import__("stb_project").DiaphragmAssignment(20, "3"),
        ),
    )


class TestWindDistribution(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dat_path = os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.dat")
        with open(cls.dat_path, encoding="utf-8") as fh:
            cls.mdl = parse_input(fh.read().splitlines())
        from stb_project import load_project_file
        cls.base_project = load_project_file(
            os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.project.json")
        )

    def _project_with_wind(self, **kwargs):
        lc = _minimal_wind_project(**kwargs)
        return ProjectDefinition(
            schema=self.base_project.schema,
            dat_path=self.base_project.dat_path,
            building=self.base_project.building,
            grids=self.base_project.grids,
            stories=self.base_project.stories,
            member_classes=self.base_project.member_classes,
            design_checks=self.base_project.design_checks,
            load_conditions=LoadConditionSettings(
                seismic=self.base_project.load_conditions.seismic,
                diaphragms=lc.diaphragms,
                seismic_masses=self.base_project.load_conditions.seismic_masses,
                wind=lc.wind,
            ),
            report=self.base_project.report,
        )

    def test_uniform_dlod_equals_f_story_over_area(self):
        project = self._project_with_wind()
        result = compute_wind_distribution(self.mdl, project)
        diap10 = next(d for d in result.diaphragm_loads if d.diaphragm_id == 10)
        area10 = diaphragm_area_m2(self.mdl, 10)
        self.assertAlmostEqual(
            diap10.area_load_kN_m2,
            uniform_diaphragm_area_load_kN_m2(diap10.f_story_kN, area10),
            places=6,
        )
        self.assertEqual(diap10.input_mode, "DIAPHRAGM_UNIFORM")

    def test_windward_and_leeward_aggregate_to_f_story(self):
        wind = WindLoadSettings(
            cases=(
                WindLoadCaseSettings(
                    case_id=1, name="WX+", direction="X_PLUS", v0=34.0,
                    roughness_category="III", load_case=4, gf=2.5,
                    building_height_H=9.045,
                ),
            ),
            surfaces=(
                WindSurfaceSettings(
                    surface_id=1, name="windward", wind_case_id=1,
                    face_direction="X_PLUS", z_bottom=3.035, z_top=6.045,
                    width=5.0, cf=1.0, surface_role="WINDWARD",
                ),
                WindSurfaceSettings(
                    surface_id=2, name="leeward", wind_case_id=1,
                    face_direction="X_MINUS", z_bottom=3.035, z_top=6.045,
                    width=5.0, cf=-0.5, surface_role="LEEWARD",
                ),
            ),
        )
        lc = _minimal_wind_project()
        lc = LoadConditionSettings(
            wind=wind,
            diaphragms=lc.diaphragms,
        )
        project = self._project_with_wind()
        project = ProjectDefinition(
            schema=project.schema,
            dat_path=project.dat_path,
            building=project.building,
            grids=project.grids,
            stories=project.stories,
            member_classes=project.member_classes,
            design_checks=project.design_checks,
            load_conditions=LoadConditionSettings(
                seismic=project.load_conditions.seismic,
                diaphragms=lc.diaphragms,
                seismic_masses=project.load_conditions.seismic_masses,
                wind=wind,
            ),
            report=project.report,
        )
        result = compute_wind_distribution(self.mdl, project)
        story2 = next(sf for sf in result.story_forces if sf.story == "2")
        comp_sum = sum(
            c.force_kN for c in result.surface_contributions if c.story == "2"
        )
        self.assertAlmostEqual(story2.f_story_kN, comp_sum, places=3)

    def test_no_dlod_for_edge_or_member_load_mode(self):
        wind = WindLoadSettings(
            cases=(
                WindLoadCaseSettings(
                    case_id=1, name="WX+", direction="X_PLUS", v0=34.0,
                    roughness_category="III", load_case=4, gf=2.5,
                    diaphragm_input_mode="EDGE_OR_MEMBER_LOAD",
                ),
            ),
            surfaces=(
                WindSurfaceSettings(
                    surface_id=1, name="wall", wind_case_id=1,
                    face_direction="X_PLUS", z_bottom=0.0, z_top=9.045, width=5.0,
                ),
            ),
        )
        project = self._project_with_wind()
        project = ProjectDefinition(
            schema=project.schema,
            dat_path=project.dat_path,
            building=project.building,
            grids=project.grids,
            stories=project.stories,
            member_classes=project.member_classes,
            design_checks=project.design_checks,
            load_conditions=LoadConditionSettings(
                seismic=project.load_conditions.seismic,
                diaphragms=project.load_conditions.diaphragms,
                seismic_masses=project.load_conditions.seismic_masses,
                wind=wind,
            ),
            report=project.report,
        )
        result = compute_wind_distribution(self.mdl, project)
        self.assertGreater(len(result.story_forces), 0)
        self.assertEqual(len(result.diaphragm_loads), 0)
        self.assertEqual(len(generate_wind_dlod_records(result)), 0)

    def test_equilibrium_with_temporary_dat(self):
        project = self._project_with_wind()
        result = compute_wind_distribution(self.mdl, project)
        dloads = generate_wind_dlod_records(result)

        with tempfile.TemporaryDirectory() as tmp:
            dat_copy = os.path.join(tmp, "wind_test.dat")
            with open(self.dat_path, encoding="utf-8") as src:
                lines = src.read().splitlines()
            extra = [
                "LNME,      4,    5,      WX+",
            ]
            lines.extend(extra)
            with open(dat_copy, "w", encoding="utf-8") as dst:
                dst.write("\n".join(lines) + "\n")

            apply_wind_to_dat(dat_copy, dloads)
            with open(dat_copy, encoding="utf-8") as fh:
                mdl = parse_input(fh.read().splitlines())
            if 4 not in mdl.lcs:
                mdl.lcs.append(4)

            eq = compute_wind_equilibrium(mdl, result)
            self.assertEqual(len(eq), 1)
            row = eq[0]
            self.assertAlmostEqual(
                row["sum_f_dlod_output_kN"],
                total_dlod_output_kN(result),
                places=2,
            )
            self.assertAlmostEqual(row["fx_applied_kN"], row["sum_f_dlod_output_kN"], places=1)
            self.assertLess(row["equilibrium_residual_kN"], 0.05)

    def test_torsion_mz_formula_placeholder(self):
        self.assertAlmostEqual(compute_story_torsion_mz_knm(10.0, 2.0), 20.0)

    def test_no_double_counting_uniform_vs_edge(self):
        wind = WindLoadSettings(
            cases=(
                WindLoadCaseSettings(
                    case_id=1, name="WX+ uniform", direction="X_PLUS", v0=34.0,
                    roughness_category="III", load_case=4, gf=2.5,
                    diaphragm_input_mode="DIAPHRAGM_UNIFORM",
                ),
                WindLoadCaseSettings(
                    case_id=2, name="WX+ edge", direction="X_PLUS", v0=34.0,
                    roughness_category="III", load_case=5, gf=2.5,
                    diaphragm_input_mode="EDGE_OR_MEMBER_LOAD",
                ),
            ),
            surfaces=(
                WindSurfaceSettings(
                    surface_id=1, name="shared_wall", wind_case_id=1,
                    face_direction="X_PLUS", z_bottom=0.0, z_top=9.045, width=5.0,
                ),
                WindSurfaceSettings(
                    surface_id=1, name="shared_wall", wind_case_id=2,
                    face_direction="X_PLUS", z_bottom=0.0, z_top=9.045, width=5.0,
                ),
            ),
        )
        project = self._project_with_wind()
        project = ProjectDefinition(
            schema=project.schema,
            dat_path=project.dat_path,
            building=project.building,
            grids=project.grids,
            stories=project.stories,
            member_classes=project.member_classes,
            design_checks=project.design_checks,
            load_conditions=LoadConditionSettings(
                seismic=project.load_conditions.seismic,
                diaphragms=project.load_conditions.diaphragms,
                seismic_masses=project.load_conditions.seismic_masses,
                wind=wind,
            ),
            report=project.report,
        )
        result = compute_wind_distribution(self.mdl, project)
        self.assertTrue(any("double counting" in w for w in result.warnings))
        self.assertEqual(len(result.diaphragm_loads), 0)


class TestWindSchema(unittest.TestCase):

    def test_wind_json_round_trip(self):
        raw = {
            "schema": 1,
            "model": {"dat": "sample.dat"},
            "building": {},
            "grids": [],
            "stories": [{"name": "1", "elevation": 0.0, "height": 3.0}],
            "member_classes": [],
            "design_checks": {"wood": {"enabled": False, "load_cases": []}},
            "load_conditions": {
                "seismic": {"ci": 0.2},
                "wind": {
                    "cases": [{
                        "id": 1,
                        "name": "WX+",
                        "direction": "X_PLUS",
                        "V0": 34.0,
                        "roughness_category": "III",
                        "building_height_H": 6.045,
                        "Gf": 2.5,
                        "Cf_default": 1.0,
                        "pressure_mode": "BUILDING_HEIGHT_UNIFORM",
                        "diaphragm_input_mode": "DIAPHRAGM_UNIFORM",
                        "load_case": 4,
                    }],
                    "surfaces": [{
                        "id": 1,
                        "name": "wall",
                        "wind_case_id": 1,
                        "face_direction": "X_PLUS",
                        "z_bottom": 0.0,
                        "z_top": 6.045,
                        "width": 8.0,
                        "Cf": 1.0,
                        "surface_role": "WINDWARD",
                    }],
                    "member_loads": [],
                },
            },
            "report": {"mode": "practice", "format": "markdown"},
        }
        project = validate_project_dict(raw)
        self.assertEqual(len(project.load_conditions.wind.cases), 1)
        self.assertEqual(project.load_conditions.wind.cases[0].diaphragm_input_mode, "DIAPHRAGM_UNIFORM")


if __name__ == "__main__":
    unittest.main()
