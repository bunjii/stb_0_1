import sys

from stb_viewer.server import run_server


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="stb-viewer",
        description="Structural Toolbox web viewer (Three.js)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port (default: 8765)",
    )
    parser.add_argument(
        "--file", default="examples/cantilever.dat",
        help="Default model path under project root",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Do not open a browser window",
    )
    args = parser.parse_args()

    try:
        run_server(
            host=args.host,
            port=args.port,
            default_model=args.file,
            open_browser=(not args.no_browser),
        )
    except ImportError as ex:
        sys.stderr.write(str(ex) + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
