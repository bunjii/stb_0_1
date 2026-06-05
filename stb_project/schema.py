import json
import os
from dataclasses import dataclass, field
from typing import Optional, Tuple


SCHEMA_VERSION = 1
DEFAULT_PROJECT_SUFFIX = ".project.json"

ALLOWED_GRID_DIRECTIONS = ("x", "y")
ALLOWED_MEMBER_KINDS = (
    "beam",
    "column",
    "brace",
    "foundation_beam",
    "panel",
    "support",
    "lateral_resisting_element",
    "other",
)
ALLOWED_REPORT_MODES = ("practice", "education", "debug")
ALLOWED_REPORT_FORMATS = ("markdown", "html", "pdf")


PROJECT_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://structural-toolbox.local/schema/project-1.json",
    "title": "Structural Toolbox project sidecar",
    "type": "object",
    "required": ["schema", "model", "building", "grids", "stories", "member_classes", "report"],
    "additionalProperties": False,
    "properties": {
        "schema": {"const": SCHEMA_VERSION},
        "model": {
            "type": "object",
            "required": ["dat"],
            "additionalProperties": False,
            "properties": {
                "dat": {
                    "type": "string",
                    "description": "Path to the analysis .dat file, relative to this project JSON.",
                },
            },
        },
        "building": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
                "use": {"type": "string"},
                "structure": {"type": "string"},
                "calculation_route": {"type": "string"},
                "designer": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "qualification": {"type": "string"},
                        "license_number": {"type": "string"},
                        "contact": {"type": "string"},
                    },
                },
            },
        },
        "grids": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "direction", "coordinate"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "direction": {"enum": list(ALLOWED_GRID_DIRECTIONS)},
                    "coordinate": {"type": "number"},
                },
            },
        },
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "elevation", "height"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "elevation": {"type": "number"},
                    "height": {"type": "number"},
                },
            },
        },
        "member_classes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "kind", "element_ids"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"enum": list(ALLOWED_MEMBER_KINDS)},
                    "element_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "story": {"type": "string"},
                    "use": {"type": "string"},
                    "notes": {"type": "string"},
                },
            },
        },
        "design_checks": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "wood": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "load_cases": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "deflection_limit_ratio": {"type": "number"},
                        "allowable_stresses": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "bending": {"type": "number"},
                                "shear": {"type": "number"},
                                "compression": {"type": "number"},
                                "tension": {"type": "number"},
                            },
                        },
                    },
                },
            },
        },
        "report": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "mode": {"enum": list(ALLOWED_REPORT_MODES)},
                "language": {"type": "string"},
                "format": {"enum": list(ALLOWED_REPORT_FORMATS)},
                "include_manual_items": {"type": "boolean"},
                "include_warnings": {"type": "boolean"},
            },
        },
    },
}


class ProjectSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class DesignerInfo:
    name: str = ""
    qualification: str = ""
    license_number: str = ""
    contact: str = ""


@dataclass(frozen=True)
class BuildingInfo:
    name: str = ""
    location: str = ""
    use: str = ""
    structure: str = ""
    calculation_route: str = ""
    designer: DesignerInfo = DesignerInfo()


@dataclass(frozen=True)
class GridLine:
    name: str
    direction: str
    coordinate: float


@dataclass(frozen=True)
class Story:
    name: str
    elevation: float
    height: float


@dataclass(frozen=True)
class MemberClass:
    name: str
    kind: str
    element_ids: Tuple[int, ...]
    story: str = ""
    use: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ReportSettings:
    title: str = ""
    mode: str = "practice"
    language: str = "ja"
    format: str = "markdown"
    include_manual_items: bool = True
    include_warnings: bool = True


@dataclass(frozen=True)
class WoodAllowableStresses:
    bending: float = 0.0
    shear: float = 0.0
    compression: float = 0.0
    tension: float = 0.0


@dataclass(frozen=True)
class WoodCheckSettings:
    enabled: bool = False
    load_cases: Tuple[int, ...] = ()
    deflection_limit_ratio: float = 0.0
    allowable_stresses: WoodAllowableStresses = field(default_factory=WoodAllowableStresses)


