from typing import Iterable, Sequence


SEISMIC_BLOCK_START = "# --- SEISMIC DLOD (auto) ---"
SEISMIC_BLOCK_END = "# --- END SEISMIC DLOD (auto) ---"


def format_dlod_line(dl) -> str:
    return dl.OutputDLoadInfo().rstrip("\n")


def build_seismic_block(dloads: Sequence) -> str:
    lines = [SEISMIC_BLOCK_START]
    for dl in dloads:
        lines.append(format_dlod_line(dl))
    lines.append(SEISMIC_BLOCK_END)
    return "\n".join(lines) + "\n"


def replace_seismic_dlod_block(lines: Iterable[str], block_text: str) -> list:
    src = list(lines)
    start = None
    end = None
    for i, line in enumerate(src):
        if line.strip() == SEISMIC_BLOCK_START:
            start = i
        elif line.strip() == SEISMIC_BLOCK_END and start is not None:
            end = i
            break

    block_lines = block_text.splitlines()
    if not block_text.endswith("\n") and block_text:
        block_lines.append("")

    if start is not None and end is not None:
        return src[:start] + block_lines + src[end + 1:]

    insert_at = _find_dlod_insert_index(src)
    return src[:insert_at] + block_lines + src[insert_at:]


def _find_dlod_insert_index(lines: Sequence[str]) -> int:
    last_dlod = None
    in_dlod_section = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# --- DIAPHRAGM LOAD"):
            in_dlod_section = True
            continue
        if in_dlod_section and stripped.startswith("# ---") and "DLOD" not in stripped.upper():
            return i
        if stripped.startswith("# --- END ") and "DLOD (AUTO)" in stripped.upper():
            last_dlod = i
        if stripped.startswith("DLOD,"):
            last_dlod = i

    if last_dlod is not None:
        return last_dlod + 1
    if in_dlod_section:
        return len(lines)
    return len(lines)


def sync_seismic_dlod_lines(lines: Iterable[str], dloads: Sequence) -> list:
    if not dloads:
        return list(lines)
    cleaned = _remove_dlod_for_records(lines, dloads)
    block = build_seismic_block(dloads)
    return replace_seismic_dlod_block(cleaned, block)


def _remove_dlod_for_records(lines: Iterable[str], dloads: Sequence) -> list:
    targets = {(dl.diap_id, dl.lc) for dl in dloads}
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("DLOD,"):
            parts = [p.strip() for p in stripped.split(",")]
            if len(parts) >= 3:
                try:
                    diap_id = int(parts[1])
                    lc = int(parts[2])
                    if (diap_id, lc) in targets:
                        continue
                except ValueError:
                    pass
        out.append(line)
    return out


WIND_BLOCK_START = "# --- WIND DLOD (auto) ---"
WIND_BLOCK_END = "# --- END WIND DLOD (auto) ---"


def build_wind_block(dloads: Sequence) -> str:
    lines = [WIND_BLOCK_START]
    for dl in dloads:
        lines.append(format_dlod_line(dl))
    lines.append(WIND_BLOCK_END)
    return "\n".join(lines) + "\n"


def replace_wind_dlod_block(lines: Iterable[str], block_text: str) -> list:
    src = list(lines)
    start = None
    end = None
    for i, line in enumerate(src):
        if line.strip() == WIND_BLOCK_START:
            start = i
        elif line.strip() == WIND_BLOCK_END and start is not None:
            end = i
            break

    block_lines = block_text.splitlines()
    if not block_text.endswith("\n") and block_text:
        block_lines.append("")

    if start is not None and end is not None:
        return src[:start] + block_lines + src[end + 1:]

    insert_at = _find_dlod_insert_index(src)
    return src[:insert_at] + block_lines + src[insert_at:]


def apply_wind_to_dat(dat_path: str, dloads: Sequence) -> None:
    f = open(dat_path, "r", encoding="utf-8")
    lines = f.read().splitlines()
    f.close()

    lines = _remove_dlod_for_records(lines, dloads)
    block = build_wind_block(dloads)
    updated = replace_wind_dlod_block(lines, block)

    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from dat_format import write_dat_text

    text = "\n".join(updated)
    if updated and updated[-1] != "":
        text += "\n"
    write_dat_text(dat_path, text)


def apply_seismic_to_dat(dat_path: str, dloads: Sequence) -> None:
    f = open(dat_path, "r", encoding="utf-8")
    lines = f.read().splitlines()
    f.close()

    lines = _remove_dlod_for_records(lines, dloads)
    block = build_seismic_block(dloads)
    updated = replace_seismic_dlod_block(lines, block)

    import os
    import sys

    classes = os.path.join(os.path.dirname(os.path.dirname(__file__)), "classes")
    if classes not in sys.path:
        sys.path.insert(0, classes)
    from dat_format import write_dat_text

    text = "\n".join(updated)
    if updated and updated[-1] != "":
        text += "\n"
    write_dat_text(dat_path, text)
