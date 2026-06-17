# STB Grasshopper .gha Scaffold

This is a Grasshopper SDK scaffold for the Karamba3D-like STB workflow.

The MVP intentionally calls the existing STB CLI instead of embedding Python in
Rhino. This keeps `numpy`, `scipy`, and `shapely` inside the repository virtual
environment and makes classroom Windows deployment easier.

## Components

- `STB Analyze`: runs `python -m stb_cli solve`
- `STB Load Cases`: lists available load cases in parsed results
- `STB Displacements`: exposes load case, node id, translation, and rotation rows
- `STB Forces`: exposes parsed element force rows
- `STB DAT Nodes`: reads original node points from an existing `.dat` file
- `STB DAT Beams`: reads element connectivity from an existing `.dat` file
- `STB Node`, `STB Beam`, `STB Material`, `STB Section`, `STB Support`, `STB Load`, `STB Assemble Model`: early model-building placeholders
- `STB Deformed Shape`: preview placeholder for the next step

## Build Notes

This project targets Rhino 8 and `net7.0` so the same source can be built for
Windows and macOS Grasshopper. Grasshopper/Rhino assemblies are not committed to
this repository; `StbGrasshopper.csproj` resolves them from a local Rhino 8
installation.

Default Windows Rhino 8 paths:

```text
C:\Program Files\Rhino 8\System\
C:\Program Files\Rhino 8\Plug-ins\Grasshopper\
```

Default macOS Rhino 8 paths:

```text
/Applications/Rhino 8.app/Contents/Resources/RhinoCommon.dll
/Applications/Rhino 8.app/Contents/Resources/ManagedPlugIns/GrasshopperPlugin.rhp/Grasshopper.dll
```

Build:

```powershell
dotnet build grasshopper\gha\StbGrasshopper.csproj -c Release
```

On macOS:

```bash
dotnet build grasshopper/gha/StbGrasshopper.csproj -c Release
```

If Rhino is installed somewhere else, pass explicit paths:

```bash
dotnet build grasshopper/gha/StbGrasshopper.csproj -c Release \
  -p:RhinoCommonPath="/path/to/RhinoCommon.dll" \
  -p:GrasshopperPath="/path/to/Grasshopper.dll"
```

The build output is `bin/Release/StbGrasshopper.gha`.

## Runtime Notes

`STB Analyze` calls the Python CLI outside Rhino. Use the platform-specific
virtual environment Python:

- Windows: `.venv\Scripts\python.exe`
- macOS: `.venv/bin/python`

The repository itself must be installed in that virtual environment:

```bash
python -m pip install -e .
```

## Load case workflow

- `STB Analyze` keeps all load cases in `Results` when `Load Case` is `-1` (default).
- Set `Load Case` on `STB Displacements`, `STB Forces`, and `STB Deformed Shape` to choose which LC to display.
- Use `STB Load Cases` to inspect available LC ids from `Results`.
- Negative `Load Case` on result components means "show all load cases".
- `STB Analyze` now embeds node coordinates and element connectivity from the `.dat` file into `Results`.
- `STB Deformed Shape` only needs `Results`, `Load Case`, and `Scale`.

The first component to make production-ready is `StbAnalyzeComponent.cs`.
