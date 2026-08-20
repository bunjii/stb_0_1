"""Record and compare golden analysis results.

Used as a safety net for refactors that change how the linear system is built
or solved (for example the move from dense to sparse matrices). The goldens
store the numeric results only, so they tolerate round-off differences from a
different assembly order but catch any real change in behaviour.

Usage
-----
    python tools/bench/golden.py record          # (re)record every model
    python tools/bench/golden.py record --only UK_240416
    python tools/bench/golden.py check           # compare without touching files
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

GOLDEN_DIR = os.path.join(_REPO_ROOT, "tests", "golden")
INDEX_PATH = os.path.join(GOLDEN_DIR, "index.json")

# Models chosen to cover the distinct solver paths: plain frames, area loads,
# CST membrane diaphragms, timber diaphragms, rigid diaphragms (MPC) and
# rated wood walls.
DEFAULT_MODELS = [
    "examples/cantilever.dat",
    "data/input01.dat",
    "data/input02.dat",
    "data/area_load_panel.dat",
    "data/building_4f_x4y2.dat",
    "data/practice_wood_single_story.dat",
    "data/UK_ROOF_240420.dat",
    "data/UK_240416.dat",
    "data/UK_240416_floors_1to3_diaphragm.dat",
    "data/UK_240416_floors_1to3_rigid_diaphragm.dat",
]

# Round-off from a different assembly or factorisation order shows up around
# 1e-14 relative; anything above these thresholds is a behaviour change.
RTOL = 1.0e-7
ATOL_SCALE = 1.0e-9


def solve_path(rel_path):
    from stb_engine import parse_input, read_input_file, solve_model

    abs_path = os.path.join(_REPO_ROOT, rel_path)
    mdl = parse_input(read_input_file(abs_path))
    mdl.filepath = abs_path
    solve_model(mdl)
    return mdl


def capture(mdl):
    """Reduce a solved model to plain arrays, ordered deterministically."""

    n_lc = int(mdl.max_clc)

    nodes = sorted(mdl.nds, key=lambda n: n.cid)
    disps = np.zeros((len(nodes), 6, n_lc), dtype=np.float64)
    reacts = np.zeros((len(nodes), 6, n_lc), dtype=np.float64)
    for i, n in enumerate(nodes):
        if n.disps is not None:
            disps[i] = np.asarray(n.disps, dtype=np.float64).reshape(6, n_lc)
        if n.reacts is not None:
            # Nd.reacts is stored as [load case][dof].
            reacts[i] = np.asarray(n.reacts, dtype=np.float64).reshape(n_lc, 6).T

    elements = sorted(mdl.elms, key=lambda e: e.id)
    forces = np.zeros((len(elements), 14, n_lc), dtype=np.float64)
    for i, e in enumerate(elements):
        if getattr(e, "forces", None) is not None:
            forces[i] = np.asarray(e.forces, dtype=np.float64).reshape(14, n_lc)

    return {
        "disps": disps,
        "reacts": reacts,
        "forces": forces,
        "node_ids": np.array([n.id for n in nodes], dtype=np.int64),
        "element_ids": np.array([e.id for e in elements], dtype=np.int64),
    }


def compare(expected, actual):
    """Return a list of human-readable differences (empty when they match)."""

    problems = []
    for key in sorted(expected):
        want = expected[key]
        got = actual.get(key)
        if got is None:
            problems.append("{0}: missing from current results".format(key))
            continue
        if want.shape != got.shape:
            problems.append("{0}: shape {1} != {2}".format(key, got.shape, want.shape))
            continue
        if want.dtype.kind in "iu":
            if not np.array_equal(want, got):
                problems.append("{0}: integer values changed".format(key))
            continue

        scale = float(np.max(np.abs(want))) if want.size else 0.0
        atol = ATOL_SCALE * max(scale, 1.0e-30)
        if np.allclose(got, want, rtol=RTOL, atol=atol):
            continue

        delta = np.abs(got - want)
        idx = np.unravel_index(int(np.argmax(delta)), delta.shape)
        problems.append(
            "{0}: max abs diff {1:.3e} at {2} (expected {3:.6e}, got {4:.6e}, "
            "tolerance {5:.3e})".format(
                key, float(delta[idx]), idx, float(want[idx]), float(got[idx]), atol
            )
        )
    return problems


def golden_path(rel_path):
    stem = os.path.splitext(os.path.basename(rel_path))[0]
    return os.path.join(GOLDEN_DIR, stem + ".npz")


def load_golden(rel_path):
    with np.load(golden_path(rel_path)) as data:
        return {k: data[k] for k in data.files}


def read_index():
    if not os.path.isfile(INDEX_PATH):
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)["models"]


def record(models):
    if not os.path.isdir(GOLDEN_DIR):
        os.makedirs(GOLDEN_DIR)

    recorded = []
    for rel_path in models:
        mdl = solve_path(rel_path)
        arrays = capture(mdl)
        path = golden_path(rel_path)
        np.savez_compressed(path, **arrays)
        recorded.append(rel_path)
        print("recorded {0:52s} nodes={1:5d} elms={2:5d} lcs={3:2d}  {4:7.1f} KB".format(
            rel_path, len(mdl.nds), len(mdl.elms), mdl.max_clc,
            os.path.getsize(path) / 1024.0,
        ))

    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        json.dump({"models": recorded, "rtol": RTOL, "atol_scale": ATOL_SCALE}, fh, indent=2)
    total = sum(os.path.getsize(golden_path(p)) for p in recorded)
    print("index written to {0} ({1} models, {2:.1f} KB total)".format(
        INDEX_PATH, len(recorded), total / 1024.0))


def check(models):
    failures = 0
    for rel_path in models:
        if not os.path.isfile(golden_path(rel_path)):
            print("MISSING  {0}".format(rel_path))
            failures += 1
            continue
        problems = compare(load_golden(rel_path), capture(solve_path(rel_path)))
        if problems:
            failures += 1
            print("CHANGED  {0}".format(rel_path))
            for p in problems:
                print("           {0}".format(p))
        else:
            print("ok       {0}".format(rel_path))
    print("{0} model(s) checked, {1} differing".format(len(models), failures))
    return failures


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("action", choices=["record", "check"])
    p.add_argument("--only", default=None,
                   help="substring filter on the model path")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    models = read_index() or DEFAULT_MODELS
    if args.action == "record":
        models = DEFAULT_MODELS
    if args.only:
        models = [m for m in models if args.only in m]
    if not models:
        print("no models selected")
        return 1

    if args.action == "record":
        record(models)
        return 0
    return 1 if check(models) else 0


if __name__ == "__main__":
    raise SystemExit(main())
