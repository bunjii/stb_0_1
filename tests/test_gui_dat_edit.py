import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui.dat_edit import (
    apply_edit_action,
    apply_ejnt_lines_text,
    delete_elements,
    delete_nodes,
    ejnt_lines_for_elements,
    set_element_section,
    set_ejnt_for_elements,
    set_material_for_elements,
    validate_dat_text,
)


SAMPLE = """MATE, 1, Sugi, 9500, 633, 5.0, 3.0e-06, 20
MATE, 2, Hinoki, 10000, 667, 5.0, 3.0e-06, 22
SECT, 1, C120, 1, 0, 120.0, 120.0
SECT, 2, B240, 1, 0, 120.0, 240.0
SECT, 3, B300, 2, 0, 120.0, 300.0
NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 3.0, 0.0, 3.0
NODE, 3, 0.0, 0.0, 0.0
NODE, 4, 3.0, 0.0, 0.0
ELEM, 1, 1, 2, 2, 0.0
ELEM, 2, 3, 1, 1, 0.0
ELEM, 3, 4, 2, 1, 0.0
CONS, 3, 1, 1, 1, 1, 1, 1
CONS, 4, 1, 1, 1, 1, 1, 1
"""


class TestDatEdit(unittest.TestCase):

    def test_delete_nodes_removes_connected_elements(self):
        text = SAMPLE + "EJNT, 1, 0.0, , 0.0,\nPLOD, 1, 0, 0, -1, 0, 0, 0\n"
        out, warnings = delete_nodes(text, [1])
        self.assertNotIn("NODE, 1,", out)
        self.assertNotIn("ELEM, 1,", out)
        self.assertNotIn("ELEM, 2,", out)
        self.assertNotIn("EJNT, 1,", out)
        self.assertIn("ELEM, 3,", out)
        self.assertIn("NODE, 2,", out)
        validate_dat_text(out)
        self.assertTrue(any("connected element" in w for w in warnings))

    def test_delete_elements_removes_elem_and_ejnt(self):
        text = SAMPLE + "EJNT, 1, 0.0, , 0.0,\nELOD, 1, 0, 1, 0, 0, -1, 0, 0, -1\n"
        out, warnings = delete_elements(text, [1])
        self.assertNotIn("ELEM, 1,", out)
        self.assertIn("ELEM, 2,", out)
        self.assertNotIn("EJNT, 1,", out)
        self.assertNotIn("ELOD, 1,", out)
        validate_dat_text(out)
        self.assertTrue(warnings)

    def test_set_element_section(self):
        out, _ = set_element_section(SAMPLE, [1, 3], 3)
        self.assertIn("ELEM, 1, 1, 2, 3, 0.0", out)
        self.assertIn("ELEM, 3, 4, 2, 3, 0.0", out)
        validate_dat_text(out)

    def test_set_material_for_elements(self):
        out, warnings = set_material_for_elements(SAMPLE, [1], 2)
        self.assertIn("SECT, 2, B240, 2, 0, 120.0, 240.0", out)
        validate_dat_text(out)
        self.assertTrue(any("share" in w.lower() for w in warnings))

    def test_set_ejnt_pin_and_remove(self):
        out, _ = set_ejnt_for_elements(SAMPLE, [1], preset="pin")
        self.assertIn("EJNT, 1,", out)
        validate_dat_text(out)
        out2, _ = apply_edit_action(out, {
            "action": "remove_ejnt",
            "element_ids": [1],
        })
        self.assertNotIn("EJNT, 1,", out2)
        validate_dat_text(out2)

    def test_ejnt_lines_for_elements_existing_and_template(self):
        text = SAMPLE + "EJNT, 1, 0.0, , 0.0,\n"
        rows = ejnt_lines_for_elements(text, [1, 2])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["exists"])
        self.assertIn("EJNT, 1,", rows[0]["line"])
        self.assertFalse(rows[1]["exists"])
        self.assertIn("EJNT, 2,", rows[1]["line"])

    def test_apply_ejnt_lines_text_update_insert_remove(self):
        text = SAMPLE + "EJNT, 1, 0.0, , 0.0,\nEJNT, 2, 1e-06, 1e-06, 1e-06, 1e-06,\n"
        out, warnings = apply_ejnt_lines_text(
            text,
            [1, 2],
            "EJNT, 1, 1e-06, 1e-06, 1e-06, 1e-06,\n",
        )
        self.assertIn("EJNT, 1, 1e-06", out)
        self.assertNotIn("EJNT, 2,", out)
        validate_dat_text(out)
        self.assertTrue(any("removed" in w.lower() for w in warnings))

        out2, _ = apply_ejnt_lines_text(
            SAMPLE,
            [1],
            "EJNT, 1, 0.0, , 0.0,\n",
        )
        self.assertIn("EJNT, 1,", out2)
        validate_dat_text(out2)

    def test_apply_ejnt_lines_text_ignores_comment_header(self):
        text = SAMPLE + "EJNT, 1, 0.0, , 0.0,\n"
        from stb_gui.input_format import EJNT_EDITOR_HEADER
        out, _ = apply_ejnt_lines_text(
            text,
            [1],
            EJNT_EDITOR_HEADER + "EJNT, 1, 1e-06, 1e-06, 1e-06, 1e-06,\n",
        )
        self.assertIn("EJNT, 1, 1e-06", out)
        validate_dat_text(out)

    def test_apply_edit_action_set_ejnt_lines(self):
        out, warnings = apply_edit_action(SAMPLE, {
            "action": "set_ejnt_lines",
            "element_ids": [1],
            "lines_text": "EJNT, 1, 0.0, , 0.0,\n",
        })
        self.assertIn("EJNT, 1,", out)
        validate_dat_text(out)
        self.assertTrue(warnings)


class TestGuiEditApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from stb_gui.server import create_app
        except ImportError:
            cls.client = None
            return
        cls.client = TestClient(create_app())

    def test_api_model_edit_set_section(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        path = "examples/cantilever.dat"
        before = self.client.get("/api/input", params={"path": path})
        self.assertEqual(before.status_code, 200)
        try:
            r = self.client.post(
                "/api/model/edit",
                params={"path": path},
                json={"action": "set_section", "element_ids": [0], "section_id": 0},
            )
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertTrue(body["ok"])
            after = self.client.get("/api/model", params={"path": path, "solve": 0})
            self.assertEqual(after.json()["elements"][0]["section_id"], 0)
        finally:
            self.client.put(
                "/api/input",
                params={"path": path},
                json={"text": before.text},
            )

    def test_api_model_includes_catalog(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        r = self.client.get("/api/model", params={"path": "examples/cantilever.dat", "solve": 0})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("materials", body)
        self.assertIn("sections", body)
        self.assertGreater(len(body["sections"]), 0)

    def test_api_model_ejnt_lines(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        path = "examples/cantilever.dat"
        r = self.client.get(
            "/api/model/ejnt-lines",
            params={"path": path, "element_ids": "0"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["path"], path)
        self.assertEqual(len(body["lines"]), 1)
        self.assertEqual(body["lines"][0]["element_id"], 0)
        self.assertIn("line", body["lines"][0])
        self.assertIn("header", body)
        self.assertIn("EJNT", body["header"])


if __name__ == "__main__":
    unittest.main()
