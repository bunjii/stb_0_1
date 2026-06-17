import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui.dat_edit import (
    apply_edit_action,
    apply_ejnt_lines_text,
    create_dmem,
    create_wwll,
    delete_dmem,
    delete_elements,
    delete_nodes,
    delete_wwll,
    ejnt_lines_for_elements,
    set_diap_timber_multiplier,
    set_element_section,
    set_ejnt_for_elements,
    set_material_for_elements,
    set_cons_for_nodes,
    set_wwll_model,
    set_wwll_multiplier,
    validate_dat_text,
)
from stb_gui.dat_format_headers import prepare_dat_text_for_write, write_dat_text


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


DIAPHRAGM_SAMPLE = """MATE, 1, Sugi, 9500, 633, 5.0, 3.0e-06, 20
NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 3.0, 0.0, 3.0
NODE, 3, 0.0, 0.0, 0.0
DIAP, 10, 2F_MAIN, 1, 1, 2.0, 1000, 0.0, 0.006667, 1820
DMEM, 1001, 10, 1, 2, 3
"""

WWLL_SAMPLE = """MATE, 1, Sugi, 9500, 633, 5.0, 3.0e-06, 20
NODE, 11, 0.0, 0.0, 0.0
NODE, 12, 1.82, 0.0, 0.0
NODE, 22, 1.82, 0.0, 2.73
NODE, 21, 0.0, 0.0, 2.73
WWLL, 1, W1_X, 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 11, 12, 22, 21, 10, 1
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

    def test_create_dmem_appends_record(self):
        out, warnings = create_dmem(DIAPHRAGM_SAMPLE, 10, [1, 2, 3])
        self.assertIn("DMEM, 1001,", out)
        self.assertRegex(out, r"DMEM,\s+1002,\s+10,\s+1,\s+2,\s+3")
        validate_dat_text(out)
        self.assertTrue(any("Created DMEM 1002" in w for w in warnings))

    def test_create_dmem_adds_section_when_missing(self):
        sample = """MATE, 1, Sugi, 9500, 633, 5.0, 3.0e-06, 20
NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 3.0, 0.0, 3.0
NODE, 3, 0.0, 3.0, 3.0
DIAP, 10, 2F_MAIN, 1, 1, 2.0, 1000, 0.0, 0.006667, 1820
"""
        out, _ = create_dmem(sample, 10, [1, 2, 3])
        self.assertIn("# --- DIAPHRAGM MEMBRANE ELEMENT(DMEM) ---", out)
        self.assertRegex(out, r"DMEM,\s+1001,\s+10,\s+1,\s+2,\s+3")
        validate_dat_text(out)

    def test_create_dmem_rejects_duplicate_nodes(self):
        with self.assertRaises(ValueError):
            create_dmem(DIAPHRAGM_SAMPLE, 10, [1, 1, 2])

    def test_delete_dmem(self):
        out, warnings = delete_dmem(DIAPHRAGM_SAMPLE, [1001])
        self.assertNotIn("DMEM, 1001,", out)
        self.assertIn("DIAP, 10,", out)
        validate_dat_text(out)
        self.assertTrue(any("DMEM" in w for w in warnings))

    def test_create_wwll_appends_record(self):
        out, warnings = create_wwll(WWLL_SAMPLE, [11, 12, 22, 21], multiplier=2.5)
        self.assertIn("WWLL, 1,", out)
        self.assertRegex(out, r"WWLL,\s+2,\s+W2,\s+1,\s+2\.5")
        self.assertRegex(out, r"WWLL,\s+2,.*11,\s+12,\s+22,\s+21")
        validate_dat_text(out)
        self.assertTrue(any("Created WRW 2" in w for w in warnings))

    def test_create_wwll_orders_corners_and_infers_dir(self):
        sample = """MATE, 1, Sugi, 9500, 633, 5.0, 3.0e-06, 20
