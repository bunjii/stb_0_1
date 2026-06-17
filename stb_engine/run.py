import os
import sys

# Resolve core modules (classes/) without wx, vedo, or VTK.
_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLASSES_DIR = os.path.join(_STB_ROOT, "classes")
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from classes.io import ReadLines, RegisterResultData
from classes.solve import Solve

from stb_engine.errors import StbParseError, StbSolveError


def read_input_file(path):
    """Read an input file and return a list of text lines."""

    f = open(path, "r", encoding="utf-8")
    lines = f.read().splitlines()
    f.close()
    return lines


def parse_input(lines):
    """Parse input lines and build a model."""

    try:
        mdl = ReadLines(lines)
    except Exception as ex:
        raise StbParseError(str(ex))

    return mdl


def solve_model(mdl):
    """Run static analysis on the model (in-place)."""

    try:
        Solve(mdl)
    except Exception as ex:
        raise StbSolveError(str(ex))

    return mdl


def format_results(mdl):
    """Format analysis results as text (same layout as the GUI output pane)."""

    return RegisterResultData(mdl)


def run_from_lines(lines, filepath=None):
    """Parse, solve, and format results from a list of input lines."""

    mdl = parse_input(lines)

    if filepath != None:
        mdl.filepath = filepath

    solve_model(mdl)
    txt = format_results(mdl)

    return mdl, txt


def run_from_file(input_path, output_path=None):
    """Read an input file, run analysis, optionally write the result file."""

    lines = read_input_file(input_path)
    mdl, txt = run_from_lines(lines, filepath=input_path)

    if output_path != None:
        f = open(output_path, "w")
        f.write(txt)
        f.close()

    return mdl, txt
