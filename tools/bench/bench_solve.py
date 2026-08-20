"""Phase-by-phase timing and peak-memory harness for a single .dat analysis.

Instruments the model-build and solve pipelines by wrapping the relevant
methods, so no production code needs to change. Reports both inclusive time
(the method and everything it calls) and self time (excluding instrumented
callees), which is what identifies an actual hotspot.

Examples
--------
    python tools/bench/bench_solve.py .bench/frame_10k.dat
    python tools/bench/bench_solve.py model.dat --json out.json --cprofile p.prof
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def peak_rss_bytes():
    """Peak resident set size of this process, or None if unavailable."""

    if os.name == "nt":
        import ctypes
        import ctypes.wintypes

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
    # Linux reports KiB, macOS reports bytes.
    return int(maxrss) if sys.platform == "darwin" else int(maxrss) * 1024


class PhaseTimer:
    """Accumulates inclusive and self time for named, possibly nested spans."""

    def __init__(self):
        self.order = []
        self.calls = {}
        self.inclusive = {}
        self.self_time = {}
        self._child_time_stack = []

    @contextlib.contextmanager
    def measure(self, name):
        if name not in self.calls:
            self.order.append(name)
            self.calls[name] = 0
            self.inclusive[name] = 0.0
            self.self_time[name] = 0.0
        self._child_time_stack.append(0.0)
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            child = self._child_time_stack.pop()
            self.calls[name] += 1
            self.inclusive[name] += elapsed
            self.self_time[name] += elapsed - child
            if self._child_time_stack:
                self._child_time_stack[-1] += elapsed


class Instrumenter:
    """Temporarily replaces attributes with timing wrappers."""

    def __init__(self, timer):
        self.timer = timer
        self._originals = []

    def patch(self, owner, attr, label=None):
        original = getattr(owner, attr, None)
        if original is None:
            return False
        name = label or attr
        timer = self.timer

        def wrapper(*args, **kwargs):
            with timer.measure(name):
                return original(*args, **kwargs)

        wrapper.__name__ = getattr(original, "__name__", attr)
        setattr(owner, attr, wrapper)
        self._originals.append((owner, attr, original))
        return True

    def restore(self):
        for owner, attr, original in reversed(self._originals):
            setattr(owner, attr, original)
        self._originals = []


MDL_METHODS = [
    "AssignElemJoints",
    "CalcElemMatrices",
    "CreateCombinedLoads",
    "AssignCompIds",
    "FindNodeForCons",
    "FindNodeElmForLd",
    "FindElmsForAld",
    "BuildDiaphragmConnections",
    "SetBounds",
    "SetPlnToAxis",
]

SOLVE_METHODS = [
    "CreateGlobalStiffMX",
    "CreateLoadMx",
    "AddDiaphragmLoads",
    "InitConstrainedReactions",
    "BuildMPCTransformation",
    "ApplySupportConstraints",
    "CheckStability",
    "SetNodalDisps",
    "CalcElemForces",
    "EffectiveElemLocalWLoads",
    "CalcMembraneForces",
    "CalcReactions",
]


def install_instrumentation(timer):
    """Wrap the model-build and solve methods. Returns the Instrumenter."""

    import classes.solve as solve_mod
    from classes.solve import Solve
    from mdl import Mdl

    inst = Instrumenter(timer)
    for name in MDL_METHODS:
        inst.patch(Mdl, name, "Mdl." + name)
    for name in SOLVE_METHODS:
        inst.patch(Solve, name, "Solve." + name)
    inst.patch(solve_mod, "spsolve", "scipy.spsolve")
    inst.patch(solve_mod, "csc_matrix", "scipy.csc_matrix")
    return inst


def model_stats(mdl):
    nodes = len(getattr(mdl, "nds", []))
    dof = 6 * nodes
    return {
        "nodes": nodes,
        "elements": len(getattr(mdl, "elms", [])),
        "dof": dof,
        "load_cases": int(getattr(mdl, "max_clc", 0) or 0),
        "mpcs": len(getattr(mdl, "mpcs", [])),
        "dmems": len(getattr(mdl, "dmems", [])),
        "point_loads": len(getattr(mdl, "lds", [])),
        "element_loads": len(getattr(mdl, "elds", [])),
        "area_loads": len(getattr(mdl, "alds", [])),
        "constraints": len(getattr(mdl, "cons", [])),
        "dense_k_bytes": dof * dof * 8,
    }


def run(dat_path, do_format=True, profile_path=None):
    from stb_engine import format_results, parse_input, read_input_file, solve_model

    timer = PhaseTimer()
    inst = install_instrumentation(timer)

    profiler = None
    if profile_path:
        import cProfile

        profiler = cProfile.Profile()

    result = {
        "dat": os.path.abspath(dat_path),
        "dat_bytes": os.path.getsize(dat_path),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "ok": False,
        "error": None,
    }

    rss_before = peak_rss_bytes()
    wall_start = time.perf_counter()
    mdl = None
    try:
        if profiler:
            profiler.enable()
        with timer.measure("read_input_file"):
            lines = read_input_file(dat_path)
        with timer.measure("parse_input"):
            mdl = parse_input(lines)
            mdl.filepath = dat_path
        with timer.measure("solve_model"):
            solve_model(mdl)
        if do_format:
            with timer.measure("format_results"):
                text = format_results(mdl)
                result["out_chars"] = len(text)
        result["ok"] = True
    except Exception as ex:
        result["error"] = "{0}: {1}".format(type(ex).__name__, ex)
    finally:
        if profiler:
            profiler.disable()
        inst.restore()

    result["wall_seconds"] = time.perf_counter() - wall_start
    rss_after = peak_rss_bytes()
    result["peak_rss_bytes"] = rss_after
    result["rss_delta_bytes"] = (
        (rss_after - rss_before) if (rss_after and rss_before) else None
    )
    result["model"] = model_stats(mdl) if mdl is not None else None
    result["phases"] = [
        {
            "name": name,
            "calls": timer.calls[name],
            "inclusive_s": timer.inclusive[name],
            "self_s": timer.self_time[name],
        }
        for name in timer.order
    ]

    if profiler:
        profiler.dump_stats(profile_path)
        result["cprofile"] = os.path.abspath(profile_path)

    return result


def _fmt_bytes(n):
    if n is None:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0 or unit == "TB":
            return "{0:.1f} {1}".format(n, unit)
        n /= 1024.0


def print_report(result, top=None):
    model = result["model"]
    print("=" * 78)
    print("model : {0}".format(result["dat"]))
    if model:
        print(
            "        nodes={0}  elements={1}  dof={2}  load cases={3}  mpcs={4}".format(
                model["nodes"], model["elements"], model["dof"],
                model["load_cases"], model["mpcs"],
            )
        )
        print(
            "        dense K would be {0}  (.dat file {1})".format(
                _fmt_bytes(model["dense_k_bytes"]), _fmt_bytes(result["dat_bytes"])
            )
        )
    print(
        "status: {0}   wall={1:.3f}s   peak RSS={2}".format(
            "OK" if result["ok"] else "FAILED",
            result["wall_seconds"],
            _fmt_bytes(result["peak_rss_bytes"]),
        )
    )
    if result["error"]:
        print("error : {0}".format(result["error"]))
    print("-" * 78)
    print("{0:<34s} {1:>7s} {2:>11s} {3:>11s} {4:>7s}".format(
        "phase", "calls", "incl [s]", "self [s]", "self %"
    ))
    print("-" * 78)

    total_self = sum(p["self_s"] for p in result["phases"]) or 1.0
    rows = sorted(result["phases"], key=lambda p: -p["self_s"])
    if top:
        rows = rows[:top]
    for p in rows:
        print("{0:<34s} {1:>7d} {2:>11.3f} {3:>11.3f} {4:>6.1f}%".format(
            p["name"], p["calls"], p["inclusive_s"], p["self_s"],
            100.0 * p["self_s"] / total_self,
        ))
    print("-" * 78)
    print("{0:<34s} {1:>7s} {2:>11s} {3:>11.3f}".format("TOTAL (instrumented self)", "", "", total_self))
    if result.get("cprofile"):
        print("cProfile written to {0}".format(result["cprofile"]))


def print_cprofile_top(profile_path, count=25):
    import pstats

    stats = pstats.Stats(profile_path)
    print()
    print("=== cProfile: top {0} by cumulative time ===".format(count))
    stats.sort_stats("cumulative").print_stats(count)


def build_parser():
    p = argparse.ArgumentParser(
        description="Measure phase-by-phase time and peak memory for one .dat analysis.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("dat", help="input .dat path")
    p.add_argument("--json", dest="json_path", default=None,
                   help="also write the raw measurements as JSON")
    p.add_argument("--cprofile", dest="profile_path", default=None,
                   help="run under cProfile and dump stats to this path")
    p.add_argument("--show-cprofile", action="store_true",
                   help="print the cProfile top entries (requires --cprofile)")
    p.add_argument("--skip-format", dest="do_format", action="store_false",
                   help="skip the .out formatting phase")
    p.add_argument("--top", type=int, default=None, help="only show the N slowest phases")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    result = run(args.dat, do_format=args.do_format, profile_path=args.profile_path)
    print_report(result, top=args.top)

    if args.profile_path and args.show_cprofile:
        print_cprofile_top(args.profile_path)

    if args.json_path:
        out_dir = os.path.dirname(os.path.abspath(args.json_path))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print("JSON written to {0}".format(os.path.abspath(args.json_path)))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
