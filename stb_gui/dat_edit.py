"""Line-based editors for Structural Toolbox .dat input files."""

from __future__ import annotations

from typing import Any


def _split_record(line: str) -> tuple[str, list[str]] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [p.strip() for p in stripped.split(",")]
    if not parts or not parts[0]:
        return None
    return parts[0].upper(), parts


def _join_record(parts: list[str]) -> str:
    return ", ".join(parts)


def _parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as ex:
        raise ValueError("Invalid {0}: {1!r}".format(label, value)) from ex


def _section_ids(lines: list[str]) -> set[int]:
    out: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "SECT":
            out.add(_parse_int(rec[1][1], "section id"))
    return out


def _element_section_map(lines: list[str]) -> dict[int, int]:
    out: dict[int, int] = {}
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "ELEM":
            continue
        parts = rec[1]
        if len(parts) < 5:
            continue
        out[_parse_int(parts[1], "element id")] = _parse_int(parts[4], "section id")
    return out


def _format_ejnt_line(elem_id: int, ryi, rzi, ryj, rzj) -> str:
    def field(val) -> str:
        if val is None:
            return ""
        if isinstance(val, (int, float)):
            if abs(val) < 1e-12:
                return "0.0"
            if abs(val) < 1e-3:
                return "{0:.6g}".format(val)
            return "{0:.6g}".format(val)
        return str(val)

    return _join_record(
        [
            "EJNT",
            str(elem_id),
            field(ryi),
            field(rzi),
            field(ryj),
            field(rzj),
        ]
    )


EJNT_PRESETS: dict[str, tuple[Any, Any, Any, Any] | None] = {
    "pin": (0.0, None, 0.0, None),
    "spring_soft": (1e-6, 1e-6, 1e-6, 1e-6),
    "rigid": None,
}


def _elements_touching_nodes(lines: list[str], node_ids: set[int]) -> set[int]:
    elem_ids: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if not rec or rec[0] != "ELEM":
            continue
        parts = rec[1]
        if len(parts) < 4:
            continue
        eid = _parse_int(parts[1], "element id")
        ni = _parse_int(parts[2], "node i")
        nj = _parse_int(parts[3], "node j")
        if ni in node_ids or nj in node_ids:
            elem_ids.add(eid)
    return elem_ids


