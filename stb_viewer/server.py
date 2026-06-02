import os
from urllib.parse import quote

from stb_viewer.model_json import (
    project_root,
    list_model_files,
    load_model_dict,
    load_input_text,
    load_results_text,
    normalize_model_relpath,
    resolve_model_path,
)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app(default_model=None):
    default_model = normalize_model_relpath(default_model)
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse, JSONResponse
    except ImportError:
        raise ImportError(
            "Web viewer requires fastapi and uvicorn. "
            "Install with: pip install -e \".[viewer]\""
        )

    app = FastAPI(title="Structural Toolbox Viewer", version="0.1.0")

    @app.get("/")
    def index():
        return FileResponse(
            os.path.join(_STATIC_DIR, "index.html"),
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )

    @app.get("/static/{asset_path:path}")
    def static_asset(asset_path: str):
        full = os.path.normpath(os.path.join(_STATIC_DIR, asset_path))
        static_root = os.path.realpath(_STATIC_DIR)
        if not os.path.realpath(full).startswith(static_root + os.sep):
            raise HTTPException(status_code=404, detail="Not found")
        if not os.path.isfile(full):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(
            full,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )

    @app.get("/api/models")
    def api_models():
        models = list_model_files()
        return JSONResponse({"models": models, "default": default_model})

    @app.get("/api/model")
    def api_model(
        path: str = Query(..., description="Relative path under project root"),
        solve: int = Query(0, description="1 to run analysis and include displacements"),
    ):
        try:
            resolve_model_path(path)
            data = load_model_dict(path, solve=(solve == 1), quiet=True)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return JSONResponse(data)

    @app.get("/api/results")
    def api_results(
        path: str = Query(..., description="Relative path under project root"),
    ):
        try:
            resolve_model_path(path)
            txt = load_results_text(path, quiet=True)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(txt, media_type="text/plain; charset=utf-8")

    @app.get("/api/input")
    def api_input(
        path: str = Query(..., description="Relative path under project root"),
    ):
        try:
            resolve_model_path(path)
            txt = load_input_text(path)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(txt, media_type="text/plain; charset=utf-8")

    return app


def viewer_open_url(host, port, default_model=None):
    """URL opened in the browser; ?file= selects the CLI model on first load."""

    default_model = normalize_model_relpath(default_model)
    url = "http://{0}:{1}/".format(host, port)
    if default_model:
        url += "?file=" + quote(default_model, safe="/")
    return url


def run_server(host="127.0.0.1", port=8765, default_model=None, open_browser=True):
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "Web viewer requires uvicorn. Install with: pip install -e \".[viewer]\""
        )

    app = create_app(default_model=default_model)
    url = viewer_open_url(host, port, default_model)

    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    print("STB viewer: {0}".format(url.split("?")[0]))
    if default_model != None:
        print("  default model: {0}".format(default_model))
    print("  project root: {0}".format(project_root()))
    print("  Press Ctrl+C to stop.")

    uvicorn.run(app, host=host, port=port, log_level="info")
