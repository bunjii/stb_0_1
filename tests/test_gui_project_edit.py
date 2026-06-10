import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_project import load_project_file
from stb_gui.project_edit import build_project_edit_form


class TestProjectEditForm(unittest.TestCase):

    def test_build_edit_form_includes_seismic_fields(self):
        project = load_project_file(
            os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        )
        form = build_project_edit_form(project)
        load_section = next(s for s in form["sections"] if s["id"] == "load_conditions")
        paths = [f["path"] for f in load_section["fields"]]
        self.assertIn("load_conditions.seismic.ci", paths)
        self.assertIn("load_conditions.seismic.rt", paths)
        self.assertIn("table", load_section)
        self.assertEqual(load_section["table"]["path"], "load_conditions.diaphragms")


if __name__ == "__main__":
    unittest.main()
