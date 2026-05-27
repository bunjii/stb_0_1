import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_viewer.model_json import (
    load_model_dict,
    list_model_files,
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

    def test_load_cantilever_solved(self):
        data = load_model_dict("examples/cantilever.dat", solve=True)
        self.assertTrue(data["solved"])
        self.assertTrue("disps" in data["nodes"][1])
        self.assertTrue("0" in data["nodes"][1]["disps"])

    def test_reject_path_outside_project(self):
        raised = False
        try:
            resolve_model_path("/etc/passwd")
        except ValueError:
            raised = True
        self.assertTrue(raised)


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

    def test_index_html(self):
        if self.client == None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue("STB Viewer" in r.text)


if __name__ == "__main__":
    unittest.main()
