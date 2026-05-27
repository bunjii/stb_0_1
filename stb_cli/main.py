import argparse
import os
import sys

_STB_VERSION = "0.1.0"

# Exit codes for scripts and Grasshopper wrappers.
EXIT_OK = 0
EXIT_INPUT = 1
EXIT_SOLVE = 2


def _ensure_project_root_on_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


def _stderr(msg):
    sys.stderr.write(msg)
    if not msg.endswith("\n"):
        sys.stderr.write("\n")


def _read_lines(path):
    if not os.path.isfile(path):
        raise IOError("Input file not found: " + path)

    f = open(path, "r")
    lines = f.read().splitlines()
    f.close()
    return lines


def _solve_with_stdout_control(mdl, quiet):
    from stb_engine import solve_model

    if quiet:
        old_stdout = sys.stdout
        devnull = open(os.devnull, "w")
        sys.stdout = devnull
        try:
            solve_model(mdl)
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
    else:
        solve_model(mdl)


def cmd_version(args):
    print("stb " + _STB_VERSION)
    return EXIT_OK


def cmd_validate(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input
    from stb_engine.errors import StbParseError

    try:
        lines = _read_lines(args.input)
        mdl = parse_input(lines)
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT

    if args.verbose:
        print("Input OK: " + args.input)
        print("  nodes:      " + str(len(mdl.nds)))
        print("  elements:   " + str(len(mdl.elms)))
        print("  materials:  " + str(len(mdl.mats)))
        print("  sections:   " + str(len(mdl.secs)))
        print("  load cases: " + str(mdl.lcs))

    return EXIT_OK


def cmd_solve(args):
    _ensure_project_root_on_path()
    from stb_engine import parse_input, format_results
    from stb_engine.errors import StbParseError, StbSolveError

    try:
        lines = _read_lines(args.input)
        mdl = parse_input(lines)
        mdl.filepath = os.path.abspath(args.input)
    except IOError as ex:
        _stderr(str(ex))
        return EXIT_INPUT
    except StbParseError as ex:
        _stderr("Parse error: " + str(ex))
        return EXIT_INPUT

    try:
        _solve_with_stdout_control(mdl, args.quiet)
        txt = format_results(mdl)
    except StbSolveError as ex:
        _stderr("Analysis error: " + str(ex))
        return EXIT_SOLVE

    if args.verbose:
        print("Solved: " + args.input)
        print("  load cases: " + str(mdl.lcs))
        print("  analysis:   " + str(mdl.date_analysis))

    if args.output != None:
        out_path = args.output
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if out_dir != "" and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        f = open(out_path, "w")
        f.write(txt)
        f.close()
        if args.verbose:
            print("  written:    " + out_path)
    else:
        sys.stdout.write(txt)

    return EXIT_OK


def cmd_view(args):
    _ensure_project_root_on_path()
    try:
        from stb_viewer.server import run_server
    except ImportError as ex:
        _stderr(str(ex))
        _stderr("Install viewer extras: pip install -e \".[viewer]\"")
        return EXIT_INPUT

    try:
        run_server(
            host=args.host,
            port=args.port,
            default_model=args.file,
            open_browser=(not args.no_browser),
        )
    except KeyboardInterrupt:
        pass
    return EXIT_OK


def _build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress solver progress messages",
    )
    common.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print extra status messages",
    )

    parser = argparse.ArgumentParser(
        prog="stb",
        description="Structural Toolbox - headless static analysis",
    )

    sub = parser.add_subparsers(dest="command")

    p_ver = sub.add_parser("version", parents=[common], help="Show version")
    p_ver.set_defaults(func=cmd_version)

    p_val = sub.add_parser(
        "validate",
        parents=[common],
        help="Parse input only (no analysis)",
    )
    p_val.add_argument("input", help="Input model file (.dat, .stb, ...)")
    p_val.set_defaults(func=cmd_validate)

    p_sol = sub.add_parser(
        "solve",
        parents=[common],
        help="Run static analysis",
    )
    p_sol.add_argument("input", help="Input model file")
    p_sol.add_argument(
        "-o", "--output",
        help="Output results file (default: stdout)",
    )
    p_sol.set_defaults(func=cmd_solve)

    p_view = sub.add_parser(
        "view",
        parents=[common],
        help="Start web 3D viewer (Three.js)",
    )
    p_view.add_argument(
        "--host", default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    p_view.add_argument(
        "--port", type=int, default=8765,
        help="Port (default: 8765)",
    )
    p_view.add_argument(
        "--file", default="examples/cantilever.dat",
        help="Default model under project root",
    )
    p_view.add_argument(
        "--no-browser", action="store_true",
        help="Do not open a browser",
    )
    p_view.set_defaults(func=cmd_view)

    return parser


def main(argv=None):
    if argv == None:
        argv = sys.argv[1:]

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == None:
        parser.print_help()
        return EXIT_INPUT

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
