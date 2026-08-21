"""Probe cheaper settings for Solve.CheckStability.

CheckStability currently costs 29 s of the 194 s spent on a 16,000-node model.
It runs a shift-invert Lanczos pass with k=6 and ARPACK's default tolerance,
which needs ~100 back-substitutions. This script measures, for a set of models:

  - how many SuperLU back-substitutions each setting actually costs
  - the smallest relative eigenvalue each setting reports
  - the LU pivot ratio min|U_ii| / max|U_ii|, which is free once the matrix is
    factorized and could serve as a gate that skips the eigensolve entirely

The point is to pick a cheaper setting, and a gate threshold, from measured
separation between sound models and real mechanisms rather than by guesswork.

Usage:
    python tools/bench/probe_stability.py
"""

import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in [_ROOT, os.path.join(_ROOT, "classes")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator, eigsh, splu

from stb_engine import parse_input, read_input_file


class CountingLU(object):
    """Wraps a SuperLU object to count back-substitutions."""

    def __init__(self, lu):
        self.lu = lu
        self.calls = 0

    def solve(self, b):
        self.calls += 1
        return self.lu.solve(b)


def build_system(lines):
    """Reproduce the matrix Solve.solve hands to splu, without solving."""

    import solve as solve_module

    mdl = parse_input(lines)
    s = solve_module.Solve.__new__(solve_module.Solve)
    s.mdl = mdl
    s.ndof = 6
    s.num_row = 0
    s.num_lcs = 0
    s.kG_orig = None
    s.constrained_rows = []

    kG = s.CreateGlobalStiffMX(apply_constraints=False)
    lm = s.CreateLoadMx(apply_constraints=False)
    s.InitConstrainedReactions(lm)

    if getattr(mdl, "mpcs", []):
        T, reduced = s.BuildMPCTransformation()
        kG = T.T @ kG @ T
        lm = T.T @ lm
        kG, lm = s.ApplySupportConstraints(kG, lm, reduced)
    else:
        kG, lm = s.ApplySupportConstraints(kG, lm)

    return kG.tocsc(), np.asarray(lm)


def spectrum_scale(kG):
    try:
        return float(abs(eigsh(kG, k=1, which="LM",
                              return_eigenvectors=False, tol=1.0e-3)[0]))
    except Exception:
        return float(abs(kG).sum(axis=1).max())


def measure(name, lines):
    try:
        kG, lm = build_system(lines)
    except Exception as ex:
        print("%-34s BUILD FAILED: %s" % (name, str(ex)[:60]))
        return

    n = kG.shape[0]
    t = time.perf_counter()
    try:
        lu = splu(kG)
    except RuntimeError as ex:
        print("%-34s n=%-7d SINGULAR (%s)" % (name, n, str(ex)[:40]))
        return
    t_lu = time.perf_counter() - t

    piv = np.abs(lu.U.diagonal())
    pivot_ratio = float(piv.min() / piv.max()) if piv.size and piv.max() > 0 else 0.0

    scale = spectrum_scale(kG)

    print("%-34s n=%-7d LU %.2fs  pivot_ratio %.3e" % (name, n, t_lu, pivot_ratio))

    for label, k, tol in [("k=6 tol=0   (current)", 6, 0),
                          ("k=6 tol=1e-4", 6, 1.0e-4),
                          ("k=3 tol=1e-4", 3, 1.0e-4),
                          ("k=1 tol=1e-4", 1, 1.0e-4)]:
        counter = CountingLU(lu)
        OPinv = LinearOperator(kG.shape, matvec=counter.solve, dtype=np.float64)
        t = time.perf_counter()
        try:
            vals = eigsh(kG, k=min(k, n - 1), sigma=0.0, which="LM",
                         OPinv=OPinv, tol=tol, return_eigenvectors=False)
            dt = time.perf_counter() - t
            rel = float(np.min(np.abs(vals)) / scale)
            print("    %-22s %7.2fs  %4d solves  min|lam|/scale %.3e"
                  % (label, dt, counter.calls, rel))
        except Exception as ex:
            print("    %-22s FAILED %s" % (label, str(ex)[:50]))


def main():
    base = read_input_file(os.path.join(_ROOT, "data", "UK_240416.dat"))

    cases = [("data/UK_240416.dat", base)]

    for name in ["UK_240416panel.dat", "building_4f_x4y2.dat"]:
        p = os.path.join(_ROOT, "data", name)
        if os.path.isfile(p):
            cases.append(("data/" + name, read_input_file(p)))

    for name in ["frame_basic_1000.dat", "frame_basic_4000.dat"]:
        p = os.path.join(_ROOT, ".bench", name)
        if os.path.isfile(p):
            cases.append((".bench/" + name, read_input_file(p)))

    # A genuine near-mechanism: a loaded node on a hair-thin member.
    cases.append(("UK_240416 + near-mechanism", base + [
        "SECT, 9001, TINY, 1, 0, 0.06, 0.06",
        "NODE, 9001, 0, 0, 99",
        "ELEM, 9001, 9001, 1, 9001, 0.0",
        "PLOD, 9001, 0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0",
    ]))

    for name, lines in cases:
        measure(name, lines)
        print("")


if __name__ == "__main__":
    main()
