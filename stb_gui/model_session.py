"""In-process caches for parsed models and project metadata (GUI server)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from stb_gui.model_json import normalize_model_relpath, project_root, resolve_model_path
from stb_project import load_project_for_dat, project_path_for_dat

_PARSE_CACHE: Dict[str, Tuple[float, Any]] = {}
_PROJECT_CACHE: Dict[str, Tuple[float, float, Any]] = {}


def invalidate_model_session(full: str) -> None:
    """Drop cached parse/project entries after .dat or project.json changes."""
    _PARSE_CACHE.pop(full, None)
    _PROJECT_CACHE.pop(full, None)


def get_parsed_model(full: str):
    """Return a parsed Mdl for an absolute .dat path (mtime-cached)."""
    dat_mtime = os.path.getmtime(full)
    cached = _PARSE_CACHE.get(full)
    if cached and cached[0] == dat_mtime:
        return cached[1]

    from stb_engine import parse_input

    with open(full, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    mdl = parse_input(lines)
    mdl.filepath = full
    _PARSE_CACHE[full] = (dat_mtime, mdl)
    return mdl


def get_model_and_project(
    dat_relpath: str,
    mdl=None,
    project=None,
) -> Tuple[str, str, Any, Any]:
    """Resolve paths and return (relpath, full, mdl, project) with caching."""
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    if mdl is not None and project is not None:
        return dat_relpath, full, mdl, project

    proj_path = project_path_for_dat(full)
    dat_mtime = os.path.getmtime(full)
    proj_mtime = os.path.getmtime(proj_path) if os.path.isfile(proj_path) else 0.0

    proj_cached = _PROJECT_CACHE.get(full)
    if proj_cached and proj_cached[0] == dat_mtime and proj_cached[1] == proj_mtime:
        return dat_relpath, full, proj_cached[2], proj_cached[3]

    mdl = get_parsed_model(full)
    project = load_project_for_dat(full, required=True)
    _PROJECT_CACHE[full] = (dat_mtime, proj_mtime, mdl, project)
    return dat_relpath, full, mdl, project