@dataclass(frozen=True)
class DesignCheckSettings:
    wood: WoodCheckSettings = field(default_factory=WoodCheckSettings)


@dataclass(frozen=True)
class ProjectDefinition:
    schema: int
    dat_path: str
    building: BuildingInfo
    grids: Tuple[GridLine, ...]
    stories: Tuple[Story, ...]
    member_classes: Tuple[MemberClass, ...]
    design_checks: DesignCheckSettings
    report: ReportSettings
    source_path: Optional[str] = None

    def to_dict(self):
        return {
            "schema": self.schema,
            "model": {"dat": self.dat_path},
            "building": {
                "name": self.building.name,
                "location": self.building.location,
                "use": self.building.use,
                "structure": self.building.structure,
                "calculation_route": self.building.calculation_route,
                "designer": {
                    "name": self.building.designer.name,
                    "qualification": self.building.designer.qualification,
                    "license_number": self.building.designer.license_number,
                    "contact": self.building.designer.contact,
                },
            },
            "grids": [
                {"name": g.name, "direction": g.direction, "coordinate": g.coordinate}
                for g in self.grids
            ],
            "stories": [
                {"name": s.name, "elevation": s.elevation, "height": s.height}
                for s in self.stories
            ],
            "member_classes": [
                {
                    "name": c.name,
                    "kind": c.kind,
                    "element_ids": list(c.element_ids),
                    "story": c.story,
                    "use": c.use,
                    "notes": c.notes,
                }
                for c in self.member_classes
            ],
            "design_checks": {
                "wood": {
                    "enabled": self.design_checks.wood.enabled,
                    "load_cases": list(self.design_checks.wood.load_cases),
                    "deflection_limit_ratio": self.design_checks.wood.deflection_limit_ratio,
                    "allowable_stresses": {
                        "bending": self.design_checks.wood.allowable_stresses.bending,
                        "shear": self.design_checks.wood.allowable_stresses.shear,
                        "compression": self.design_checks.wood.allowable_stresses.compression,
                        "tension": self.design_checks.wood.allowable_stresses.tension,
                    },
                },
            },
            "report": {
                "title": self.report.title,
                "mode": self.report.mode,
                "language": self.report.language,
                "format": self.report.format,
                "include_manual_items": self.report.include_manual_items,
                "include_warnings": self.report.include_warnings,
            },
        }


def project_path_for_dat(dat_path):
    """Return the default sidecar path for an existing analysis file."""

    base, _ext = os.path.splitext(dat_path)
    return base + DEFAULT_PROJECT_SUFFIX


def load_project_for_dat(dat_path, required=False):
    """Load the sidecar project JSON next to a .dat file.

    This deliberately does not read or parse the .dat file; the sidecar is an
    optional layer above the existing analysis format.
    """

    project_path = project_path_for_dat(dat_path)
    if not os.path.isfile(project_path):
        if required:
            raise IOError("Project file not found: " + project_path)
        return None
    return load_project_file(project_path)


def load_project_file(path):
    f = open(path, "r", encoding="utf-8")
    try:
        raw = json.load(f)
    finally:
        f.close()
    return validate_project_dict(raw, source_path=path)


def validate_project_dict(raw, source_path=None):
    _require_type(raw, dict, "project")
    _reject_unknown(
        raw,
        ["schema", "model", "building", "grids", "stories", "member_classes", "design_checks", "report"],
        "project",
    )

    schema = _required(raw, "schema", "project")
    if schema != SCHEMA_VERSION:
        raise ProjectSchemaError("project.schema must be " + str(SCHEMA_VERSION))

    model = _required(raw, "model", "project")
    _require_type(model, dict, "project.model")
    _reject_unknown(model, ["dat"], "project.model")
    dat_path = _required_string(model, "dat", "project.model")

    building = _parse_building(_required(raw, "building", "project"))
    grids = tuple(_parse_grid_lines(_required(raw, "grids", "project")))
    stories = tuple(_parse_stories(_required(raw, "stories", "project")))
    member_classes = tuple(_parse_member_classes(_required(raw, "member_classes", "project")))
    design_checks = _parse_design_checks(raw.get("design_checks", {}))
    report = _parse_report(_required(raw, "report", "project"))

    return ProjectDefinition(
        schema=schema,
        dat_path=dat_path,
        building=building,
        grids=grids,
        stories=stories,
        member_classes=member_classes,
        design_checks=design_checks,
        report=report,
        source_path=source_path,
    )


