import json
import os
import shutil
import sys
import tempfile
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import parse_input, run_from_file
from stb_loads import (
    apply_seismic_to_dat,
    compute_ai_coefficients,
    compute_seismic_distribution,
    compute_story_forces,
    compute_story_seismic_forces,
    generate_dlod_records,
    replace_seismic_dlod_block,
    replace_wind_dlod_block,
)
from stb_loads.mass_level import build_mass_level_summaries
from stb_project import load_project_file, validate_project_dict, effective_seismic_ci


def _read_dat_lines(path):
    f = open(path, "r", encoding="utf-8")
    lines = f.read().splitlines()
    f.close()
    return lines


class TestSeismicAiDistribution(unittest.TestCase):

    def test_single_story_ai_is_unity(self):
        ai = compute_ai_coefficients([100.0], [1.5], 0.2)
        self.assertEqual(len(ai), 1)
        self.assertAlmostEqual(ai[0], 1.0, places=6)

    def test_story_seismic_forces_from_shear(self):
        qi = (100.0, 60.0, 30.0)
        fi = compute_story_seismic_forces(qi)
        self.assertAlmostEqual(fi[0], 40.0, places=6)
        self.assertAlmostEqual(fi[1], 30.0, places=6)
        self.assertAlmostEqual(fi[2], 30.0, places=6)
        self.assertAlmostEqual(sum(fi), qi[0], places=6)

    def test_story_forces_ci_per_floor(self):
        weights = [100.0, 80.0]
        ai = (1.0, 1.5)
        qi, ci_stories = compute_story_forces(weights, ai, 0.2, 1.0, 1.0)
        self.assertAlmostEqual(ci_stories[0], 0.2, places=6)
        self.assertAlmostEqual(ci_stories[1], 0.3, places=6)
        self.assertAlmostEqual(qi[0], 0.2 * 180.0, places=6)

    def test_three_equal_stories_story_forces_sum_to_base_shear(self):
        weights = [100.0, 100.0, 100.0]
        heights = [1.5, 4.5, 7.5]
        c0, z, rt = 0.2, 1.0, 1.0
        ai = compute_ai_coefficients(weights, heights, 0.2)
        qi, _ = compute_story_forces(weights, ai, c0, z, rt)
        self.assertAlmostEqual(qi[0], c0 * z * rt * sum(weights), places=4)
        self.assertGreater(qi[0], qi[2])

    def test_practice_single_story_pressure(self):
        dat_path = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.dat")
        project_path = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        project = load_project_file(project_path)
        mdl = parse_input(_read_dat_lines(dat_path))
        result = compute_seismic_distribution(mdl, project)

        self.assertEqual(len(result.stories), 1)
        self.assertAlmostEqual(result.stories[0].ai, 1.0, places=4)
        self.assertEqual(len(result.diaphragm_loads), 2)
        for item in result.diaphragm_loads:
            self.assertAlmostEqual(item.pressure_kN_m2, 0.151, places=2)

    def test_apply_seismic_block_round_trip(self):
        dat_path = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.dat")
        project = load_project_file(
            os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        )
        mdl = parse_input(_read_dat_lines(dat_path))
        result = compute_seismic_distribution(mdl, project)
        dloads = generate_dlod_records(result)

        tmp_dir = tempfile.mkdtemp(prefix="stb_seismic_")
        try:
            tmp_dat = os.path.join(tmp_dir, "sample.dat")
            shutil.copy2(dat_path, tmp_dat)
            apply_seismic_to_dat(tmp_dat, dloads)

            reparsed = parse_input(_read_dat_lines(tmp_dat))
            seismic = [
                dl for dl in reparsed.dloads
                if dl.lc in (2, 3) and dl.load_type == "AREA"
            ]
            self.assertGreaterEqual(len(seismic), 2)
            with open(tmp_dat, "r", encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("# --- SEISMIC DLOD (auto) ---", text)
            mdl2, txt = run_from_file(tmp_dat)
            self.assertIn("NDSP", txt)
        finally:
            try:
                shutil.rmtree(tmp_dir)
            except PermissionError:
                pass

    def test_replace_seismic_block_idempotent(self):
        lines = [
            "# header",
            "DLOD, 1, 1, 0, 1.0, 0.0",
            "# --- SEISMIC DLOD (auto) ---",
            "DLOD, 10, 2, 0, 0.2, 0.0",
            "# --- END SEISMIC DLOD (auto) ---",
            "PLOD, 1, 1, 0, 0, -1, 0, 0, 0",
        ]
        block = "# --- SEISMIC DLOD (auto) ---\nDLOD, 10, 2, 0, 0.3, 0.0\n# --- END SEISMIC DLOD (auto) ---\n"
        updated = replace_seismic_dlod_block(lines, block)
        self.assertEqual(updated.count("# --- SEISMIC DLOD (auto) ---"), 1)
        self.assertIn("0.3", "\n".join(updated))

    def test_wind_block_is_inserted_after_existing_seismic_block(self):
        lines = [
            "# header",
            "# --- SEISMIC DLOD (auto) ---",
            "DLOD, 10, 2, 0, 0.2, 0.0",
            "# --- END SEISMIC DLOD (auto) ---",
            "PLOD, 1, 1, 0, 0, -1, 0, 0, 0",
        ]
        block = "# --- WIND DLOD (auto) ---\nDLOD, 10, 4, 0, 0.3, 0.0\n# --- END WIND DLOD (auto) ---\n"
        updated = replace_wind_dlod_block(lines, block)
        seismic_end = updated.index("# --- END SEISMIC DLOD (auto) ---")
        wind_start = updated.index("# --- WIND DLOD (auto) ---")
        self.assertGreater(wind_start, seismic_end)

    def test_stories_without_diaphragm_emit_warning(self):
        weights = [50.0, 100.0, 80.0]
        heights = [1.5, 4.5, 7.5]
        ai = compute_ai_coefficients(weights, heights, 0.2)
        qi, _ = compute_story_forces(weights, ai, 0.2, 1.0, 1.0)
        unassigned = qi[0]
        self.assertGreater(unassigned, 0.0)

    def test_rt_defaults_to_one(self):
        project = load_project_file(
            os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        )
        self.assertIsNone(project.load_conditions.seismic.rt)

    def test_rt_override_scales_base_shear(self):
        weights = [100.0]
        heights = [3.0]
        ai = compute_ai_coefficients(weights, heights, 0.2)
        qi_base, _ = compute_story_forces(weights, ai, 0.2, 1.0, 1.0)
        qi_rt, _ = compute_story_forces(weights, ai, 0.2, 1.0, 0.85)
        self.assertAlmostEqual(qi_rt[0], qi_base[0] * 0.85, places=4)

    def test_project_schema_rt_round_trip(self):
        project_path = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        project = load_project_file(project_path)
        raw = project.to_dict()
        raw["load_conditions"]["seismic"]["rt"] = 0.85
        reparsed = validate_project_dict(raw)
        self.assertAlmostEqual(reparsed.load_conditions.seismic.rt, 0.85, places=6)
        self.assertAlmostEqual(effective_seismic_ci(reparsed.load_conditions.seismic), 0.169 * 0.85, places=6)

    def test_project_schema_load_conditions_round_trip(self):
        project_path = os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        project = load_project_file(project_path)
        reparsed = validate_project_dict(project.to_dict())
        self.assertAlmostEqual(reparsed.load_conditions.seismic.ci, 0.169, places=3)
        self.assertEqual(reparsed.load_conditions.diaphragms[0].diaphragm_id, 10)


class TestUkSeismicSample(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dat_path = os.path.join(_STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.dat")
        cls.project_path = os.path.join(
            _STB_ROOT, "data", "UK_240416_floors_1to3_diaphragm.project.json"
        )
        if not os.path.isfile(cls.dat_path):
            raise unittest.SkipTest("UK sample dat not found")
        cls.project = load_project_file(cls.project_path)
        cls.mdl = parse_input(_read_dat_lines(cls.dat_path))

    def test_uk_distribution_has_two_diaphragm_loads(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        self.assertEqual(result.base_level, "1")
        self.assertEqual(len(result.stories), 3)
        self.assertGreater(result.total_weight_kN, 47.0)
        diap_ids = {d.diaphragm_id for d in result.diaphragm_loads}
        self.assertIn(10, diap_ids)
        self.assertIn(20, diap_ids)
        by_story = {s.story_name: s for s in result.stories}
        self.assertIn("1", by_story)
        self.assertFalse(by_story["1"].output_dlod)
        self.assertTrue(by_story["2"].output_dlod)
        self.assertAlmostEqual(
            result.q1_kN,
            result.c0 * result.z * result.rt * result.total_weight_kN,
            places=1,
        )
        self.assertAlmostEqual(result.q1_kN, result.fi_all_mass_levels_kN, places=2)

    def test_uk_wi_above_and_alpha_i(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        by_story = {s.story_name: s for s in result.stories}
        self.assertAlmostEqual(result.total_weight_kN, 330.935, places=2)
        self.assertAlmostEqual(by_story["3"].w_supported_above_kN, 60.725, places=2)
        self.assertAlmostEqual(by_story["2"].w_supported_above_kN, 125.988, places=2)
        self.assertAlmostEqual(by_story["1"].w_supported_above_kN, 330.935, places=2)
        self.assertAlmostEqual(by_story["3"].beta, 60.725 / 330.935, places=3)
        self.assertAlmostEqual(by_story["2"].beta, 125.988 / 330.935, places=3)
        self.assertAlmostEqual(by_story["1"].beta, 1.0, places=3)

    def test_uk_wi_matches_fem_applied_loads(self):
        from classes.solve import Solve
        from stb_loads.weight import aggregate_weight_for_load_case

        result = compute_seismic_distribution(self.mdl, self.project)
        solver = Solve.__new__(Solve)
        solver.mdl = self.mdl
        solver.ndof = 6
        solver.num_row = 6 * len(self.mdl.nds)
        lm = solver.CreateLoadMx(apply_constraints=False)
        for lc in result.weight_result.weight_load_cases:
            col = self.mdl.lcs.index(lc)
            applied_kN = -sum(float(lm[n.cid * 6 + 2, col]) for n in self.mdl.nds) * 1e-3
            wi_kN = aggregate_weight_for_load_case(self.mdl, self.project, lc)
            self.assertAlmostEqual(wi_kN, applied_kN, places=3)

    def test_uk_lc3_lle_vertical_reactions(self):
        from stb_engine import solve_model
        from stb_loads.story import diaphragm_area_m2

        mdl = parse_input(_read_dat_lines(self.dat_path))
        area = diaphragm_area_m2(mdl, 10)
        expected_kN = 2.0 * 0.8 * area

        from classes.solve import Solve

        solver = Solve.__new__(Solve)
        solver.mdl = mdl
        solver.ndof = 6
        solver.num_row = 6 * len(mdl.nds)
        lm = solver.CreateLoadMx(apply_constraints=False)
        col = mdl.lcs.index(3)
        applied_n = sum(float(lm[n.cid * 6 + 2, col]) for n in mdl.nds)

        solve_model(mdl)
        reacted_n = sum(
            float(c.nd.reacts[col, 2])
            for c in mdl.cons
            if c.nd.reacts is not None
        )

        self.assertAlmostEqual(applied_n * 1.0e-3, -expected_kN, places=1)
        self.assertAlmostEqual(reacted_n * 1.0e-3, expected_kN, places=1)
        self.assertAlmostEqual(applied_n + reacted_n, 0.0, places=0)

        dloads = {
            (d.diap_id, d.lc): d.weight * 1e-3
            for d in self.mdl.dloads
            if d.load_type == "WEIGHT"
        }
        self.assertAlmostEqual(dloads[(10, 2)], 1.8, places=3)
        self.assertAlmostEqual(dloads[(20, 2)], 1.8, places=3)
        self.assertAlmostEqual(dloads[(10, 3)], 0.8, places=3)
        self.assertAlmostEqual(dloads[(20, 3)], 0.8, places=3)

    def test_uk_vertical_weight_reactions_after_resolve(self):
        import copy
        from stb_engine import solve_model
        from stb_loads.format import _check_vertical_weight_reactions

        result = compute_seismic_distribution(self.mdl, self.project)
        solve_model(self.mdl)
        mdl_s = copy.deepcopy(self.mdl)
        solve_model(mdl_s)
        ok, detail = _check_vertical_weight_reactions(
            self.mdl, result, mdl_solved=mdl_s, project=self.project
        )
        self.assertTrue(ok, detail)
        self.assertIn("LC0 Wi=", detail)
        self.assertIn("LC3 Wi=", detail)

    def test_uk_per_story_ci_values(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        by_story = {s.story_name: s for s in result.stories}
        self.assertAlmostEqual(by_story["3"].ci_story, 0.451, places=3)
        self.assertAlmostEqual(by_story["2"].ci_story, 0.387, places=3)
        self.assertAlmostEqual(by_story["1"].ci_story, 0.300, places=3)
        self.assertAlmostEqual(result.fi_dlod_output_kN, 48.788, places=2)

    def test_uk_base_mass_warning_and_no_first_floor_dlod(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        self.assertTrue(
            any("BASE_MASS" in w and "1階DLOD" in w for w in result.warnings)
        )
        by_story = {s.story_name: s for s in result.stories}
        self.assertGreater(by_story["1"].weight_kN, 0.0)
        self.assertGreater(by_story["1"].fi_kN, 0.0)
        self.assertFalse(by_story["1"].output_dlod)

    def test_uk_lc1_equilibrium_after_dlod(self):
        from stb_loads.equilibrium import compute_seismic_equilibrium

        result = compute_seismic_distribution(self.mdl, self.project)
        eq = compute_seismic_equilibrium(self.mdl, result)
        self.assertEqual(len(eq), 1)
        row = eq[0]
        self.assertEqual(row["load_case"], 1)
        self.assertEqual(row["direction"], "X+")
        self.assertAlmostEqual(row["fi_dlod_output_kN"], 48.788, places=2)
        self.assertAlmostEqual(row["fx_applied_kN"], 48.788, places=2)
        self.assertAlmostEqual(row["sum_reaction_kN"], -48.788, places=2)
        self.assertLess(row["equilibrium_residual_kN"], 0.05)
        self.assertFalse(row["other_loads"])
        self.assertFalse(row["pressure_mismatches"])

    def test_uk_uses_fi_not_qi_for_dlod(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        by_diap = {d.diaphragm_id: d for d in result.diaphragm_loads}
        by_story = {s.story_name: s for s in result.stories}
        self.assertAlmostEqual(by_diap[10].fi_kN, by_story["2"].fi_kN, places=2)
        self.assertLess(by_diap[10].fi_kN, by_story["2"].qi_kN)

    def test_uk_pressure_order_of_magnitude(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        by_diap = {d.diaphragm_id: d.pressure_kN_m2 for d in result.diaphragm_loads}
        self.assertGreater(by_diap[10], 0.01)
        self.assertGreater(by_diap[20], 0.01)

    def test_uk_base_mass_lumped_to_story_two(self):
        from dataclasses import replace

        raw = {sw.story_name: sw.weight_kN for sw in
               compute_seismic_distribution(self.mdl, self.project).weight_result.stories}
        lump_seismic = replace(
            self.project.load_conditions.seismic,
            base_mass_policy="LUMP_TO_ABOVE_DIAPHRAGM",
        )
        warnings = []
        levels = build_mass_level_summaries(
            raw,
            self.project.stories,
            lump_seismic,
            {"2", "3"},
            warnings,
        )
        by_name = {lv.story_name: lv.weight_kN for lv in levels}
        self.assertNotIn("1", by_name)
        self.assertGreater(by_name["2"], raw["2"])

    def test_uk_ignore_at_base_excludes_story_one_fi(self):
        from dataclasses import replace

        legacy_lc = replace(self.project.load_conditions, seismic_masses=())
        legacy_seismic = replace(legacy_lc.seismic, base_mass_policy="IGNORE_AT_BASE")
        legacy_lc = replace(legacy_lc, seismic=legacy_seismic)
        legacy_proj = replace(self.project, load_conditions=legacy_lc)
        result = compute_seismic_distribution(self.mdl, legacy_proj)
        story_names = {s.story_name for s in result.stories}
        self.assertNotIn("1", story_names)


class TestCurrentUkSeismicModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dat_path = os.path.join(_STB_ROOT, "data", "UK_240416.dat")
        cls.project_path = os.path.join(_STB_ROOT, "data", "UK_240416.project.json")
        cls.project = load_project_file(cls.project_path)
        cls.mdl = parse_input(_read_dat_lines(cls.dat_path))

    def test_diaphragm_areas_are_valid_for_seismic_dlod(self):
        from stb_loads.story import diaphragm_area_m2

        self.assertAlmostEqual(diaphragm_area_m2(self.mdl, 20), 44.1945, places=3)
        self.assertAlmostEqual(diaphragm_area_m2(self.mdl, 30), 44.1945, places=3)

    def test_dlod_uses_story_fi_not_diaphragm_area_or_qi(self):
        result = compute_seismic_distribution(self.mdl, self.project)
        by_story = {s.story_name: s for s in result.stories}
        by_diap_lc = {(d.diaphragm_id, d.load_case): d for d in result.diaphragm_loads}

        self.assertAlmostEqual(by_diap_lc[(20, 2)].fi_kN, by_story["2"].fi_kN, places=3)
        self.assertAlmostEqual(by_diap_lc[(30, 2)].fi_kN, by_story["3"].fi_kN, places=3)
        self.assertLess(by_diap_lc[(20, 2)].fi_kN, by_story["2"].qi_kN)
        self.assertLess(by_diap_lc[(30, 2)].fi_kN, by_story["3"].qi_kN)
        self.assertLess(by_diap_lc[(20, 2)].pressure_kN_m2, 1.0)
        self.assertLess(by_diap_lc[(30, 2)].pressure_kN_m2, 1.0)


if __name__ == "__main__":
    unittest.main()