NODE, 11, 0.0, 0.0, 0.0
NODE, 12, 1.82, 0.0, 0.0
NODE, 22, 1.82, 0.0, 2.73
NODE, 21, 0.0, 0.0, 2.73
"""
        out, warnings = create_wwll(sample, [22, 11, 21, 12], multiplier=2.0, model=0)
        self.assertRegex(out, r"WWLL,\s+1,\s+W1,\s+0,\s+2")
        self.assertRegex(out, r"WWLL,\s+1,.*11,\s+12,\s+22,\s+21")
        validate_dat_text(out)
        self.assertTrue(any("DIR=X" in w for w in warnings))

    def test_create_wwll_adds_section_when_missing(self):
        sample = """MATE, 1, Sugi, 9500, 633, 5.0, 3.0e-06, 20
NODE, 11, 0.0, 0.0, 0.0
NODE, 12, 1.82, 0.0, 0.0
NODE, 22, 1.82, 0.0, 2.73
NODE, 21, 0.0, 0.0, 2.73
CONS, 11, 1, 1, 1, 1, 1, 1
"""
        out, _ = create_wwll(sample, [11, 12, 22, 21])
        self.assertIn("# --- WOOD RATED WALL(WWLL) ---", out)
        self.assertRegex(out, r"WWLL,\s+1,")
        validate_dat_text(out)

    def test_create_wwll_rejects_non_rectangle(self):
        sample = """NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 1.0, 0.0, 0.0
