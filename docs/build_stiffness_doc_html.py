#!/usr/bin/env python3
"""element_stiffness_matrix.md → HTML（KaTeX 付き）を生成する。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "element_stiffness_matrix.md"
OUT_PATH = ROOT / "element_stiffness_matrix.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>要素剛性マトリックスの考え方</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" crossorigin="anonymous">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5.5.1/github-markdown-light.min.css">
  <style>
    body { box-sizing: border-box; max-width: 980px; margin: 0 auto; padding: 2rem 1.5rem; background: #fff; }
    .markdown-body { font-size: 16px; line-height: 1.6; }
    .markdown-body pre { background: #f6f8fa; }
    .katex-display { overflow-x: auto; overflow-y: hidden; padding: 0.25em 0; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" crossorigin="anonymous"></script>
</head>
<body class="markdown-body">
  <article id="content"></article>
  <script>
    const SOURCE = __MD_JSON__;
    document.getElementById("content").innerHTML = marked.parse(SOURCE, { gfm: true });
    function renderMath() {
      if (typeof renderMathInElement !== "function") return;
      renderMathInElement(document.getElementById("content"), {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false }
        ],
        throwOnError: false
      });
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", renderMath);
    } else {
      renderMath();
    }
  </script>
</body>
</html>
"""


def build(md_path: Path = MD_PATH, out_path: Path = OUT_PATH) -> Path:
    md_text = md_path.read_text(encoding="utf-8")
    html = HTML_TEMPLATE.replace("__MD_JSON__", json.dumps(md_text, ensure_ascii=False))
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> int:
    if not MD_PATH.is_file():
        print(f"not found: {MD_PATH}", file=sys.stderr)
        return 1
    out = build()
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