def _parse_building(raw):
    _require_type(raw, dict, "project.building")
    _reject_unknown(
        raw,
        ["name", "location", "use", "structure", "calculation_route", "designer"],
        "project.building",
    )
    designer_raw = raw.get("designer", {})
    _require_type(designer_raw, dict, "project.building.designer")
    _reject_unknown(
        designer_raw,
        ["name", "qualification", "license_number", "contact"],
        "project.building.designer",
    )

    designer = DesignerInfo(
        name=_optional_string(designer_raw, "name", "project.building.designer"),
        qualification=_optional_string(designer_raw, "qualification", "project.building.designer"),
        license_number=_optional_string(designer_raw, "license_number", "project.building.designer"),
        contact=_optional_string(designer_raw, "contact", "project.building.designer"),
    )
    return BuildingInfo(
        name=_optional_string(raw, "name", "project.building"),
        location=_optional_string(raw, "location", "project.building"),
        use=_optional_string(raw, "use", "project.building"),
        structure=_optional_string(raw, "structure", "project.building"),
        calculation_route=_optional_string(raw, "calculation_route", "project.building"),
        designer=designer,
    )


def _parse_grid_lines(raw):
    _require_type(raw, list, "project.grids")
    seen = set()
    grids = []
    for idx, item in enumerate(raw):
        path = "project.grids[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "direction", "coordinate"], path)
        name = _required_string(item, "name", path)
        direction = _required_string(item, "direction", path).lower()
        if direction not in ALLOWED_GRID_DIRECTIONS:
            raise ProjectSchemaError(path + ".direction must be x or y")
        coordinate = _required_number(item, "coordinate", path)
        key = (direction, name)
        if key in seen:
            raise ProjectSchemaError(path + " duplicates grid " + direction + ":" + name)
        seen.add(key)
        grids.append(GridLine(name=name, direction=direction, coordinate=coordinate))
    return grids


def _parse_stories(raw):
    _require_type(raw, list, "project.stories")
    seen = set()
    stories = []
    for idx, item in enumerate(raw):
        path = "project.stories[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "elevation", "height"], path)
        name = _required_string(item, "name", path)
        if name in seen:
            raise ProjectSchemaError(path + " duplicates story " + name)
        seen.add(name)
        stories.append(Story(
            name=name,
            elevation=_required_number(item, "elevation", path),
            height=_required_number(item, "height", path),
        ))
    return stories


def _parse_member_classes(raw):
    _require_type(raw, list, "project.member_classes")
    seen = set()
    classes = []
    for idx, item in enumerate(raw):
        path = "project.member_classes[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "kind", "element_ids", "story", "use", "notes"], path)
        name = _required_string(item, "name", path)
        if name in seen:
            raise ProjectSchemaError(path + " duplicates member class " + name)
        seen.add(name)
        kind = _required_string(item, "kind", path)
        if kind not in ALLOWED_MEMBER_KINDS:
            raise ProjectSchemaError(path + ".kind is not supported: " + kind)
        classes.append(MemberClass(
            name=name,
            kind=kind,
            element_ids=tuple(_parse_int_list(_required(item, "element_ids", path), path + ".element_ids")),
            story=_optional_string(item, "story", path),
            use=_optional_string(item, "use", path),
            notes=_optional_string(item, "notes", path),
        ))
    return classes


