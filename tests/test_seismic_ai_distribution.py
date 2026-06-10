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
        ai = compute_ai_coefficients([100.0], [1.5])
        self.assertEqual(len(ai), 1)
        self.assertAlmostEqual(ai[0], 1.0, places=6)

    def test_story_seismic_forces_from_shear(self):
        qi = (100.0, 60.0, 30.0)
        fi = compute_story_seismic_forces(qi)
        self.assertAlmostEqual(fi[0], 40.0, places=6)
        self.assertAlmostEqual(fi[1], 30.0, places=6)
        self.assertAlmostEqual(fi[2], 30.0, places=6)
        self.assertAlmostEqual(sum(fi), qi[0], places=6)

    def test_three_equal_stories_story_forces_sum_to_base_shear(self):
        weights = [100.0, 100.0, 100.0]
        heights = [1.5, 4.5, 7.5]
        ci = 0.2
        ai = compute_ai_coefficients(weights, heights)
        qi = compute_story_forces(weights, ai, ci)
        self.assertAlmostEqual(sum(qi), ci * sum(weights), places=4)
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

    def test_stories_without_diaphragm_emit_warning(self):
        weights = [50.0, 100.0, 80.0]
        heights = [1.5, 4.5, 7.5]
        ai = compute_ai_coefficients(weights, heights)
        qi = compute_story_forces(weights, ai, 0.2)
        unassigned = qi[0]
        self.assertGreater(unassigned, 0.0)

    def test_rt_defaults_to_one(self):
        project = load_project_file(
            os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        )
        self.assertAlmostEqual(project.load_conditions.seismic.rt, 1.0, places=6)

    def test_rt_override_scales_base_shear(self):
        weights = [100.0]
        heights = [3.0]
        ai = compute_ai_coefficients(weights, heights)
        qi_base = compute_story_forces(weights, ai, 0.2)
        qi_rt = compute_story_forces(weights, ai, 0.2 * 0.85)
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
        self.assertEqual(result.base_mass_policy, "IGNORE_AT_BASE")
        self.assertEqual(len(result.stories), 2)
        self.assertGreater(result.total_weight_kN, 0.0)
        diap_ids = {d.diaphragm_id for d in result.diaphragm_loads}
        self.assertIn(10, diap_ids)
        self.assertIn(20, diap_ids)
        self.assertAlmostEqual(sum(s.qi_kN for s in result.stories), result.base_shear_kN, places=2)
        self.assertAlmostEqual(sum(s.fi_kN for s in result.stories), result.stories[0].qi_kN, places=2)
        by_story = {s.story_name: s for s in result.stories}
        self.assertNotIn("1", by_story)

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
        result = compute_seismic_distribution(self.mdl, self.project)
        story_names = {s.story_name for s in result.stories}
        self.assertNotIn("1", story_names)
        by_story = {s.story_name: s for s in result.stories}
        self.assertAlmostEqual(by_story["2"].fi_kN, by_story["2"].qi_kN - by_story["3"].qi_kN, places=2)


if __name__ == "__main__":
    unittest.main()
