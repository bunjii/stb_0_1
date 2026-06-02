import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_viewer.model_json import (
    load_model_dict,
    list_model_files,
    normalize_model_relpath,
    resolve_model_path,
)


class TestViewerModelJson(unittest.TestCase):

    def test_list_models_includes_cantilever(self):
        models = list_model_files()
        self.assertTrue("examples/cantilever.dat" in models)

    def test_load_cantilever_geometry(self):
        data = load_model_dict("examples/cantilever.dat", solve=False)
        self.assertEqual(len(data["nodes"]), 2)
        self.assertEqual(len(data["elements"]), 1)
        self.assertFalse(data["solved"])
        elem = data["elements"][0]
        self.assertTrue("section_id" in elem)
        self.assertTrue("material_name" in elem)
        self.assertTrue("material_id" in elem)
        self.assertEqual(len(data["point_loads"]), 1)
        self.assertAlmostEqual(data["point_loads"][0]["pz"], -5.0, places=3)

    def test_uk_roof_gravity_element_loads(self):
        data = load_model_dict("data/UK_ROOF_240420.dat", solve=False)
        gravity = [ld for ld in data["element_loads"] if ld.get("gravity")]
        self.assertGreater(len(gravity), 50)
        self.assertAlmostEqual(abs(gravity[0]["w"][2]), 0.18, places=1)
        self.assertTrue(str(gravity[0]["display_value"]).endswith("G"))
        self.assertIn("-0.2G", gravity[0]["display_value"])

    def test_building_area_load_element_loads_after_solve(self):
        data = load_model_dict("data/building_4f_x4y2.dat", solve=True)
        self.assertTrue(data["solved"])
        area = [ld for ld in data["element_loads"] if ld.get("area_load")]
        self.assertGreater(len(area), 0)
        by_lc = {}
        for ld in area:
            by_lc.setdefault(ld["lc"], 0)
            by_lc[ld["lc"]] += 1
        self.assertGreater(by_lc.get(0, 0), 0)
        self.assertGreater(by_lc.get(1, 0), 0)
        self.assertFalse(area[0]["global"])
        self.assertEqual(len(area[0]["w"]), 6)
        self.assertTrue(str(area[0]["display_value"]).endswith("A"))

    def test_load_cantilever_solved(self):
        data = load_model_dict("examples/cantilever.dat", solve=True)
        self.assertTrue(data["solved"])
        self.assertEqual(data.get("schema"), 2)
        self.assertTrue("disps" in data["nodes"][1])
        self.assertTrue("0" in data["nodes"][1]["disps"])
        elem = data["elements"][0]
        self.assertTrue("forces" in elem)
        self.assertTrue("0" in elem["forces"])
        self.assertEqual(len(elem["forces"]["0"]), 14)
        self.assertTrue("local_wloads" in elem)
        self.assertTrue("vy" in elem)
        self.assertTrue("vz" in elem)
        sup = data["supports"][0]
        self.assertTrue("reacts" in sup)
        self.assertTrue("0" in sup["reacts"])
        self.assertEqual(len(sup["reacts"]["0"]), 6)
        self.assertAlmostEqual(sup["reacts"]["0"][2], 5.0, places=3)
        self.assertAlmostEqual(sup["reacts"]["0"][4], -10.0, places=3)
        self.assertTrue(len(data.get("reactions", [])) >= 1)
        self.assertAlmostEqual(data["reactions"][0]["rz"], 5.0, places=3)

    def test_reject_path_outside_project(self):
        raised = False
        try:
            resolve_model_path("/etc/passwd")
        except ValueError:
            raised = True
        self.assertTrue(raised)

    def test_normalize_model_relpath_windows_separators(self):
        self.assertEqual(
            normalize_model_relpath(r"data\UK_ROOF_240420.dat"),
            "data/UK_ROOF_240420.dat",
        )
        self.assertEqual(
            normalize_model_relpath("./data/input01.dat"),
            "data/input01.dat",
        )

    def test_resolve_model_path_accepts_backslashes(self):
        full = resolve_model_path(r"data\UK_ROOF_240420.dat")
        self.assertTrue(full.endswith("UK_ROOF_240420.dat"))


class TestViewerApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from stb_viewer.server import create_app
        except ImportError:
            cls.client = None
            return
        except RuntimeError:
            cls.client = None
            return
        cls.client = TestClient(create_app(default_model="examples/cantilever.dat"))

    def test_api_models(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/models")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue("examples/cantilever.dat" in body["models"])

    def test_api_model_geometry(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/model", params={"path": "examples/cantilever.dat", "solve": 0})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(len(body["elements"]), 1)

    def test_api_model_solved_has_results_text(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/model", params={"path": "examples/cantilever.dat", "solve": 1})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["solved"])
        self.assertTrue("NDSP" in body["results_text"])
        elem = body["elements"][0]
        self.assertTrue("forces" in elem)
        self.assertTrue("0" in elem["forces"])
        sup = body["supports"][0]
        self.assertTrue("reacts" in sup)
        self.assertAlmostEqual(sup["reacts"]["0"][2], 5.0, places=3)

    def test_api_results_plain_text(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/results", params={"path": "examples/cantilever.dat"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue("NDSP" in r.text)
        self.assertTrue("EFRC" in r.text)

    def test_api_input_plain_text(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/input", params={"path": "examples/cantilever.dat"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue("MATE" in r.text)

    def test_index_html(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue("STB Viewer" in r.text)

    def test_viewer_open_url_includes_file_query(self):
        from stb_viewer.server import viewer_open_url
        url = viewer_open_url("127.0.0.1", 8765, "data/UK_ROOF_240420.dat")
        self.assertIn("?file=data/UK_ROOF_240420.dat", url)
        plain = viewer_open_url("127.0.0.1", 8765, None)
        self.assertNotIn("?file=", plain)

    def test_viewer_open_url_normalizes_backslashes(self):
        from stb_viewer.server import viewer_open_url
        url = viewer_open_url("127.0.0.1", 8765, r"data\UK_ROOF_240420.dat")
        self.assertIn("?file=data/UK_ROOF_240420.dat", url)

    def test_api_models_default_normalizes_backslashes(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        from fastapi.testclient import TestClient
        from stb_viewer.server import create_app
        client = TestClient(create_app(default_model=r"data\UK_ROOF_240420.dat"))
        r = client.get("/api/models")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["default"], "data/UK_ROOF_240420.dat")


if __name__ == "__main__":
    unittest.main()
