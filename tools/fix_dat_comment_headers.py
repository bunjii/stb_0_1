#!/usr/bin/env python3
"""Align .dat section headers and data-line comma columns."""

from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLASSES = os.path.join(ROOT, "classes")
if _CLASSES not in sys.path:
    sys.path.insert(0, _CLASSES)

from dat_format import (  # noqa: E402
    SECTION_HEADERS,
    ensure_section_blank_lines,
    fmts_for_record,
    is_schema_comment_row,
    parse_record_line,
    reformat_record_line,
)

SECTION_TITLE_RE = re.compile(r"^#\s*---\s*.+---\s*$")
TITLE_KEY_RE = re.compile(r"^#\s*---.+?\(([A-Z0-9_]+)\)")
RECORD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*,")
COMMENT_RECORD_RE = re.compile(r"^#\s+[A-Z][A-Z0-9_]*\s*,")
COLUMN_HEADER_RE = re.compile(r"^#\s+\w+,\s+\w+")
UNIT_LINE_RE = re.compile(r"^#\s+.*\([A-Za-z0-9/^2]+\)")


def record_key(line: str) -> str | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    m = RECORD_RE.match(s)
    if not m:
        return None
    return m.group(1).upper()


def is_structural_comment(line: str, header_set: set[str]) -> bool:
    s = line.rstrip("\n")
    if s in header_set:
        return True
    body = s.strip()
    if not body.startswith("#"):
        return False
    if SECTION_TITLE_RE.match(body):
        return True
    if COMMENT_RECORD_RE.match(body):
        return True
    if re.match(r"^#\s+,", body):
        return True
    if COLUMN_HEADER_RE.match(body):
        return True
    if re.match(r"^#\s+ID,", body):
        return True
    if UNIT_LINE_RE.match(body):
        return True
    if re.match(r"^#\s+(\(|TYPE:|SRC:|MODEL:|DIR:|TRGT:|CONN:|EG:|FC|MAG)", body):
        return True
    if re.match(r"^#\s+\w+:\s", body):
        return True
    return False


def section_title_for_key(key: str) -> str:
    return SECTION_HEADERS[key][0]


def find_header_region(lines: list[str], key: str, data_idx: int) -> tuple[int, int]:
    """Return [start, end) comment region to replace before the first data row."""
    our_title = section_title_for_key(key)
    end = data_idx
    title_indices: list[int] = []
    i = end - 1
    while i >= 0:
        s = lines[i].strip()
        if not s:
            i -= 1
            continue
        if record_key(lines[i]) is not None:
            break
        if s == our_title:
            title_indices.append(i)
        elif SECTION_TITLE_RE.match(s):
            break
        i -= 1

    if title_indices:
        return title_indices[-1], end

    start = end
    while start > 0:
        prev = lines[start - 1].strip()
        if not prev:
            start -= 1
            continue
        if record_key(lines[start - 1]) is not None or SECTION_TITLE_RE.match(prev):
            break
        if prev.startswith("#"):
            start -= 1
            continue
        break
    return start, end


def collect_user_comments(lines: list[str], start: int, end: int, headers: list[str]) -> list[str]:
    header_set = set(headers)
    extras: list[str] = []
    for i in range(start, end):
        s = lines[i].rstrip("\n")
        if not s.strip():
            continue
        if is_structural_comment(s, header_set):
            continue
        extras.append(s)
    return extras


def fix_file(path: str) -> bool:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    first_idx: dict[str, int] = {}
    for i, line in enumerate(lines):
        key = record_key(line)
        if key and key in SECTION_HEADERS and key not in first_idx:
            first_idx[key] = i

    changed = False

    for key in sorted(first_idx, key=lambda k: first_idx[k], reverse=True):
        idx = first_idx[key]
        headers = SECTION_HEADERS[key]
        run_start, run_end = find_header_region(lines, key, idx)
        extras = collect_user_comments(lines, run_start, run_end, headers)
        new_block = [h + "\n" for h in headers]
        if extras:
            new_block.append("\n")
            new_block.extend(e + "\n" for e in extras)
        new_block.append("\n")
        if lines[run_start:run_end] != new_block:
            lines[run_start:run_end] = new_block
            changed = True

    for i, line in enumerate(lines):
        key = record_key(line)
        if not key:
            continue
        new_line = reformat_record_line(line) + "\n"
        if new_line != line:
            lines[i] = new_line
            changed = True

    if fix_template_sections(lines):
        changed = True

    if ensure_section_blank_lines(lines):
        changed = True

    if changed:
        from dat_format import write_dat_text

        write_dat_text(path, "".join(lines))
    return changed


def fix_template_sections(lines: list[str]) -> bool:
    """Rewrite comment-only section blocks (templates with no live data rows)."""
    indices: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = TITLE_KEY_RE.match(line.strip())
        if m and m.group(1) in SECTION_HEADERS:
            indices.append((i, m.group(1)))

    changed = False
    for pos in range(len(indices) - 1, -1, -1):
        i, key = indices[pos]
        j = indices[pos + 1][0] if pos + 1 < len(indices) else len(lines)
        if any(record_key(lines[k]) for k in range(i, j)):
            continue
        examples: list[str] = []
        for line in lines[i:j]:
            body = line.strip()
            if not body.startswith("#"):
                continue
            body = body[1:].strip()
            parsed = parse_record_line(body)
            if (
                parsed
                and parsed[0] == key
                and fmts_for_record(parsed[0], parsed[1]) is not None
                and not is_schema_comment_row(parsed[0], parsed[1])
            ):
                examples.append("# " + reformat_record_line(body))
        new_block = [h + "\n" for h in SECTION_HEADERS[key]]
        new_block.extend(ex + "\n" for ex in examples)
        new_block.append("#\n")
        if lines[i:j] != new_block:
            lines[i:j] = new_block
            changed = True
    return changed


def main() -> int:
    patterns = [
        os.path.join(ROOT, "data", "*.dat"),
        os.path.join(ROOT, "examples", "*.dat"),
    ]
    paths: list[str] = []
    for pat in patterns:
        paths.extend(sorted(glob.glob(pat)))

    updated = []
    for path in paths:
        if fix_file(path):
            updated.append(path)

    for path in updated:
        print("updated:", os.path.relpath(path, ROOT))
    if not updated:
        print("no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
