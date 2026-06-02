# Structural Toolbox

3D linear static analysis for frame structures. Use the **CLI** (`stb solve`) and **browser viewer** (`stb view`); the headless engine (`stb_engine`) is the shared solver core.

## Virtual environment (each PC)

Do **not** commit or share `.venv` via Git. Create one local venv per machine (Linux / Windows each use `.venv` in the project folder, or a path outside Dropbox).

```bash
cd /path/to/stb_0_1
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[viewer]"
```

Multi-machine / Dropbox notes: [docs/setup_venv.md](docs/setup_venv.md).

## Command-line interface (Phase 1)

Install the `stb` command (once per virtual environment):

```bash
cd /path/to/stb_0_1
.venv/bin/pip install -e .
```

Use the `stb` inside the project virtual environment (recommended):

```bash
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever_out.dat -q -v
```

Or activate the venv first: `source .venv/bin/activate`, then run `stb ...`.

### Troubleshooting: `ModuleNotFoundError` (e.g. shapely)

If `which stb` shows `~/.local/bin/stb`, you may be running a **user install** with system Python (`/usr/bin/python3`), not the project `.venv`. That Python often lacks solver dependencies.

Fix (pick one):

```bash
# A) Recommended: install into project .venv and call it explicitly
cd /path/to/stb_0_1
.venv/bin/pip install -e .
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever_out.dat -q -v

# B) Remove the conflicting user entry, then use .venv only
python3 -m pip uninstall structural-toolbox
hash -r
```

Check which Python runs `stb`: `head -1 "$(which stb)"` should point to `.venv/bin/python`, not `/usr/bin/python3`.

### Commands

```bash
# Smallest sample (see examples/README.md)
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever_out.dat -q -v

# Run analysis; write results to a file
stb solve data/input01.dat -o tests/_tmp_out/out.dat

# Same without installing (from project root)
.venv/bin/python -m stb_cli solve data/input01.dat -o tests/_tmp_out/out.dat

# Parse input only (no solve)
stb validate data/input01.dat -v

# Version
stb version

# Web 3D viewer (Phase C1)
.venv/bin/pip install -e ".[viewer]"
.venv/bin/stb view --file examples/cantilever.dat
# or: .venv/bin/python -m stb_viewer
```

### Web viewer (Phase C1)

Read-only **Three.js** frame viewer in the browser. Lists models under `data/` and `examples/`.

```bash
.venv/bin/pip install -e ".[viewer]"
.venv/bin/stb view --file data/input01.dat --port 8765
```

Open http://127.0.0.1:8765/ — drag to orbit, scroll to zoom. Main bar: model, **Solve**, **Results** (forces, LC, deformation), **Options** (load arrow / label sizes; settings persist).

Stop the server with **Ctrl+C**.

### Options

| Flag | Effect |
|------|--------|
| `-o`, `--output` | Result file (`solve` only; default is stdout) |
| `-q`, `--quiet` | Suppress solver progress messages on stderr/stdout |
| `-v`, `--verbose` | Print status (node count, load cases, output path) |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Input error (missing file, parse failure) |
| `2` | Analysis error |

### Python API (Phase 0)

```bash
.venv/bin/python -c "
from stb_engine import run_from_file
mdl, txt = run_from_file('data/input01.dat', 'tests/_tmp_out/out.dat')
print('load cases:', mdl.lcs)
"
```

**Public API:** `parse_input`, `solve_model`, `format_results`, `run_from_lines`, `run_from_file`

**Exceptions:** `StbParseError`, `StbSolveError`

Input and output use the same comma-separated text format (editable in the web viewer).  
**Input reference:** [docs/input_format.md](docs/input_format.md) (`PLOD`, `ELOD`, `ALOD`, `GLOD`, … — not `LOAD`).

### Tests

```bash
.venv/bin/python -m unittest tests.test_engine tests.test_cli tests.test_data_models tests.test_viewer -v
```
