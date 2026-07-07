"""Synchronize project-managed load case names to .dat LNME records."""

from __future__ import annotations

import os
import sys
from typing import Iterable, Sequence

_CLASSES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from ld import Lcase


LNME_BLOCK_START = "# --- PROJECT LNME (auto) ---"
LNME_BLOCK_END = "# --- END PROJECT LNME (auto) ---"


def project_floor_load_lnames(project) -> list:
    """Return unique LNME records required by project-managed floor loads."""

    by_lc = {}
    for entry in getattr(project.load_conditions, "floor_loads", ()):
        load_type = 3 if entry.role == "LL_E" else 2
        label = entry.name or ("LL(E)" if entry.role == "LL_E" else "LL")
        current = by_lc.get(entry.load_case)
        next_value = (load_type, label)
        if current is not None and current != next_value:
            raise ValueError(
                "Floor load LC {0} has conflicting LNME definitions".format(entry.load_case)
            )
        by_lc[entry.load_case] = next_value
    return [
        Lcase(lc, load_type, label)
        for lc, (load_type, label) in sorted(by_lc.items())
    ]


def build_project_lnme_block(lnames: Sequence) -> str:
    lines = [LNME_BLOCK_START]
    for lname in lnames:
        lines.append(lname.OutputLnameInfo().rstrip("\n"))
    lines.append(LNME_BLOCK_END)
    return "\n".join(lines) + "\n"


def replace_project_lnme_block(lines: Iterable[str], block_text: str, managed_lcs: Sequence[int]) -> list[str]:
    src = list(lines)
    start = None
    end = None
    for i, line in enumerate(src):
        stripped = line.strip()
        if stripped == LNME_BLOCK_START:
            start = i
        elif stripped == LNME_BLOCK_END and start is not None:
            end = i
            break

    block_lines = block_text.splitlines()
    if not block_text.endswith("\n") and block_text:
        block_lines.append("")

    if start is not None and end is not None:
        cleaned = src[:start] + src[end + 1:]
    else:
        cleaned = src
    cleaned = _remove_lnme_records(cleaned, managed_lcs)

    has_lnme_section = any(
        line.strip().startswith("# --- LOAD NAME") or "LOAD NAME(LNME)" in line.strip().upper()
        for line in cleaned
    )
    if not has_lnme_section:
        if cleaned and cleaned[-1] != "":
            cleaned.append("")
        cleaned.extend([
            "# --- LOAD NAME(LNME) ---",
            "#       LC, TYPE, LABEL",
            "#   TYPE: 1=DL  2=LL  3=LL(E)  4=S  5=W  6=E  7=CUSTOM(label required)",
        ])

    insert_at = _find_lnme_insert_index(cleaned)
    return cleaned[:insert_at] + block_lines + cleaned[insert_at:]


def sync_project_lnme_lines(lines: Iterable[str], project) -> list[str]:
    lnames = project_floor_load_lnames(project)
    if not lnames:
        return list(lines)
    block = build_project_lnme_block(lnames)
    return replace_project_lnme_block(lines, block, [ln.lc for ln in lnames])


def apply_project_lnme_to_dat(dat_path: str, project) -> int:
    lnames = project_floor_load_lnames(project)
    if not lnames:
        return 0

    with open(dat_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    block = build_project_lnme_block(lnames)
    updated = replace_project_lnme_block(lines, block, [ln.lc for ln in lnames])
    text = "\n".join(updated)
    if updated and updated[-1] != "":
        text += "\n"

    from dat_format import write_dat_text

    write_dat_text(dat_path, text)
    return len(lnames)


def _remove_lnme_records(lines: Sequence[str], managed_lcs: Sequence[int]) -> list[str]:
    targets = {int(lc) for lc in managed_lcs}
    if not targets:
        return list(lines)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("LNME,"):
            parts = [p.strip() for p in stripped.split(",")]
            if len(parts) >= 2:
                try:
                    if int(parts[1]) in targets:
                        continue
                except ValueError:
                    pass
        out.append(line)
    return out


def _find_lnme_insert_index(lines: Sequence[str]) -> int:
    in_lnme_section = False
    last_lnme_header = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        upper = stripped.upper()
        if stripped.startswith("# --- LOAD NAME") or "LOAD NAME(LNME)" in upper:
            in_lnme_section = True
            last_lnme_header = i
            continue
        if in_lnme_section and stripped.startswith("# ---") and "LNME" not in upper and "LOAD NAME" not in upper:
            return i
        if in_lnme_section and stripped.startswith("#"):
            last_lnme_header = i
        if in_lnme_section and upper.startswith("LNME,"):
            last_lnme_header = i

    if last_lnme_header is not None:
        return last_lnme_header + 1

    return len(lines)
