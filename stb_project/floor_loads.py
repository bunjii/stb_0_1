"""Synchronize project-managed floor loads to .dat DLOD TYPE 4 records."""

from __future__ import annotations

import os
import sys
from typing import Iterable, Sequence

_CLASSES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from diaphragm import DiaphragmLoad


FLOOR_DLOD_BLOCK_START = "# --- PROJECT FLOOR DLOD (auto) ---"
FLOOR_DLOD_BLOCK_END = "# --- END PROJECT FLOOR DLOD (auto) ---"


def project_floor_dloads(project) -> list:
    """Return DLOD TYPE 4 records required by project-managed floor loads."""

    dloads = []
    seen = {}
    for entry in getattr(project.load_conditions, "floor_loads", ()):
        key = (entry.diaphragm_id, entry.load_case)
        current = (entry.role, entry.pressure_kN_m2)
        if key in seen and seen[key] != current:
            raise ValueError(
                "Floor load DIAP/LC {0}/{1} has conflicting settings".format(
                    entry.diaphragm_id, entry.load_case
                )
            )
        seen[key] = current
        dloads.append(DiaphragmLoad(
            entry.diaphragm_id,
            entry.load_case,
            DiaphragmLoad.WEIGHT,
            _weight=entry.pressure_kN_m2 * 1.0e3,
            _ax=0.0,
            _ay=0.0,
            _source="PROJECT",
        ))
    return dloads


def build_project_floor_dlod_block(dloads: Sequence) -> str:
    lines = [FLOOR_DLOD_BLOCK_START]
    for dl in dloads:
        lines.append(dl.OutputDLoadInfo().rstrip("\n"))
    lines.append(FLOOR_DLOD_BLOCK_END)
    return "\n".join(lines) + "\n"


def replace_project_floor_dlod_block(
    lines: Iterable[str],
    block_text: str,
    managed_keys: Sequence[tuple[int, int]],
) -> list[str]:
    src = list(lines)
    start = None
    end = None
    for i, line in enumerate(src):
        stripped = line.strip()
        if stripped == FLOOR_DLOD_BLOCK_START:
            start = i
        elif stripped == FLOOR_DLOD_BLOCK_END and start is not None:
            end = i
            break

    block_lines = block_text.splitlines()
    if not block_text.endswith("\n") and block_text:
        block_lines.append("")

    if start is not None and end is not None:
        cleaned = src[:start] + src[end + 1:]
    else:
        cleaned = src
    cleaned = _remove_managed_weight_dlod_records(cleaned, managed_keys)
    insert_at = _find_dlod_insert_index(cleaned)
    return cleaned[:insert_at] + block_lines + cleaned[insert_at:]


def sync_project_floor_dlod_lines(lines: Iterable[str], project) -> list[str]:
    dloads = project_floor_dloads(project)
    if not dloads:
        return list(lines)
    _validate_diaphragms_exist(lines, [dl.diap_id for dl in dloads])
    block = build_project_floor_dlod_block(dloads)
    keys = [(dl.diap_id, dl.lc) for dl in dloads]
    return replace_project_floor_dlod_block(lines, block, keys)


def apply_project_floor_loads_to_dat(dat_path: str, project) -> int:
    dloads = project_floor_dloads(project)
    if not dloads:
        return 0

    with open(dat_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    _validate_diaphragms_exist(lines, [dl.diap_id for dl in dloads])
    block = build_project_floor_dlod_block(dloads)
    updated = replace_project_floor_dlod_block(lines, block, [(dl.diap_id, dl.lc) for dl in dloads])
    text = "\n".join(updated)
    if updated and updated[-1] != "":
        text += "\n"

    from dat_format import write_dat_text

    write_dat_text(dat_path, text)
    return len(dloads)


def _validate_diaphragms_exist(lines: Iterable[str], diaphragm_ids: Sequence[int]) -> None:
    required = {int(v) for v in diaphragm_ids}
    if not required:
        return
    existing = set()
    for line in lines:
        stripped = line.strip()
        if not stripped.upper().startswith("DIAP,"):
            continue
        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) >= 2:
            try:
                existing.add(int(parts[1]))
            except ValueError:
                pass
    missing = sorted(required - existing)
    if missing:
        raise ValueError("Floor load references unknown DIAP id(s): " + ", ".join(str(v) for v in missing))


def _remove_managed_weight_dlod_records(lines: Sequence[str], managed_keys: Sequence[tuple[int, int]]) -> list[str]:
    targets = {(int(diap), int(lc)) for diap, lc in managed_keys}
    if not targets:
        return list(lines)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("DLOD,"):
            parts = [p.strip() for p in stripped.split(",")]
            if len(parts) >= 4:
                try:
                    key = (int(parts[1]), int(parts[2]))
                    load_type = int(parts[3])
                    if key in targets and load_type == 4:
                        continue
                except ValueError:
                    pass
        out.append(line)
    return out


def _find_dlod_insert_index(lines: Sequence[str]) -> int:
    last_dlod = None
    in_dlod_section = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        upper = stripped.upper()
        if stripped.startswith("# --- DIAPHRAGM LOAD"):
            in_dlod_section = True
            continue
        if in_dlod_section and stripped.startswith("# ---") and "DLOD" not in upper:
            return i
        if stripped.startswith("# --- END ") and "DLOD (AUTO)" in upper:
            last_dlod = i
        if upper.startswith("DLOD,"):
            last_dlod = i

    if last_dlod is not None:
        return last_dlod + 1
    if in_dlod_section:
        return len(lines)
    return len(lines)
