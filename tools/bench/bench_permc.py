"""Benchmark scipy.sparse.linalg.splu permc_spec orderings on FEM stiffness matrices.

Captures the exact constrained CSC stiffness matrix and load vector that
Solve.solve passes to splu (via a one-shot monkey-patch), then times each
permc_spec factorization and back-substitution independently.

Examples
--------
    python tools/bench/bench_permc.py
    python tools/bench/bench_permc.py --model .bench/frame_basic_4000.dat
    python tools/bench/bench_permc.py --all-models --skip-natural
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ctypes
import ctypes.wintypes
import os
import sys
import time

import numpy as np
from scipy.sparse.linalg import splu as _real_splu

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CLASSES_DIR = os.path.join(_REPO_ROOT, "classes")
for _p in (_REPO_ROOT, _CLASSES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PERMC_SPECS = ("COLAMD", "MMD_AT_PLUS_A", "MMD_ATA", "NATURAL")

DEFAULT_MODEL = os.path.join(_REPO_ROOT, ".bench", "frame_basic_1000.dat")

ALL_MODELS = (
    os.path.join(_REPO_ROOT, ".bench", "frame_basic_1000.dat"),
    os.path.join(_REPO_ROOT, ".bench", "frame_basic_4000.dat"),
    os.path.join(_REPO_ROOT, ".bench", "frame_basic_8000.dat"),
    os.path.join(_REPO_ROOT, "data", "UK_240416.dat"),
)


def peak_rss_bytes():
    """Peak resident set size of this process, or None if unavailable."""

    if os.name == "nt":
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
        get_info = kernel32.K32GetProcessMemoryInfo
        get_info.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            ctypes.wintypes.DWORD,
        ]
        get_info.restype = ctypes.wintypes.BOOL

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        ok = get_info(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        return int(counters.PeakWorkingSetSize) if ok else None

    try:
        import resource
    except ImportError:
        return None
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maxrss) if sys.platform == "darwin" else int(maxrss) * 1024


def _fmt_bytes(n):
    if n is None:
        return "-"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0 or unit == "TB":
            return "{0:.1f} {1}".format(value, unit)
        value /= 1024.0


def _max_rel_diff(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    scale = np.maximum(np.abs(b), np.finfo(np.float64).tiny)
    return float(np.max(np.abs(a - b) / scale))


class _CapturingLU:
    """Delegate to a real SuperLU object while recording the RHS on first solve."""

    def __init__(self, lu, store):
        self._lu = lu
        self._store = store

    def solve(self, rhs, *args, **kwargs):
        # Only the untransposed solve carries the real right-hand side; the
        # transposed ones come from the condition-number estimate.
        if not args and not kwargs and self._store.get("lm") is None:
            self._store["lm"] = np.asarray(rhs, dtype=np.float64).copy()
        return self._lu.solve(rhs, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._lu, name)


def capture_system(dat_path):
    """Run one full solve and return (kG, lm, model_stats) from the splu call."""

    import classes.solve as solve_mod
    from classes.solve import Solve
    from stb_engine import parse_input, read_input_file

    store = {"kG": None, "lm": None}
    original_splu = solve_mod.splu

    def patched_splu(kG, *args, **kwargs):
        store["kG"] = kG.copy()
        lu = original_splu(kG, *args, **kwargs)
        return _CapturingLU(lu, store)

    lines = read_input_file(dat_path)
    mdl = parse_input(lines)
    mdl.filepath = dat_path

    solve_mod.splu = patched_splu
    try:
        Solve(mdl)
    finally:
        solve_mod.splu = original_splu

    if store["kG"] is None or store["lm"] is None:
        raise RuntimeError("failed to capture stiffness matrix / load vector from splu")

    nodes = len(getattr(mdl, "nds", []))
    stats = {
        "nodes": nodes,
        "elements": len(getattr(mdl, "elms", [])),
        "dof": 6 * nodes,
        "load_cases": int(getattr(mdl, "max_clc", 0) or 0),
        "mpcs": len(getattr(mdl, "mpcs", [])),
    }
    return store["kG"], store["lm"], stats


def _timed_splu(kG, permc_spec, timeout_s):
    """Factorize kG with permc_spec; return (lu, factor_s) or raise."""

    def _run():
        return _real_splu(kG, permc_spec=permc_spec)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        lu = future.result(timeout=timeout_s)
    return lu


def benchmark_spec(kG, lm, permc_spec, timeout_s):
    """Benchmark one permc_spec; never raises — returns a result dict."""

    orig_nnz = kG.nnz
    result = {
        "permc_spec": permc_spec,
        "status": "ok",
        "detail": "",
        "factor_s": None,
        "solve_s": None,
        "lu_nnz": None,
        "fill_ratio": None,
        "peak_rss": peak_rss_bytes(),
        "max_rel_diff": None,
        "x": None,
    }

    rss_before = peak_rss_bytes()
    try:
        t0 = time.perf_counter()
        lu = _timed_splu(kG, permc_spec, timeout_s)
        result["factor_s"] = time.perf_counter() - t0
    except concurrent.futures.TimeoutError:
        result["status"] = "TIMEOUT"
        result["detail"] = "exceeded {0:.0f}s".format(timeout_s)
        return result
    except MemoryError as ex:
        result["status"] = "MEMORY"
        result["detail"] = str(ex)
        return result
    except Exception as ex:
        result["status"] = "ERROR"
        result["detail"] = "{0}: {1}".format(type(ex).__name__, ex)
        return result

    result["lu_nnz"] = lu.L.nnz + lu.U.nnz
    result["fill_ratio"] = result["lu_nnz"] / float(orig_nnz) if orig_nnz else None
    result["peak_rss"] = peak_rss_bytes()

    try:
        t0 = time.perf_counter()
        x = lu.solve(lm)
        result["solve_s"] = time.perf_counter() - t0
        result["x"] = np.asarray(x, dtype=np.float64)
    except Exception as ex:
        result["status"] = "ERROR"
        result["detail"] = "solve: {0}: {1}".format(type(ex).__name__, ex)

    if rss_before and result["peak_rss"]:
        result["rss_delta"] = result["peak_rss"] - rss_before
    else:
        result["rss_delta"] = None

    return result


def run_model(dat_path, timeout_s, skip_natural):
    """Benchmark all permc_spec values for one model."""

    print()
    print("=" * 96)
    print("model: {0}".format(os.path.abspath(dat_path)))

    t0 = time.perf_counter()
    kG, lm, stats = capture_system(dat_path)
    capture_s = time.perf_counter() - t0

    print(
        "  nodes={0}  elements={1}  dof={2}  load_cases={3}  mpcs={4}".format(
            stats["nodes"], stats["elements"], stats["dof"],
            stats["load_cases"], stats["mpcs"],
        )
    )
    print(
        "  K: {0} x {1}, nnz={2:,}  (captured in {3:.2f}s)".format(
            kG.shape[0], kG.shape[1], kG.nnz, capture_s,
        )
    )
    print("-" * 96)

    specs = [s for s in PERMC_SPECS if not (skip_natural and s == "NATURAL")]
    results = []
    baseline_x = None

    for spec in specs:
        print("  benchmarking {0}...".format(spec), flush=True)
        row = benchmark_spec(kG, lm, spec, timeout_s)
        if spec == "COLAMD" and row["status"] == "ok" and row["x"] is not None:
            baseline_x = row["x"]
        results.append(row)

    if baseline_x is not None:
        for row in results:
            if row["status"] == "ok" and row["x"] is not None and row["permc_spec"] != "COLAMD":
                row["max_rel_diff"] = _max_rel_diff(row["x"], baseline_x)
            elif row["permc_spec"] == "COLAMD":
                row["max_rel_diff"] = 0.0

    # Strip solution vectors before returning (keep only diffs).
    for row in results:
        row.pop("x", None)

    return {"dat": dat_path, "stats": stats, "k_nnz": kG.nnz, "results": results}


def print_table(report):
    stats = report["stats"]
    print()
    print("=== {0} (dof={1}, K nnz={2:,}) ===".format(
        os.path.basename(report["dat"]), stats["dof"], report["k_nnz"],
    ))
    header = (
        "{0:<16s} {1:>8s} {2:>8s} {3:>12s} {4:>8s} {5:>12s} {6:>12s} {7:>10s}"
    ).format(
        "permc_spec", "factor", "solve", "LU nnz", "fill", "peak RSS", "RSS d", "rel diff",
    )
    print(header)
    print("-" * len(header))

    colamd_factor = None
    for row in report["results"]:
        if row["permc_spec"] == "COLAMD" and row["factor_s"] is not None:
            colamd_factor = row["factor_s"]
            break

    for row in report["results"]:
        if row["status"] != "ok":
            print("{0:<16s}  {1}: {2}".format(
                row["permc_spec"], row["status"], row["detail"],
            ))
            continue

        speedup = ""
        if colamd_factor and row["factor_s"]:
            ratio = colamd_factor / row["factor_s"]
            speedup = " ({0:.2f}x vs COLAMD)".format(ratio)

        rel = row["max_rel_diff"]
        rel_str = "{0:.2e}".format(rel) if rel is not None else "-"

        print("{0:<16s} {1:7.3f}s{2} {3:7.3f}s {4:12,} {5:7.2f}x {6:>12s} {7:>12s} {8:>10s}".format(
            row["permc_spec"],
            row["factor_s"],
            speedup,
            row["solve_s"],
            row["lu_nnz"],
            row["fill_ratio"],
            _fmt_bytes(row["peak_rss"]),
            _fmt_bytes(row.get("rss_delta")),
            rel_str,
        ))


def build_parser():
    p = argparse.ArgumentParser(
        description="Benchmark splu permc_spec orderings on a .dat model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--model", default=DEFAULT_MODEL,
        help="input .dat path (ignored when --all-models is set)",
    )
    p.add_argument(
        "--all-models", action="store_true",
        help="run all benchmark models (1000/4000/8000 nodes + UK_240416)",
    )
    p.add_argument(
        "--timeout", type=float, default=180.0,
        help="max seconds per factorization before skipping",
    )
    p.add_argument(
        "--skip-natural", action="store_true",
        help="skip the NATURAL ordering (often impractically slow)",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    models = ALL_MODELS if args.all_models else [args.model]

    reports = []
    for dat in models:
        if not os.path.isfile(dat):
            print("SKIP: {0} (file not found)".format(dat))
            continue
        reports.append(run_model(dat, args.timeout, args.skip_natural))

    print()
    print("=" * 96)
    print("SUMMARY")
    print("=" * 96)
    for report in reports:
        print_table(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