NODE, 3, 0.5, 0.0, 1.0
NODE, 4, 0.5, 0.0, 2.0
"""
        with self.assertRaises(ValueError):
            create_wwll(sample, [1, 2, 3, 4])

    def test_delete_wwll(self):
        out, warnings = delete_wwll(WWLL_SAMPLE, [1])
        self.assertNotIn("WWLL, 1,", out)
        validate_dat_text(out)
        self.assertTrue(any("WWLL" in w for w in warnings))

    def test_set_wwll_multiplier(self):
        out, _ = set_wwll_multiplier(WWLL_SAMPLE, [1], 3.5)
        self.assertIn("WWLL, 1, W1_X, 0, 3.5,", out)
        validate_dat_text(out)

    def test_set_wwll_model(self):
        out, warnings = set_wwll_model(WWLL_SAMPLE, [1], 1)
        self.assertIn("WWLL, 1, W1_X, 1, 2.0,", out)
        validate_dat_text(out)
        self.assertTrue(any("panel" in w for w in warnings))

    def test_apply_edit_action_set_wwll_model(self):
        out, _ = apply_edit_action(WWLL_SAMPLE, {
            "action": "set_wwll_model",
            "wwll_ids": [1],
            "model": 1,
        })
        self.assertIn("WWLL, 1, W1_X, 1, 2.0,", out)
        validate_dat_text(out)

    def test_set_diap_timber_multiplier(self):
        out, _ = set_diap_timber_multiplier(DIAPHRAGM_SAMPLE, [10], 2.5)
        self.assertIn("DIAP, 10, 2F_MAIN, 1, 1, 2.5,", out)
        validate_dat_text(out)

    def test_apply_edit_action_delete_dmem(self):
        out, _ = apply_edit_action(DIAPHRAGM_SAMPLE, {
            "action": "delete_dmem",
            "dmem_ids": [1001],
        })
        self.assertNotIn("DMEM, 1001,", out)
        validate_dat_text(out)

    def test_apply_edit_action_create_dmem(self):
        out, _ = apply_edit_action(DIAPHRAGM_SAMPLE, {
            "action": "create_dmem",
            "node_ids": [1, 2, 3],
            "diap_id": 10,
        })
        self.assertRegex(out, r"DMEM,\s+1002,\s+10,\s+1,\s+2,\s+3")
        validate_dat_text(out)

    def test_apply_edit_action_create_wwll(self):
        out, _ = apply_edit_action(WWLL_SAMPLE, {
            "action": "create_wwll",
            "node_ids": [11, 12, 22, 21],
            "multiplier": 3.0,
            "model": 1,
        })
        self.assertRegex(out, r"WWLL,\s+2,\s+W2,\s+1,\s+3")
        validate_dat_text(out)


class TestConsEdit(unittest.TestCase):

    def test_set_cons_add_update_remove(self):
        text = "\n".join([
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 0, 1, 0",
        ]) + "\n"
        out, warnings = set_cons_for_nodes(text, [1], [1, 1, 1, 0, 0, 0])
        self.assertIn("CONS,      1,    1,    1,    1,    0,    0,    0", out)
        validate_dat_text(out)
        out2, _ = set_cons_for_nodes(out, [1], [1, 1, 1, 1, 1, 1])
        self.assertIn("CONS,      1,    1,    1,    1,    1,    1,    1", out2)
        out3, warnings3 = set_cons_for_nodes(out2, [1], [0, 0, 0, 0, 0, 0])
        self.assertNotIn("CONS,      1,", out3)
        self.assertIn("Removed CONS", warnings3[0])

    def test_apply_edit_action_set_cons(self):
        out, _ = apply_edit_action(SAMPLE, {
            "action": "set_cons",
            "node_ids": [3],
            "fixed": [1, 1, 1, 1, 1, 1],
        })
        self.assertIn("CONS,      3,    1,    1,    1,    1,    1,    1", out)
        validate_dat_text(out)


class TestDatTextWrite(unittest.TestCase):

    def test_prepare_dat_text_strips_cr_and_preserves_blank_lines(self):
        text = "MATE, 1, A, 1, 1, 1, 0, 1\r\n\r\nNODE, 1, 0, 0, 0\r\n"
        out = prepare_dat_text_for_write(text)
        self.assertEqual(out, "MATE, 1, A, 1, 1, 1, 0, 1\n\nNODE, 1, 0, 0, 0\n")
        self.assertNotIn("\r", out)

    def test_write_dat_text_crlf_roundtrip_does_not_grow_blank_lines(self):
        import os
        import tempfile

        original = "A\n\nB\n"
        crlf = original.replace("\n", "\r\n")
        fd, path = tempfile.mkstemp(suffix=".dat")
        os.close(fd)
        try:
            for _ in range(3):
                write_dat_text(path, crlf)
                with open(path, encoding="utf-8") as fh:
                    saved = fh.read()
                self.assertEqual(saved, original)
                crlf = saved.replace("\n", "\r\n")
        finally:
            os.remove(path)


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

    def test_api_input_save_crlf_does_not_grow_blank_lines(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        import os
        import tempfile

        original = "# sample\n\nMATE, 0, A, 1, 1, 1, 0, 1\n"
        fd, full = tempfile.mkstemp(suffix=".dat", dir=os.path.join(_STB_ROOT, "examples"))
        os.close(fd)
        rel = os.path.relpath(full, _STB_ROOT).replace("\\", "/")
        try:
            write_dat_text(full, original)
            crlf = original.replace("\n", "\r\n")
            for _ in range(3):
                r = self.client.put(
                    "/api/input",
                    params={"path": rel},
                    json={"text": crlf},
                )
                self.assertEqual(r.status_code, 200, r.text)
                got = self.client.get("/api/input", params={"path": rel})
                self.assertEqual(got.status_code, 200)
                self.assertEqual(got.text, original)
                crlf = got.text.replace("\n", "\r\n")
        finally:
            os.remove(full)

    def test_api_input_save_unchanged_reports_not_changed(self):
        if self.client is None:
            self.skipTest("fastapi not installed")
        import os
        import tempfile

        original = "# sample\n\nMATE, 0, A, 1, 1, 1, 0, 1\n"
        fd, full = tempfile.mkstemp(suffix=".dat", dir=os.path.join(_STB_ROOT, "examples"))
        os.close(fd)
        rel = os.path.relpath(full, _STB_ROOT).replace("\\", "/")
        try:
            write_dat_text(full, original)
            r = self.client.put(
                "/api/input",
                params={"path": rel},
                json={"text": original},
            )
            self.assertEqual(r.status_code, 200, r.text)
            self.assertFalse(r.json().get("changed"))
        finally:
            os.remove(full)

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