def _parse_report(raw):
    _require_type(raw, dict, "project.report")
    _reject_unknown(
        raw,
        ["title", "mode", "language", "format", "include_manual_items", "include_warnings"],
        "project.report",
    )
    mode = _optional_string(raw, "mode", "project.report", default="practice")
    if mode not in ALLOWED_REPORT_MODES:
        raise ProjectSchemaError("project.report.mode is not supported: " + mode)
    output_format = _optional_string(raw, "format", "project.report", default="markdown")
    if output_format not in ALLOWED_REPORT_FORMATS:
        raise ProjectSchemaError("project.report.format is not supported: " + output_format)
    return ReportSettings(
        title=_optional_string(raw, "title", "project.report"),
        mode=mode,
        language=_optional_string(raw, "language", "project.report", default="ja"),
        format=output_format,
        include_manual_items=_optional_bool(raw, "include_manual_items", "project.report", default=True),
        include_warnings=_optional_bool(raw, "include_warnings", "project.report", default=True),
    )


def _parse_design_checks(raw):
    _require_type(raw, dict, "project.design_checks")
    _reject_unknown(raw, ["wood"], "project.design_checks")
    return DesignCheckSettings(wood=_parse_wood_check_settings(raw.get("wood", {})))


def _parse_wood_check_settings(raw):
    _require_type(raw, dict, "project.design_checks.wood")
    _reject_unknown(
        raw,
        ["enabled", "load_cases", "deflection_limit_ratio", "allowable_stresses"],
        "project.design_checks.wood",
    )
    allowable = _parse_wood_allowable_stresses(raw.get("allowable_stresses", {}))
    return WoodCheckSettings(
        enabled=_optional_bool(raw, "enabled", "project.design_checks.wood", default=False),
        load_cases=tuple(_parse_int_list(raw.get("load_cases", []), "project.design_checks.wood.load_cases")),
        deflection_limit_ratio=_optional_number(
            raw,
            "deflection_limit_ratio",
            "project.design_checks.wood",
            default=0.0,
        ),
        allowable_stresses=allowable,
    )


def _parse_wood_allowable_stresses(raw):
    _require_type(raw, dict, "project.design_checks.wood.allowable_stresses")
    _reject_unknown(
        raw,
        ["bending", "shear", "compression", "tension"],
        "project.design_checks.wood.allowable_stresses",
    )
    return WoodAllowableStresses(
        bending=_optional_number(raw, "bending", "project.design_checks.wood.allowable_stresses", default=0.0),
        shear=_optional_number(raw, "shear", "project.design_checks.wood.allowable_stresses", default=0.0),
        compression=_optional_number(raw, "compression", "project.design_checks.wood.allowable_stresses", default=0.0),
        tension=_optional_number(raw, "tension", "project.design_checks.wood.allowable_stresses", default=0.0),
    )


def _parse_int_list(raw, path):
    _require_type(raw, list, path)
    values = []
    for idx, item in enumerate(raw):
        if type(item) is not int:
            raise ProjectSchemaError(path + "[" + str(idx) + "] must be an integer")
        values.append(item)
    return values


def _required(raw, key, path):
    if key not in raw:
        raise ProjectSchemaError(path + "." + key + " is required")
    return raw[key]


def _required_string(raw, key, path):
    value = _required(raw, key, path)
    if type(value) is not str or value.strip() == "":
        raise ProjectSchemaError(path + "." + key + " must be a non-empty string")
    return value


def _optional_string(raw, key, path, default=""):
    value = raw.get(key, default)
    if type(value) is not str:
        raise ProjectSchemaError(path + "." + key + " must be a string")
    return value


def _required_number(raw, key, path):
    value = _required(raw, key, path)
    if type(value) not in (int, float):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    return float(value)


def _optional_number(raw, key, path, default):
    value = raw.get(key, default)
    if type(value) not in (int, float):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    return float(value)


def _optional_bool(raw, key, path, default):
    value = raw.get(key, default)
    if type(value) is not bool:
        raise ProjectSchemaError(path + "." + key + " must be true or false")
    return value


def _require_type(value, expected_type, path):
    if type(value) is not expected_type:
        raise ProjectSchemaError(path + " must be " + expected_type.__name__)


def _reject_unknown(raw, allowed, path):
    for key in raw.keys():
        if key not in allowed:
            raise ProjectSchemaError(path + "." + str(key) + " is not supported")

