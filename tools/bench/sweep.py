"""Run the solve benchmark across a range of model sizes and summarise results.

Each size runs in its own subprocess so that a MemoryError, a crash or a
timeout at one size does not lose the results of the others, and so that peak
memory is measured per model rather than cumulatively.

Examples
--------
    python tools/bench/sweep.py --sizes 500 2000 8000 --scenario basic
    python tools/bench/sweep.py --sizes 2000 10000 50000 --scenario elod --timeout 900
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))

GEN_SCRIPT = os.path.join(_HERE, "gen_model.py")
BENCH_SCRIPT = os.path.join(_HERE, "bench_solve.py")

SCENARIOS = {
    "basic": [],
    "elod": ["--elod"],
    "alod": ["--area-loads"],
    "diaphragm": ["--diaphragms"],
    "full": ["--elod", "--area-loads", "--diaphragms"],
}

DEFAULT_SIZES = [250, 1000, 4000, 16000]


def _fmt_bytes(n):
    if not n:
        return "-"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0 or unit == "TB":
            return "{0:.1f}{1}".format(value, unit)
        value /= 1024.0


def generate(target_nodes, scenario, outdir):
    dat = os.path.join(outdir, "frame_{0}_{1}.dat".format(scenario, target_nodes))
    cmd = [
        sys.executable, GEN_SCRIPT,
        "--target-nodes", str(target_nodes),
        "-o", dat, "-q",
    ] + SCENARIOS[scenario]
    subprocess.run(cmd, cwd=_REPO_ROOT, check=True)
    return dat


def measure(dat, outdir, timeout, skip_format):
    json_path = os.path.splitext(dat)[0] + ".json"
    cmd = [sys.executable, BENCH_SCRIPT, dat, "--json", json_path]
    if skip_format:
        cmd.append("--skip-format")
    try:
        proc = subprocess.run(
            cmd, cwd=_REPO_ROOT, timeout=timeout,
            capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "detail": "exceeded {0}s".format(timeout)}

    if os.path.isfile(json_path):
        with open(json_path, "r", encoding="utf-8") as fh:
            result = json.load(fh)
        result["status"] = "ok" if result.get("ok") else "ERROR"
        result["detail"] = result.get("error") or ""
        return result

    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    return {
        "status": "CRASH",
        "detail": detail[-1] if detail else "exit code {0}".format(proc.returncode),
    }


def top_phases(result, count=3):
    phases = result.get("phases") or []
    ranked = sorted(phases, key=lambda p: -p["self_s"])[:count]
    return ", ".join(
        "{0} {1:.2f}s".format(p["name"].replace("Solve.", "").replace("Mdl.", ""), p["self_s"])
        for p in ranked if p["self_s"] > 0.0005
    )


def print_table(rows):
    header = "{0:>8s} {1:>9s} {2:>9s} {3:>4s} {4:>9s} {5:>9s} {6:>8s}  {7}".format(
        "nodes", "elements", "dof", "lcs", "wall[s]", "peakRSS", "status", "top self-time phases"
    )
    print()
    print(header)
    print("-" * max(len(header), 100))
    for row in rows:
        model = row.get("model") or {}
        print("{0:>8s} {1:>9s} {2:>9s} {3:>4s} {4:>9s} {5:>9s} {6:>8s}  {7}".format(
            str(model.get("nodes", "-")),
            str(model.get("elements", "-")),
            str(model.get("dof", "-")),
            str(model.get("load_cases", "-")),
            "{0:.2f}".format(row["wall_seconds"]) if row.get("wall_seconds") else "-",
            _fmt_bytes(row.get("peak_rss_bytes")),
            row.get("status", "?"),
            top_phases(row) or row.get("detail", ""),
        ))
    print("-" * max(len(header), 100))


def build_parser():
    p = argparse.ArgumentParser(
        description="Sweep the solve benchmark over several model sizes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES,
                   help="target node counts to generate and measure")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), default="basic",
                   help="which load patterns to include")
    p.add_argument("--outdir", default=os.path.join(_REPO_ROOT, ".bench"),
                   help="directory for generated models and results")
    p.add_argument("--timeout", type=float, default=600.0,
                   help="per-model timeout in seconds")
    p.add_argument("--skip-format", action="store_true",
                   help="skip the .out formatting phase in each run")
    p.add_argument("--summary-json", default=None,
                   help="write the combined results to this path")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)

    rows = []
    for size in sorted(args.sizes):
        dat = generate(size, args.scenario, args.outdir)
        print("running {0} ...".format(os.path.basename(dat)), flush=True)
        row = measure(dat, args.outdir, args.timeout, args.skip_format)
        row["target_nodes"] = size
        row["scenario"] = args.scenario
        rows.append(row)
        print("  -> {0} {1}".format(
            row.get("status"),
            "{0:.2f}s".format(row["wall_seconds"]) if row.get("wall_seconds") else row.get("detail", ""),
        ), flush=True)

    print_table(rows)

    if args.summary_json:
        with open(args.summary_json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2)
        print("summary written to {0}".format(os.path.abspath(args.summary_json)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