def delete_nodes(text: str, node_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(n) for n in node_ids}
    if not targets:
        raise ValueError("node_ids is empty")

    lines = text.splitlines()
    elem_targets = _elements_touching_nodes(lines, targets)
    elem_remove_tags = {"ELEM", "EJNT", "ELOD"}

    out: list[str] = []
    removed_nodes = 0
    removed_elems = 0
    removed_other = 0

    for line in lines:
        rec = _split_record(line)
        if not rec:
            out.append(line)
            continue
        tag, parts = rec
        rec_id = _parse_int(parts[1], tag + " id")

        if tag == "NODE" and rec_id in targets:
            removed_nodes += 1
            continue
        if tag == "CONS" and rec_id in targets:
            removed_other += 1
            continue
        if tag == "PLOD" and rec_id in targets:
            removed_other += 1
            continue
        if tag in elem_remove_tags and rec_id in elem_targets:
            removed_elems += 1
            continue
        if tag == "DMEM" and len(parts) >= 6:
            nids = [
                _parse_int(parts[i], "node id")
                for i in range(3, 6)
            ]
            if any(nid in targets for nid in nids):
                removed_other += 1
                continue
        out.append(line)

    if removed_nodes == 0:
        raise ValueError("No matching nodes found to delete")

    warnings = [
        "Deleted {0} node(s) {1}, {2} connected element record(s), {3} related load/constraint record(s).".format(
            removed_nodes,
            sorted(targets),
            removed_elems,
            removed_other,
        )
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def delete_elements(text: str, element_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")
    removed_tags = {"ELEM", "EJNT", "ELOD"}
    out: list[str] = []
    removed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] in removed_tags:
            parts = rec[1]
            rec_id = _parse_int(parts[1], rec[0] + " id")
            if rec_id in targets:
                removed += 1
                continue
        out.append(line)
    if removed == 0:
        raise ValueError("No matching elements found to delete")
    warnings = [
        "Deleted {0} record(s) for element id(s) {1}. Orphan nodes were kept.".format(
            removed, sorted(targets)
        )
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def set_element_section(text: str, element_ids: list[int], section_id: int) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    sec_id = int(section_id)
    if not targets:
        raise ValueError("element_ids is empty")

    section_ids = _section_ids(text.splitlines())
    if sec_id not in section_ids:
        raise ValueError("Unknown section id: {0}".format(sec_id))

    out: list[str] = []
    changed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "ELEM":
            parts = rec[1]
            eid = _parse_int(parts[1], "element id")
            if eid in targets:
                parts[4] = str(sec_id)
                line = _join_record(parts)
                changed += 1
        out.append(line)
    if changed == 0:
        raise ValueError("No matching elements found")
    return _ensure_trailing_newline("\n".join(out)), [
        "Changed section to {0} for {1} element(s).".format(sec_id, changed)
    ]


def set_material_for_elements(
    text: str, element_ids: list[int], material_id: int
) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    mat_id = int(material_id)
    if not targets:
        raise ValueError("element_ids is empty")

    lines = text.splitlines()
    elem_secs = _element_section_map(lines)
    sec_targets = {elem_secs[eid] for eid in targets if eid in elem_secs}
    if not sec_targets:
        raise ValueError("No matching elements found")

    mate_ids = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "MATE":
            mate_ids.add(_parse_int(rec[1][1], "material id"))
    if mat_id not in mate_ids:
        raise ValueError("Unknown material id: {0}".format(mat_id))

    out: list[str] = []
    changed_secs: set[int] = set()
    for line in lines:
        rec = _split_record(line)
        if rec and rec[0] == "SECT":
            parts = rec[1]
            sid = _parse_int(parts[1], "section id")
            if sid in sec_targets:
                parts[3] = str(mat_id)
                line = _join_record(parts)
                changed_secs.add(sid)
        out.append(line)

    warnings = [
        "Changed material to {0} on section id(s) {1}.".format(
            mat_id, sorted(changed_secs)
        ),
        "Note: all elements using the same section share the updated material.",
    ]
    return _ensure_trailing_newline("\n".join(out)), warnings


def set_ejnt_for_elements(
    text: str,
    element_ids: list[int],
    preset: str | None = None,
    values: list[Any] | None = None,
) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")

    if preset is not None:
        if preset not in EJNT_PRESETS:
            raise ValueError("Unknown EJNT preset: {0}".format(preset))
        preset_values = EJNT_PRESETS[preset]
        if preset_values is None:
            return remove_ejnt_for_elements(text, element_ids)
        ryi, rzi, ryj, rzj = preset_values
    elif values is not None and len(values) == 4:
        ryi, rzi, ryj, rzj = values
    else:
        raise ValueError("preset or values is required")

    lines = text.splitlines()
    existing: dict[int, int] = {}
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            existing[eid] = idx

    out = list(lines)
    updated = 0
    inserted: list[str] = []
    for eid in sorted(targets):
        new_line = _format_ejnt_line(eid, ryi, rzi, ryj, rzj)
        if eid in existing:
            out[existing[eid]] = new_line
            updated += 1
        else:
            inserted.append(new_line)

    if inserted:
        insert_at = _ejnt_insert_index(out)
        out[insert_at:insert_at] = inserted

    if updated == 0 and not inserted:
        raise ValueError("No matching elements found")

    label = preset or "custom"
    return _ensure_trailing_newline("\n".join(out)), [
        "Set EJNT ({0}) for {1} element(s).".format(label, len(targets))
    ]


def remove_ejnt_for_elements(text: str, element_ids: list[int]) -> tuple[str, list[str]]:
    targets = {int(e) for e in element_ids}
    if not targets:
        raise ValueError("element_ids is empty")
    out: list[str] = []
    removed = 0
    for line in text.splitlines():
        rec = _split_record(line)
        if rec and rec[0] == "EJNT":
            eid = _parse_int(rec[1][1], "element id")
            if eid in targets:
                removed += 1
                continue
        out.append(line)
    return _ensure_trailing_newline("\n".join(out)), [
        "Removed EJNT for {0} element(s); default rigid joints apply.".format(removed)
    ]


def _ejnt_insert_index(lines: list[str]) -> int:
    last_ejnt = -1
    last_elem = -1
    for idx, line in enumerate(lines):
        rec = _split_record(line)
        if not rec:
            continue
        if rec[0] == "ELEM":
            last_elem = idx
        elif rec[0] == "EJNT":
            last_ejnt = idx
    if last_ejnt >= 0:
        return last_ejnt + 1
    if last_elem >= 0:
        return last_elem + 1
    return len(lines)


def apply_edit_action(text: str, action: dict[str, Any]) -> tuple[str, list[str]]:
    op = action.get("action")
    element_ids = action.get("element_ids") or []
    node_ids = action.get("node_ids") or []
    if not isinstance(element_ids, list):
        raise ValueError("element_ids must be a list")
    if not isinstance(node_ids, list):
        raise ValueError("node_ids must be a list")

    if op == "delete":
        return delete_elements(text, element_ids)
    if op == "delete_nodes":
        return delete_nodes(text, node_ids)
    if op == "set_section":
        return set_element_section(text, element_ids, action["section_id"])
    if op == "set_material":
        return set_material_for_elements(text, element_ids, action["material_id"])
    if op == "set_ejnt":
        return set_ejnt_for_elements(
            text,
            element_ids,
            preset=action.get("preset"),
            values=action.get("values"),
        )
    if op == "remove_ejnt":
        return remove_ejnt_for_elements(text, element_ids)
    raise ValueError("Unknown action: {0!r}".format(op))


def validate_dat_text(text: str) -> None:
    import sys

    root = __import__("os").path.dirname(__import__("os").path.dirname(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError

    try:
        parse_input(text.splitlines())
    except StbParseError as ex:
        raise ValueError(str(ex)) from ex


def _ensure_trailing_newline(text: str) -> str:
    if not text.endswith("\n"):
        return text + "\n"
    return text
