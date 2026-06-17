# Grasshopper STB Integration

This folder contains the first Grasshopper integration layer for Structural Toolbox.
The recommended MVP is to call the existing CLI from Grasshopper, then parse the
`.out` file into lists or DataTrees.

## Phase 1: Script Component

Use `stb_analyze_script.py` as the code behind a Grasshopper Python Script
component.

Inputs:

- `datPath`: path to the STB `.dat` file
- `pythonExe`: path to the project Python, usually `.venv\Scripts\python.exe`
- `repoRoot`: path to this repository
- `run`: boolean toggle
- `outPath`: optional output path
- `loadCase`: optional integer load case filter

Outputs:

- `success`
- `exitCode`
- `outPath`
- `stdout`
- `stderr`
- `summary`
- `nodeIds`
- `loadCases`
- `translations`
- `rotations`

The script internally runs:

```powershell
.venv\Scripts\python.exe -m stb_cli solve input.dat -o output.out -q -v
```

Arguments are passed as a list, so paths with spaces are supported.

## Local Smoke Test

From the repository root:

```powershell
.venv\Scripts\python.exe grasshopper\stb_analyze_script.py data\UK_240416_floors_1to3_diaphragm.dat --repo-root . --out tests\_tmp_out\gh_uk_diaphragm.out --load-case 0
```

Expected result:

- exit code `0`
- an output file at `tests\_tmp_out\gh_uk_diaphragm.out`
- a summary containing `Solved UK_240416_floors_1to3_diaphragm.dat`
- displacement rows are available as `nodeIds`, `loadCases`, `translations`, and `rotations`

## Phase 2: Result Parser

`stb_out_parser.py` parses the current STB text output records:

- `NDSP`: nodal displacement
- `REAC`: reaction force
- `EFRC`: element force

The first Grasshopper outputs expose only `NDSP` because that is the smallest
useful Karamba3D-like result flow. `REAC` and `EFRC` are parsed so later
components can expose support reactions and member force diagrams without
rewriting the parser.

## Phase 3: .gha MVP

The `gha/` folder contains a C# Grasshopper SDK scaffold. It mirrors the script
component behavior:

- `STB Analyze`: runs `stb_cli solve`
- `STB Displacements`: extracts nodal displacement lists
- `STB Forces`: exposes parsed element force rows
- `STB Deformed Shape`: placeholder for viewport preview logic

The scaffold expects Grasshopper/Rhino references to be supplied locally because
their paths differ by Rhino version and installation.
