import os
import sys
import subprocess
import unittest
from datetime import datetime

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_engine import run_from_file
from stb_practice import build_practice_summary
from stb_project import load_project_file
from stb_reports import build_confirmation_draft, render_confirmation_draft_markdown


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


def _run_stb(args):
    cmd = [sys.executable, "-m", "stb_cli"] + args
    return subprocess.run(
        cmd,
        cwd=_STB_ROOT,
        capture_output=True,
        text=True,
    )


class TestReportDraft(unittest.TestCase):

    def test_markdown_draft_contains_practice_and_check_values(self):
        project = load_project_file(_data_path("practice_wood_single_story.project.json"))
        mdl, txt = run_from_file(_data_path(project.dat_path))
        summary = build_practice_summary(mdl, project)

        markdown = render_confirmation_draft_markdown(
            mdl,
            project,
            analysis_text=txt,
            generated_at=datetime(2026, 6, 5, 10, 0, 0),
            program_version="0.1.0",
        )

        self.assertTrue("# Practice Wood Single-Story Summary" in markdown)
        self.assertTrue("## 5. 重心・剛心・偏心率" in markdown)
        self.assertTrue("## 6. 木造梁・柱・筋かいの基本検定" in markdown)
        self.assertTrue("## 7. 照合メモ" in markdown)
        self.assertTrue("解析出力 NDSP | あり" in markdown)
        self.assertTrue("wood_columns" in markdown)
        self.assertTrue("最大検定比" in markdown)

        center_text = "X={0:.3f} m, Y={1:.3f} m".format(
            summary.center_of_mass.x,
            summary.center_of_mass.y,
        )
        self.assertTrue(center_text in markdown)

    def test_builds_html_from_same_draft(self):
        project = load_project_file(_data_path("practice_wood_single_story.project.json"))
        mdl, txt = run_from_file(_data_path(project.dat_path))

        draft = build_confirmation_draft(
            mdl,
            project,
            analysis_text=txt,
            generated_at=datetime(2026, 6, 5, 10, 0, 0),
            program_version="0.1.0",
        )

        self.assertTrue("<!doctype html>" in draft.html)
        self.assertTrue("<h1>Practice Wood Single-Story Summary</h1>" in draft.html)
        self.assertTrue("<table>" in draft.html)
        self.assertTrue("wood_columns" in draft.html)

    def test_cli_report_writes_markdown_and_html(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        md_path = os.path.join(out_dir, "practice_report.md")
        html_path = os.path.join(out_dir, "practice_report.html")
        project_path = _data_path("practice_wood_single_story.project.json")

        r = _run_stb(["report", project_path, "-o", md_path, "--format", "markdown", "-q", "-v"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(os.path.isfile(md_path))
        f = open(md_path, "r", encoding="utf-8")
        markdown = f.read()
        f.close()
        self.assertTrue("確認申請前の検算" in markdown)
        self.assertTrue("照合メモ" in markdown)

        r = _run_stb(["report", project_path, "-o", html_path, "--format", "html", "-q"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(os.path.isfile(html_path))
        f = open(html_path, "r", encoding="utf-8")
        html = f.read()
        f.close()
        self.assertTrue("<html lang=\"ja\">" in html)
        self.assertTrue("<td>wood_columns</td>" in html)


if __name__ == "__main__":
    unittest.main()

