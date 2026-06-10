"""Load-case type codes for LNME records."""

LC_TYPE_DL = 1
LC_TYPE_LL = 2
LC_TYPE_LL_E = 3
LC_TYPE_S = 4
LC_TYPE_W = 5
LC_TYPE_E = 6
LC_TYPE_CUSTOM = 7

LC_TYPE_CANONICAL = {
    LC_TYPE_DL: "DL",
    LC_TYPE_LL: "LL",
    LC_TYPE_LL_E: "LL(E)",
    LC_TYPE_S: "S",
    LC_TYPE_W: "W",
    LC_TYPE_E: "E",
    LC_TYPE_CUSTOM: "CUSTOM",
}

SEISMIC_WEIGHT_TYPES = frozenset({LC_TYPE_DL, LC_TYPE_LL_E})

_LEGACY_NAME_TO_TYPE = {
    "DL": LC_TYPE_DL,
    "DEAD": LC_TYPE_DL,
    "G": LC_TYPE_DL,
    "SW": LC_TYPE_DL,
    "LL": LC_TYPE_LL,
    "LIVE": LC_TYPE_LL,
    "LL(E)": LC_TYPE_LL_E,
    "LLE": LC_TYPE_LL_E,
    "LL_E": LC_TYPE_LL_E,
    "S": LC_TYPE_S,
    "SNOW": LC_TYPE_S,
    "W": LC_TYPE_W,
    "WIND": LC_TYPE_W,
    "E": LC_TYPE_E,
    "EQ": LC_TYPE_E,
    "SEISMIC": LC_TYPE_E,
    "EQX": LC_TYPE_E,
    "EQY": LC_TYPE_E,
    "EQ+X": LC_TYPE_E,
    "EQ-X": LC_TYPE_E,
    "EQ+Y": LC_TYPE_E,
    "EQ-Y": LC_TYPE_E,
}


def canonical_name(load_type: int, label: str = "") -> str:
    label = str(label or "").strip()
    if load_type == LC_TYPE_CUSTOM:
        return label or "CUSTOM"
    if label:
        return label
    return LC_TYPE_CANONICAL.get(int(load_type), "CUSTOM")


def parse_lnme_fields(type_token, label_token=""):
    """Parse LNME TYPE and optional LABEL from .dat columns."""

    label = str(label_token or "").strip()
    token = str(type_token or "").strip()
    if token == "":
        raise ValueError("LNME TYPE is required")

    try:
        load_type = int(token)
    except ValueError:
        key = token.upper()
        load_type = _LEGACY_NAME_TO_TYPE.get(key, LC_TYPE_CUSTOM)
        if load_type == LC_TYPE_CUSTOM and not label:
            label = token
        elif load_type == LC_TYPE_E and not label:
            label = token.upper()
        return load_type, label

    if load_type not in LC_TYPE_CANONICAL:
        raise ValueError("LNME TYPE must be 1..7")

    if load_type == LC_TYPE_CUSTOM and not label:
        raise ValueError("LNME TYPE=7 requires a LABEL")

    return load_type, label


def infer_axis_from_label(label: str):
    text = str(label or "").strip().upper()
    if text in ("EQX", "EQ+X", "EX", "X"):
        return "x", 1
    if text in ("EQ-X", "EX-", "EMX"):
        return "x", -1
    if text in ("EQY", "EQ+Y", "EY", "Y"):
        return "y", 1
    if text in ("EQ-Y", "EY-", "EMY"):
        return "y", -1
    return None, 1
