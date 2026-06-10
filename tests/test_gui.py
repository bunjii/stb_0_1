import copy
import os
import sys
import unittest
import unittest.mock

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui.model_json import (
    load_model_dict,
    list_model_files,
    mdl_to_dict,
    normalize_model_relpath,
    resolve_model_path,
)
from stb_engine import parse_input, solve_model


class TestGuiModelJson(unittest.TestCase):

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
        self.assertIn("materials", data)
        self.assertIn("sections", data)
        self.assertIn("element_joints", data)
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

    def test_wood_rated_walls_in_model_json(self):
        lines = [
            "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
            "SECT, 1, C120, 1, 0, 120, 120",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1.82, 0, 0",
            "NODE, 3, 1.82, 0, 2.73",
            "NODE, 4, 0, 0, 2.73",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 1, 1, 1, 1, 1, 1",
            "WWLL, 1, W1, 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)
        data = mdl_to_dict(mdl, relpath="inline.dat", solved=False)

        self.assertEqual(len(data["wood_rated_walls"]), 1)
        wall = data["wood_rated_walls"][0]
        self.assertEqual(wall["id"], 1)
        self.assertEqual(wall["name"], "W1")
        self.assertEqual(wall["nodes"], [1, 2, 3, 4])
        self.assertEqual(wall["model_requested"], "EQUIVALENT_BRACE")
        self.assertAlmostEqual(wall["qa_kN"], 1.96 * 2.0 * 1.82, places=6)

    def test_membrane_elements_in_model_json(self):
        lines = [
            "DMAT, 1, D1, 1000, 1000, 384.6153846, 0.3, 0, 0",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1, 0, 0",
            "NODE, 3, 0, 1, 0",
            "DIAP, 1, F1, 1, 0, 1, 100, 0, ,",
            "DMEM, 1, 1, 1, 2, 3",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 0, 1, 1, 1, 1, 1",
            "CONS, 3, 1, 0, 1, 1, 1, 1",
            "PLOD, 2, 0, 1.0, 0, 0, 0, 0, 0",
        ]
        mdl = parse_input(lines)
        solve_model(mdl)
        data = mdl_to_dict(mdl, relpath="inline.dat", solved=True)

        self.assertEqual(len(data["diaphragm_materials"]), 1)
        self.assertEqual(len(data["diaphragms"]), 1)
        self.assertEqual(len(data["membrane_elements"]), 1)
        self.assertTrue("0" in data["membrane_elements"][0]["stresses"])


class TestGuiApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from stb_gui.server import create_app
        except ImportError:
            cls.client = None
            return
        except RuntimeError:
            cls.client = None
            return
        cls.client = TestClient(create_app())

    def test_api_models(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/models")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue("examples/cantilever.dat" in body["models"])
        self.assertIsNone(body["default"])

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

    def test_api_project_for_sample(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["found"])
        self.assertIn("practice_wood_single_story.project.json", body["project_path"])
        section_ids = [s["id"] for s in body["sections"]]
        self.assertIn("building", section_ids)
        self.assertIn("load_conditions", section_ids)
        load_section = next(s for s in body["sections"] if s["id"] == "load_conditions")
        labels = [row["label"] for row in load_section["rows"]]
        self.assertIn("Rt (振動特性係数)", labels)
        self.assertIn("edit", body)
        self.assertIn("sections", body["edit"])

    def test_api_project_save_round_trip(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        get_r = self.client.get(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
        )
        self.assertEqual(get_r.status_code, 200)
        project = get_r.json()["raw"]
        project["building"]["name"] = "GUI Save Test"
        put_r = self.client.put(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
            json={"project": project},
        )
        self.assertEqual(put_r.status_code, 200)
        saved = put_r.json()["view"]["raw"]["building"]["name"]
        self.assertEqual(saved, "GUI Save Test")
        # restore original name
        project["building"]["name"] = "Practice Wood Single-Story Sample"
        self.client.put(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
            json={"project": project},
        )

    def test_api_project_save_empty_grids_placeholder(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        path = "data/UK_240416_floors_1to3_diaphragm.dat"
        get_r = self.client.get("/api/project", params={"path": path})
        self.assertEqual(get_r.status_code, 200)
        project = get_r.json()["raw"]
        self.assertEqual(project.get("grids"), [])
        # GUI used to send one blank placeholder row when grids is empty.
        project["building"]["name"] = "UK GUI Save Test"
        project["grids"] = [{"name": "", "direction": "x", "coordinate": 0}]
        put_r = self.client.put(
            "/api/project",
            params={"path": path},
            json={"project": project},
        )
        self.assertEqual(put_r.status_code, 400)
        project["grids"] = []
        put_r = self.client.put(
            "/api/project",
            params={"path": path},
            json={"project": project},
        )
        self.assertEqual(put_r.status_code, 200)
        saved_name = put_r.json()["view"]["raw"]["building"]["name"]
        self.assertEqual(saved_name, "UK GUI Save Test")
        project["building"]["name"] = "UK 240416 Floors 1-3 Diaphragm Sample"
        self.client.put(
            "/api/project",
            params={"path": path},
            json={"project": project},
        )

    def test_api_project_save_seismic_rt_default(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        get_r = self.client.get(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
        )
        self.assertEqual(get_r.status_code, 200)
        project = copy.deepcopy(get_r.json()["raw"])
        self.assertNotIn("rt", project["load_conditions"]["seismic"])
        bad = copy.deepcopy(project)
        bad["load_conditions"]["seismic"]["rt"] = 0
        put_r = self.client.put(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
            json={"project": bad},
        )
        self.assertEqual(put_r.status_code, 400)
        good = copy.deepcopy(project)
        good["building"]["name"] = "RT Default Save Test"
        put_r = self.client.put(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
            json={"project": good},
        )
        self.assertEqual(put_r.status_code, 200)
        seismic = put_r.json()["view"]["raw"]["load_conditions"]["seismic"]
        self.assertNotIn("rt", seismic)
        project["building"]["name"] = "Practice Wood Single-Story Sample"
        self.client.put(
            "/api/project",
            params={"path": "data/practice_wood_single_story.dat"},
            json={"project": project},
        )

    def test_api_project_missing_sidecar(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get(
            "/api/project",
            params={"path": "examples/cantilever.dat"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertFalse(body["found"])

    def test_index_html(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue("Structural Toolbox" in r.text)
        self.assertIn("btnNew", r.text)
        self.assertIn("btnOpen", r.text)
        self.assertIn("btnSave", r.text)
        self.assertIn("btnClose", r.text)
        self.assertIn("btnToggleSelect", r.text)
        self.assertIn("selectionPanel", r.text)
        self.assertIn("selectionMarquee", r.text)
        self.assertIn("elemContextMenu", r.text)
        self.assertIn("btnProject", r.text)
        self.assertIn("st-icon-256.png", r.text)
        self.assertNotIn("app-icon", r.text)
        self.assertIn("manifest.webmanifest", r.text)
        r_popup = self.client.get("/static/popup.html")
        self.assertEqual(r_popup.status_code, 200)

    def test_gui_open_url(self):
        from stb_gui.server import gui_open_url
        url = gui_open_url("127.0.0.1", 8765)
        self.assertEqual(url, "http://127.0.0.1:8765/")
        self.assertNotIn("?file=", url)

    def test_api_models_default_normalizes_backslashes(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        from fastapi.testclient import TestClient
        from stb_gui.server import create_app
        client = TestClient(create_app(default_model=r"data\UK_ROOF_240420.dat"))
        r = client.get("/api/models")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["default"], "data/UK_ROOF_240420.dat")

    def test_api_model_new_creates_comment_only_file(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        import os
        from stb_gui.input_format import NEW_MODEL_TEMPLATE
        from stb_gui.model_json import project_root
        r = self.client.post("/api/model/new")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["path"].startswith("data/"))
        self.assertTrue(body["path"].endswith(".dat"))
        self.assertEqual(body["text"], NEW_MODEL_TEMPLATE)
        full = os.path.join(project_root(), body["path"].replace("/", os.sep))
        try:
            self.assertTrue(os.path.isfile(full))
            with open(full, encoding="utf-8") as f:
                txt = f.read()
            self.assertEqual(txt, NEW_MODEL_TEMPLATE)
            m = self.client.get("/api/model", params={"path": body["path"], "solve": 0})
            self.assertEqual(m.status_code, 200)
            self.assertEqual(len(m.json()["nodes"]), 0)
        finally:
            if os.path.isfile(full):
                os.remove(full)

    def test_api_model_open_upload(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        import os
        from stb_gui.model_json import project_root
        text = "# upload test\n"
        r = self.client.post("/api/model/open", json={"filename": "_gui_upload_test.dat", "text": text})
        self.assertEqual(r.status_code, 200)
        rel = r.json()["path"]
        self.assertEqual(rel, "data/_gui_upload_test.dat")
        full = os.path.join(project_root(), rel.replace("/", os.sep))
        try:
            with open(full, encoding="utf-8") as f:
                self.assertEqual(f.read(), text)
        finally:
            if os.path.isfile(full):
                os.remove(full)

    def test_api_shutdown_returns_ok(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        with unittest.mock.patch("stb_gui.server.threading.Timer") as timer:
            with unittest.mock.patch("stb_gui.server._terminate_gui_server") as stop:
                inst = timer.return_value
                r = self.client.post("/api/shutdown")
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.json()["ok"])
                timer.assert_called_once()
                inst.start.assert_called_once()
                stop.assert_not_called()

    def test_api_heartbeat_returns_ok(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.post("/api/heartbeat")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])


if __name__ == "__main__":
    unittest.main()
