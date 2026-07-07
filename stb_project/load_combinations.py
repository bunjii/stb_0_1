"""Apply project.json load-combination settings to an analysis model."""

from __future__ import annotations

import os
import sys
from typing import Any, Iterable, Sequence

_CLASSES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from classes.ld import Lcmb

LCMB_BLOCK_START = "# --- PROJECT LCMB (auto) ---"
LCMB_BLOCK_END = "# --- END PROJECT LCMB (auto) ---"


def apply_load_combinations_to_model(mdl: Any, project: Any) -> bool:
    """Replace model LCMB definitions with project-side load combinations.

    The low-level ``.dat`` parser expands LCMB records during ``Mdl`` creation.
    When project.json defines combinations, remove those generated loads and
    rebuild them from the sidecar settings.
    """

    combinations = tuple(getattr(project.load_conditions, "load_combinations", ()))
    if not combinations:
        return False

    for attr in ("lds", "elds", "glds", "alds", "dloads"):
        values = getattr(mdl, attr, [])
        setattr(mdl, attr, [v for v in values if not getattr(v, "combi", False)])

    mdl.lcmbs = [
        Lcmb(c.load_case, c.name, list(c.factors), list(c.load_cases), c.duration)
        for c in combinations
    ]
    mdl.load_combination_durations = {
        c.load_case: c.duration for c in combinations
    }

    mdl.CreateCombinedLoads()
    mdl.AssignCompIds()
    mdl.FindNodeElmForLd()
    mdl.FindElmsForAld()
    return True


def build_lcmb_block(combinations: Sequence[Any]) -> str:
    lines = [LCMB_BLOCK_START]
    for c in combinations:
        lines.append(
            Lcmb(c.load_case, c.name, list(c.factors), list(c.load_cases), c.duration)
            .OutputLcmbInfo()
            .rstrip("\n")
        )
        lines.append("# LCMB_DURATION, {0}, {1}".format(c.load_case, c.duration))
    lines.append(LCMB_BLOCK_END)
    return "\n".join(lines) + "\n"


def replace_project_lcmb_block(lines: Iterable[str], block_text: str) -> list[str]:
    src = list(lines)
    start = None
    end = None
    for i, line in enumerate(src):
        stripped = line.strip()
        if stripped == LCMB_BLOCK_START:
            start = i
        elif stripped == LCMB_BLOCK_END and start is not None:
            end = i
            break

    block_lines = block_text.splitlines()
    if not block_text.endswith("\n") and block_text:
        block_lines.append("")

    if start is not None and end is not None:
        return src[:start] + block_lines + src[end + 1:]

    cleaned = _remove_lcmb_records(src)
    has_lcmb_section = any(
        line.strip().startswith("# --- LOAD COMBINATION") or "LOAD COMBINATION(LCMB)" in line.strip().upper()
        for line in cleaned
    )
    if not has_lcmb_section:
        if cleaned and cleaned[-1] != "":
            cleaned.append("")
        cleaned.extend([
            "# --- LOAD COMBINATION(LCMB) ---",
            "#       LC,     NAME,   FC1,   LC1,   FC2,   LC2,   FC3,   LC3,...",
        ])
    insert_at = _find_lcmb_insert_index(cleaned)
    return cleaned[:insert_at] + block_lines + cleaned[insert_at:]


def apply_project_load_combinations_to_dat(dat_path: str, project: Any) -> int:
    combinations = tuple(getattr(project.load_conditions, "load_combinations", ()))
    if not combinations:
        return 0

    with open(dat_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    block = build_lcmb_block(combinations)
    updated = replace_project_lcmb_block(lines, block)
    text = "\n".join(updated)
    if updated and updated[-1] != "":
        text += "\n"

    from dat_format import write_dat_text

    write_dat_text(dat_path, text)
    return len(combinations)


def sync_project_lcmb_lines(lines: Iterable[str], project: Any) -> list[str]:
    combinations = tuple(getattr(project.load_conditions, "load_combinations", ()))
    if not combinations:
        return list(lines)
    block = build_lcmb_block(combinations)
    return replace_project_lcmb_block(lines, block)


def _remove_lcmb_records(lines: Sequence[str]) -> list[str]:
    out = []
    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("LCMB,") or upper.startswith("# LCMB_DURATION,"):
            continue
        out.append(line)
    return out


def _find_lcmb_insert_index(lines: Sequence[str]) -> int:
    in_lcmb_section = False
    last_lcmb_header = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        upper = stripped.upper()
        if stripped.startswith("# --- LOAD COMBINATION") or "LOAD COMBINATION(LCMB)" in upper:
            in_lcmb_section = True
            last_lcmb_header = i
            continue
        if in_lcmb_section and stripped.startswith("# ---") and "LCMB" not in upper and "LOAD COMBINATION" not in upper:
            return i
        if in_lcmb_section and stripped.startswith("#"):
            last_lcmb_header = i

    if last_lcmb_header is not None:
        return last_lcmb_header + 1

    return len(lines)
