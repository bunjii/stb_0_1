import os

from stb_viewer.model_json import (
    project_root,
    list_model_files,
    load_model_dict,
    resolve_model_path,
)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app(default_model=None):
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        raise ImportError(
            "Web viewer requires fastapi and uvicorn. "
            "Install with: pip install -e \".[viewer]\""
        )

    app = FastAPI(title="Structural Toolbox Viewer", version="0.1.0")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

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

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    return app


def run_server(host="127.0.0.1", port=8765, default_model=None, open_browser=True):
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "Web viewer requires uvicorn. Install with: pip install -e \".[viewer]\""
        )

    app = create_app(default_model=default_model)
    url = "http://{0}:{1}/".format(host, port)

    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    print("STB viewer: {0}".format(url))
    if default_model != None:
        print("  default model: {0}".format(default_model))
    print("  project root: {0}".format(project_root()))
    print("  Press Ctrl+C to stop.")

    uvicorn.run(app, host=host, port=port, log_level="info")
