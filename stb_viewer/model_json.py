import os
import json

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_root():
    return _STB_ROOT


def resolve_model_path(path):
    """Resolve path under project root; reject paths outside the tree."""

    if path == None or path.strip() == "":
        raise ValueError("Model path is empty")

    root = os.path.realpath(project_root())
    if os.path.isabs(path):
        full = os.path.realpath(path)
    else:
        full = os.path.realpath(os.path.join(root, path))

    if not full.startswith(root + os.sep) and full != root:
        raise ValueError("Model path must be inside the project: " + path)

    if not os.path.isfile(full):
        raise ValueError("Model file not found: " + path)

    return full


def list_model_files():
    """Return relative paths of .dat files under data/ and examples/."""

    out = []
    for sub in ("data", "examples"):
        base = os.path.join(project_root(), sub)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if name.endswith(".dat"):
                out.append(os.path.join(sub, name).replace("\\", "/"))
    return out


def mdl_to_dict(mdl, relpath=None, solved=False):
    """Build a JSON-serializable model description for the web viewer."""

    nodes = []
    for n in sorted(mdl.nds, key=lambda x: x.id):
        item = {
            "id": n.id,
            "x": n.x,
            "y": n.y,
            "z": n.z,
        }
        if solved and n.disps is not None and mdl.lcs != None:
            item["disps"] = {}
            for i in range(len(mdl.lcs)):
                lc = mdl.lcs[i]
                d = n.disps[:, i]
                item["disps"][str(lc)] = [
                    float(d[0]), float(d[1]), float(d[2]),
                    float(d[3]), float(d[4]), float(d[5]),
                ]
        nodes.append(item)

    elements = []
    for e in sorted(mdl.elms, key=lambda x: x.id):
        sec_name = e.sec.name if e.sec != None else ""
        elements.append({
            "id": e.id,
            "n0": e.n0.id,
            "n1": e.n1.id,
            "section": sec_name,
        })

    supports = []
    for c in mdl.cons:
        supports.append({
            "node": c.nid,
            "fixed": [bool(x) for x in c.csts],
        })

    point_loads = []
    for l in mdl.lds:
        point_loads.append({
            "node": l.nid,
            "lc": l.lc,
            "px": float(l.lds[0]) * 1e-3,
            "py": float(l.lds[1]) * 1e-3,
            "pz": float(l.lds[2]) * 1e-3,
            "mx": float(l.lds[3]) * 1e-3,
            "my": float(l.lds[4]) * 1e-3,
            "mz": float(l.lds[5]) * 1e-3,
        })

    element_loads = []
    for el in mdl.elds:
        element_loads.append({
            "elem": el.eid,
            "lc": el.lc,
            "global": bool(el.isGlobal),
            "w": [
                float(el.lds[0]) * 1e-3, float(el.lds[1]) * 1e-3,
                float(el.lds[2]) * 1e-3, float(el.lds[3]) * 1e-3,
                float(el.lds[4]) * 1e-3, float(el.lds[5]) * 1e-3,
            ],
        })

    bounds = None
    if mdl.bounds != None:
        bounds = [
            float(mdl.bounds[0]), float(mdl.bounds[1]),
            float(mdl.bounds[2]), float(mdl.bounds[3]),
            float(mdl.bounds[4]), float(mdl.bounds[5]),
        ]

    return {
        "path": relpath,
        "solved": solved,
        "date_analysis": mdl.date_analysis,
        "load_cases": mdl.lcs if mdl.lcs != None else [],
        "bounds": bounds,
        "nodes": nodes,
        "elements": elements,
        "supports": supports,
        "point_loads": point_loads,
        "element_loads": element_loads,
    }


def load_model_dict(path, solve=False, quiet=True):
    """Parse (and optionally solve) a model file; return dict for JSON."""

    import sys
    root = project_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    from stb_engine import parse_input, read_input_file, solve_model
    from stb_engine.errors import StbParseError, StbSolveError

    full = resolve_model_path(path)
    relpath = os.path.relpath(full, root).replace("\\", "/")

    lines = read_input_file(full)
    try:
        mdl = parse_input(lines)
    except StbParseError as ex:
        raise ValueError(str(ex))

    mdl.filepath = full

    if solve:
        if quiet:
            old_stdout = sys.stdout
            devnull = open(os.devnull, "w")
            sys.stdout = devnull
            try:
                solve_model(mdl)
            except StbSolveError as ex:
                raise ValueError(str(ex))
            finally:
                devnull.close()
                sys.stdout = old_stdout
        else:
            try:
                solve_model(mdl)
            except StbSolveError as ex:
                raise ValueError(str(ex))

    return mdl_to_dict(mdl, relpath=relpath, solved=solve)


def model_to_json(path, solve=False, quiet=True):
    data = load_model_dict(path, solve=solve, quiet=quiet)
    return json.dumps(data, indent=2)
