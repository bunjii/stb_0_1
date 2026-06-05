# Project sidecar format (`model.project.json`)

`model.project.json` is an optional JSON file placed next to an existing
analysis input file. It does not replace or change the low-level `.dat` format.
The `.dat` file remains the source for nodes, elements, sections, loads, and
analysis cases. The project file adds the minimum building-level information
needed for practice reports and classroom views.

Default sidecar name:

| Analysis file | Project file |
|---|---|
| `model.dat` | `model.project.json` |
| `data/input01.dat` | `data/input01.project.json` |

## Minimal example

```json
{
  "schema": 1,
  "model": {
    "dat": "model.dat"
  },
  "building": {
    "name": "Sample wooden single-story building",
    "location": "Tokyo",
    "use": "residential",
    "structure": "wood",
    "calculation_route": "route-1",
    "designer": {
      "name": "Structural Toolbox User",
      "qualification": "",
      "license_number": "",
      "contact": ""
    }
  },
  "grids": [
    {"name": "X1", "direction": "x", "coordinate": 0.0},
    {"name": "X2", "direction": "x", "coordinate": 3.64},
    {"name": "Y1", "direction": "y", "coordinate": 0.0},
    {"name": "Y2", "direction": "y", "coordinate": 2.73}
  ],
  "stories": [
    {"name": "1", "elevation": 0.0, "height": 3.0}
  ],
  "member_classes": [
    {
      "name": "main_columns",
      "kind": "column",
      "element_ids": [1, 2, 3, 4],
      "story": "1",
      "use": "wood column",
      "notes": ""
    },
    {
      "name": "roof_beams",
      "kind": "beam",
      "element_ids": [5, 6],
      "story": "1",
      "use": "wood beam",
      "notes": ""
    }
  ],
  "report": {
    "title": "Structural calculation draft",
    "mode": "practice",
    "language": "ja",
    "format": "markdown",
    "include_manual_items": true,
    "include_warnings": true
  }
}
```

## Fields

`schema`
: Schema version. The first supported version is `1`.

`model.dat`
: Path to the existing analysis `.dat` file, relative to this JSON file.

`building`
: Building overview for report front matter: name, location, use, structure,
  calculation route, and designer information.

`grids`
: Grid lines used by practice and education layers. `direction` is `x` or `y`;
  `coordinate` uses the same metre coordinate system as `NODE` records.

`stories`
: Story definitions. `elevation` and `height` are metres. For the first MVP,
  a wooden single-story project can define one story with `name: "1"`.

`member_classes`
: Meaning added on top of `.dat` element IDs. Supported `kind` values are
  `beam`, `column`, `brace`, `foundation_beam`, `panel`, `support`,
  `lateral_resisting_element`, and `other`.

`report`
: Report generation settings. `mode` is `practice`, `education`, or `debug`.
  `format` is `markdown`, `html`, or `pdf`; the MVP starts from Markdown.

## Python API

```python
from stb_project import load_project_for_dat

project = load_project_for_dat("data/input01.dat")
if project is not None:
    print(project.building.name)
```

`load_project_for_dat()` returns `None` when the sidecar file is missing unless
`required=True` is passed. This keeps existing `.dat` workflows unchanged.

