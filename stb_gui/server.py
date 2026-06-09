import os
import signal
import socket
import threading

from stb_gui.dat_edit import apply_edit_action, validate_dat_text, ejnt_lines_for_elements
from stb_gui.input_format import EJNT_EDITOR_HEADER
from stb_gui.model_json import (
    project_root,
    list_model_files,
    load_model_dict,
    load_input_text,
    load_results_text,
    normalize_model_relpath,
    resolve_model_path,
    create_new_model_file,
    open_uploaded_model,
)

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app(default_model=None):
    default_model = normalize_model_relpath(default_model)
    try:
        from fastapi import FastAPI, HTTPException, Query, Body
        from fastapi.responses import FileResponse, JSONResponse
    except ImportError:
        raise ImportError(
            "Structural Toolbox GUI requires fastapi and uvicorn. "
            "Install with: pip install -e \".[gui]\""
        )

    app = FastAPI(title="Structural Toolbox", version="0.1.0")

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

    @app.put("/api/input")
    def api_input_save(
        path: str = Query(..., description="Relative path under project root"),
        text: str = Body(..., embed=True, description="Input file content"),
    ):
        try:
            full = resolve_model_path(path)
            with open(full, "w", encoding="utf-8") as f:
                f.write(text)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({"ok": True, "path": normalize_model_relpath(path)})

    @app.post("/api/model/edit")
    def api_model_edit(
        path: str = Query(..., description="Relative path under project root"),
        body: dict = Body(..., description="Edit action payload"),
    ):
        try:
            full = resolve_model_path(path)
            text = load_input_text(path)
            new_text, warnings = apply_edit_action(text, body)
            validate_dat_text(new_text)
            with open(full, "w", encoding="utf-8") as f:
                f.write(new_text)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({
            "ok": True,
            "path": normalize_model_relpath(path),
            "warnings": warnings,
            "element_ids": body.get("element_ids") or [],
            "action": body.get("action"),
        })

    @app.get("/api/model/ejnt-lines")
    def api_model_ejnt_lines(
        path: str = Query(..., description="Relative path under project root"),
        element_ids: str = Query(..., description="Comma-separated element ids"),
    ):
        try:
            resolve_model_path(path)
            ids = [int(x.strip()) for x in element_ids.split(",") if x.strip()]
            text = load_input_text(path)
            rows = ejnt_lines_for_elements(text, ids)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return JSONResponse({
            "path": normalize_model_relpath(path),
            "header": EJNT_EDITOR_HEADER,
            "lines": rows,
        })

    @app.post("/api/model/new")
    def api_model_new():
        try:
            rel, text = create_new_model_file()
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({"ok": True, "path": rel, "text": text})

    @app.post("/api/model/open")
    def api_model_open(body: dict = Body(...)):
        text = body.get("text")
        if text is None:
            raise HTTPException(status_code=400, detail="text is required")
        filename = body.get("filename") or body.get("path") or "model.dat"
        try:
            rel = open_uploaded_model(filename, text)
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        except OSError as ex:
            raise HTTPException(status_code=500, detail=str(ex))
        return JSONResponse({"ok": True, "path": rel})

    @app.post("/api/shutdown")
    def api_shutdown():
        def _stop_server():
            os.kill(os.getpid(), signal.SIGINT)

        threading.Timer(0.3, _stop_server).start()
        return JSONResponse({"ok": True})

    return app


def gui_open_url(host, port):
    return "http://{0}:{1}/".format(host, port)


def _port_is_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def run_server(
    host="127.0.0.1",
    port=8765,
    default_model=None,
    open_browser=True,
    log_file=None,
):
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "Structural Toolbox GUI requires uvicorn. "
            "Install with: pip install -e \".[gui]\""
        )

    app = create_app(default_model=default_model)
    url = gui_open_url(host, port)

    if _port_is_open(host, port):
        print("Structural Toolbox: already running at {0}".format(url))
        print("  project root: {0}".format(project_root()))
        print("  Logs are in the other console window (do not close it while debugging).")
        print("  Or end the old server: close that window, or stop python.exe in Task Manager.")
        if open_browser:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass
        return "already_running"

    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    print("Structural Toolbox: {0}".format(url))
    print("  project root: {0}".format(project_root()))
    print("  Close this window to stop the server.")
    if log_file:
        print("  Log file: {0}".format(os.path.abspath(log_file)))

    log_config = None
    if log_file:
        log_path = os.path.abspath(log_file)
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": log_path,
                    "encoding": "utf-8",
                    "formatter": "default",
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["file", "console"], "level": "INFO"},
                "uvicorn.error": {"handlers": ["file", "console"], "level": "INFO"},
                "uvicorn.access": {"handlers": ["file", "console"], "level": "INFO"},
            },
        }

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        log_config=log_config,
    )
    return "stopped"
