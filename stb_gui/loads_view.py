"""Structured load / external-force verification payloads for the GUI."""

from __future__ import annotations

import os
from typing import Any, Dict

from stb_loads import (
    compute_seismic_distribution,
    compute_wind_distribution,
    generate_dlod_records,
    generate_wind_dlod_records,
)
from stb_loads.format import build_seismic_report_view
from stb_loads.wind_format import build_wind_report_view
from stb_gui.model_json import normalize_model_relpath, project_root, resolve_model_path
from stb_project import load_project_for_dat, project_path_for_dat


LOAD_VERIFY_TABS = (
    {"id": "seismic", "label": "地震", "enabled": True},
    {"id": "dead", "label": "固定荷重", "enabled": False},
    {"id": "live", "label": "積載荷重", "enabled": False},
    {"id": "snow", "label": "雪荷重", "enabled": False},
    {"id": "wind", "label": "風荷重", "enabled": True},
)


def _load_model_and_project(dat_relpath: str, mdl=None, project=None):
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    if project is None:
        project = load_project_for_dat(full, required=True)
    if mdl is None:
        from stb_engine import parse_input

        with open(full, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        mdl = parse_input(lines)
        mdl.filepath = full
    return dat_relpath, full, mdl, project


def build_seismic_loads_view(mdl, project, dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    project_rel = os.path.relpath(project_path_for_dat(full), project_root()).replace("\\", "/")

    result = compute_seismic_distribution(mdl, project)
    dloads = generate_dlod_records(result)
    report = build_seismic_report_view(result, project, mdl=mdl)

    return {
        "kind": "seismic",
        "found": True,
        "dat_path": dat_relpath,
        "project_path": project_rel,
        "title": "荷重・外力確認 — 地震力",
        "tabs": list(LOAD_VERIFY_TABS),
        "active_tab": "seismic",
        "summary": report["summary"],
        "raw_weight_rows": report["raw_weight_rows"],
        "mass_level_rows": report["mass_level_rows"],
        "diaphragm_rows": report["diaphragm_rows"],
        "alpha_i_note": report["alpha_i_note"],
        "wi_above_note": report.get("wi_above_note") or "",
        "report_notice": report["report_notice"],
        "dlod_section_title": report["dlod_section_title"],
        "dlod_section_note": report["dlod_section_note"],
        "qi_fi_rules_text": report["qi_fi_rules_text"],
        "equilibrium_rows": report.get("equilibrium_rows") or [],
        "checks": report.get("checks") or [],
        "warnings": list(result.warnings),
        "dlod_record_count": len(dloads),
        "can_apply_dlod": len(dloads) > 0,
    }


def build_wind_loads_view(mdl, project, dat_relpath: str) -> Dict[str, Any]:
    dat_relpath = normalize_model_relpath(dat_relpath)
    full = resolve_model_path(dat_relpath)
    project_rel = os.path.relpath(project_path_for_dat(full), project_root()).replace("\\", "/")

    result = compute_wind_distribution(mdl, project)
    dloads = generate_wind_dlod_records(result)
    report = build_wind_report_view(result, project, mdl=mdl)

    return {
        "kind": "wind",
        "found": bool(result.cases),
        "dat_path": dat_relpath,
        "project_path": project_rel,
        "title": "荷重・外力確認 — 風荷重",
        "tabs": list(LOAD_VERIFY_TABS),
        "active_tab": "wind",
        "summary": report["summary"],
        "surface_rows": report["surface_rows"],
        "story_force_rows": report["story_force_rows"],
        "diaphragm_rows": report["diaphragm_rows"],
        "uniform_input_note": report["uniform_input_note"],
        "report_notice": report["report_notice"],
        "dlod_section_title": report["dlod_section_title"],
        "visual": report["visual"],
        "equilibrium_rows": report.get("equilibrium_rows") or [],
        "checks": report.get("checks") or [],
        "warnings": list(result.warnings),
        "dlod_record_count": len(dloads),
        "can_apply_dlod": len(dloads) > 0,
    }


def load_seismic_view_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, _full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)
    return build_seismic_loads_view(mdl, project, dat_relpath)


def load_wind_view_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, _full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)
    return build_wind_loads_view(mdl, project, dat_relpath)


def apply_seismic_dlod_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)

    result = compute_seismic_distribution(mdl, project)
    dloads = generate_dlod_records(result)
    from stb_loads import apply_seismic_to_dat

    apply_seismic_to_dat(full, dloads)
    view = build_seismic_loads_view(mdl, project, dat_relpath)
    view["applied"] = True
    view["dlod_record_count"] = len(dloads)
    return view


def apply_wind_dlod_for_model(dat_relpath: str, mdl=None, project=None) -> Dict[str, Any]:
    dat_relpath, full, mdl, project = _load_model_and_project(dat_relpath, mdl, project)

    result = compute_wind_distribution(mdl, project)
    dloads = generate_wind_dlod_records(result)
    from stb_loads import apply_wind_to_dat

    apply_wind_to_dat(full, dloads)
    view = build_wind_loads_view(mdl, project, dat_relpath)
    view["applied"] = True
    view["dlod_record_count"] = len(dloads)
    return view
