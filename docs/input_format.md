# Input text format (Structural Toolbox)

Comma-separated text files (`.dat`, `.stb`, etc.) for 3D linear static frame analysis.  
The GUI editor, `stb solve`, and `stb validate` all use the same parser (`ReadLines` in `classes/io.py`).

## General rules

- One record per line; fields separated by **commas** (`,`).
- Lines starting with `#` are comments and ignored.
- Blank lines are ignored.
- **Use explicit load keywords** — see [Loads](#loads) below.
- Define materials and sections before elements that reference them; define nodes before elements.

### Not supported: `LOAD`

The keyword **`LOAD` is not read**. It does not mean “point, line, or area” and is intentionally unsupported.

| Intent | Use |
|--------|-----|
| Point load (force/moment at a node) | **`PLOD`** |
| Distributed load on a member | **`ELOD`** |
| Pressure on a panel bounded by members | **`ALOD`** |
| Self-weight / gravity direction | **`GLOD`** |

Old files may still contain `LOAD` lines (e.g. `data/input01.dat`); those lines are **silently ignored**. Replace them with `PLOD` if you need those point loads.

---

## Units (input)

| Quantity | Input unit | Notes |
|----------|------------|--------|
| Node coordinates | m | |
| Material E, G, Fy | N/mm² | Converted internally to N/m² |
| Material γ (Gamma) | kN/m³ | Converted to N/m³ |
| Section dimensions | mm | Converted to m |
| Point loads (PLOD) | kN, kNm | |
| Member loads (ELOD) | kN/m | |
| Area loads (ALOD) | kN/m² | |
| Gravity (GLOD) | m/s² | Components gx, gy, gz |
| EJNT spring values | kNm/rad | Optional; blank = default rigid offsets |
| Element beta (ELEM) | degrees | |
| Diaphragm material Ex, Ey, Gxy | N/mm² | Converted internally to N/m² |
| Diaphragm thickness T | mm | Converted internally to m |
| Diaphragm material axis THETA | degrees | In-plane angle from each membrane element local x axis |

Load case IDs (`LC`) are integers you choose (e.g. `0`, `1`, `2`). Every load record must include an `LC` field.

---

## Geometry and properties

### `MATE` — material

```
MATE, ID, NAME, E, G, Gamma, Alpha, Fy
```

| Field | Unit | Description |
|-------|------|-------------|
| E, G | N/mm² | Young’s modulus, shear modulus |
| Gamma | kN/m³ | Weight density |
| Alpha | — | Thermal expansion coefficient |
| Fy | N/mm² | Yield stress (stored; linear analysis) |

Short alias: line may start with `m` (lowercase) instead of `MATE`.

---

### `SECT` — cross-section

```
SECT, ID, NAME, MAT_ID, TYPE, DIM1, DIM2, ...
```

| TYPE | Shape | Dimensions (mm) |
|------|--------|-----------------|
| 0 | Rectangle | B, H |
| 1 | Circle | D |
| 2 | I-section | H, B, tw, tf |
| 3 | CHS (tube) | D, t |
| 4 | RHS | H, B, t |

`MAT_ID` must refer to an existing `MATE` record.

Short alias: `s` instead of `SECT`.

---

### `NODE` — node

```
NODE, ID, X, Y, Z
```

Coordinates in **metres**. Optional trailing `*` in some GUI exports is ignored by the parser if present after the Z value (see legacy files).

Short alias: `n` instead of `NODE`.

---

### `ELEM` — frame element (straight member)

```
ELEM, ID, NODE_I, NODE_J, SEC_ID, BETA
```

- Connects two nodes with a 1D frame element.
- `BETA` (degrees): section rotation about the member axis; default `0` if omitted.

Short aliases: `ELEM` or `ele`.

---

### `EJNT` — element end releases / springs (optional)

```
EJNT, ELEM_ID, Ryi, Rzi, Ryj, Rzj
```

| Field | Unit | Description |
|-------|------|-------------|
| Ryi, Rzi, Ryj, Rzj | kNm/rad | Rotational spring at ends; empty field = use built-in default |

If no `EJNT` line exists for an element, default joint stiffness is assigned in the model builder.

Short alias: `ej`.

---

### `DMAT` — diaphragm material

```
DMAT, ID, NAME, Ex, Ey, Gxy, Nuxy, Gamma, Alpha
```

Plane-stress material used by diaphragm membrane elements. This is the low-level
input for verification and advanced use. Ordinary preset inputs will be added on
top of this in later phases.

| Field | Unit | Description |
|-------|------|-------------|
| Ex, Ey, Gxy | N/mm² | Orthotropic in-plane elastic constants |
| Nuxy | — | Major Poisson ratio |
| Gamma | kN/m³ | Weight density, stored for future use |
| Alpha | — | Thermal expansion coefficient, stored for future use |

For isotropic behavior, use `Ex = Ey = E`, `Gxy = E / (2(1 + nu))`, `Nuxy = nu`.

---

### `DIAP` — diaphragm region

```
DIAP, ID, NAME, TYPE, DMAT=MAT_ID, T=THICKNESS, THETA=ANGLE
```

Defines a floor/roof diaphragm region. Phase 1 supports `TYPE = SEMI` with
manual `DMEM` triangles. `RIGID` and `FLEX` are reserved for future diaphragm
strategy switching.

| Field | Unit | Description |
|-------|------|-------------|
| TYPE | — | `SEMI`, `RIGID`, or `FLEX` |
| DMAT | — | Diaphragm material ID |
| T | mm | Membrane thickness |
| THETA | degrees | Material axis angle in the membrane plane |

Positional form is also accepted for the MVP:

```
DIAP, ID, NAME, SEMI, MAT_ID, T, THETA
```

---

### `DMEM` — 3-node CST membrane element

```
DMEM, ID, DIAP_ID, NODE1, NODE2, NODE3
```

Adds a 3-node constant-strain membrane element to a diaphragm. The element uses
local in-plane `u, v` displacement components and contributes stiffness to the
global translational DOFs `ux, uy, uz` of the three referenced nodes. Rotational
DOFs are not used by this element.

---

### `DCON` — diaphragm-to-member connection

```
DCON, DIAP_ID, AUTO, CONNECTION_TYPE, TOL=...
DCON, DIAP_ID, MEMBER, ELEM_ID, CONNECTION_TYPE, TOL=...
```

Associates existing frame members with a diaphragm mesh. The MVP supports
`CONNECTED_RIGID` and `DISCONNECTED`. `CONNECTED_RIGID` generates MPC
constraints for the member end nodes found on the diaphragm boundary or inside
the diaphragm triangles. Only horizontal `ux, uy` DOFs are constrained.

| Field | Unit | Description |
|-------|------|-------------|
| TARGET | — | `AUTO` for all members, or `MEMBER` for one element |
| CONNECTION_TYPE | — | `CONNECTED_RIGID`, `DISCONNECTED`; `LOAD_TRANSFER_ONLY` and `CONNECTED_SPRING` are reserved |
| TOL | m | Geometry tolerance for edge/triangle matching |

Examples:

```
DCON, 1, AUTO, CONNECTED_RIGID, TOL=0.01
DCON, 1, MEMBER, 201, DISCONNECTED
```

---

### `DREG` / `DOPN` — diaphragm region and opening polygons (reserved)

```
DREG, DIAP_ID, NODE1, NODE2, NODE3, ...
DOPN, DIAP_ID, NODE1, NODE2, NODE3, ...
```

These records are reserved for future automatic diaphragm meshing. `DREG`
defines an outer polygon and `DOPN` defines an opening polygon. Phase 1 keeps
these records as metadata; analysis uses manually supplied `DMEM` triangles.

---

### `CONS` — support (boundary condition)

```
CONS, NODE_ID, TX, TY, TZ, RX, RY, RZ
```

Each DOF: **`0` = free**, **`1` = fixed**.

Short alias: `c`.

---

## Loads

### `PLOD` — point load (nodal)

```
PLOD, NODE_ID, LC, PX, PY, PZ, MX, MY, MZ
```

Forces in **kN**, moments in **kNm**, in the **global** coordinate system.

Example (5 kN downward at node 1, load case 0):

```
PLOD, 1, 0, 0.00, 0.00, -5.00, 0.00, 0.00, 0.00
```

Short alias: `plo`.

---

### `ELOD` — member distributed load (line load)

```
ELOD, ELEM_ID, LC, E_G, WXi, WYi, WZi, WXj, WYj, WZj
```

| Field | Description |
|-------|-------------|
| E_G | `0` = element local axes, `1` = global axes |
| WXi…WZj | Distributed load intensity at start/end (kN/m) |

Short alias: `elo`.

---

### `ALOD` — area load (surface pressure)

```
ALOD, LC, PX, PY, PZ, ELEM1, ELEM2, ELEM3, ELEM4
```

| Field | Unit | Description |
|-------|------|-------------|
| PX, PY, PZ | kN/m² | Pressure components (global axes) |
| ELEM1…ELEM4 | — | Member IDs bounding the loaded panel (triangle: use 3 IDs; 4th optional) |

The pressure is distributed to the bounding members with the **tributary-area
method**: the panel surface is partitioned by nearest boundary edge
(medial-axis / 45° rule), and each member receives an equivalent
linearly-varying line load that reproduces the exact tributary resultant and
its centroid. This preserves global equilibrium and support reactions exactly,
including the member-axial pressure component. The bounding members must form a
single closed triangular or quadrilateral loop.

Short alias: `al`.

---

### `GLOD` — gravity / acceleration

```
GLOD, LC, GX, GY, GZ
```

Acceleration components in **m/s²** (e.g. `0, 0, -9.80665` for downward Z).

Short alias: `gl`.

---

## Load cases and combinations (optional)

### `LNME` — load case name (optional metadata)

```
LNME, LC_ID, NAME
```

### `LCMB` — load combination

```
LCMB, COMB_LC, NAME, factor1, lc1, factor2, lc2, ...
```

Creates a combined load case `COMB_LC` from existing cases with factors.  
Pairs of `(factor, lc)` repeat for each term.

---

## Post-processing / plotting (optional, GUI)

### `AXIS` — plot axis definition

```
AXIS, ID, NAME, V_H, NODE_ID, X_DIR
```

| V_H | `0` = vertical plane, `1` = horizontal |
| X_DIR | For vertical: `0` = global X, `1` = global Y |

Short alias: `ax`.

---

### `PLOT` — plot request

```
PLOT, ID, NAME, AXIS_ID, TYPE, LC, SCALE, DEFFAC
```

| TYPE | Meaning |
|------|---------|
| 0 | Model |
| 1 | Load |
| 2 | Force diagram |
| 3 | Utilization |

Short alias: `plt`.

---

## Minimal input example

See `examples/cantilever.dat`:

```
MATE, ...
SECT, ...
NODE, ...
ELEM, ...
CONS, ...
PLOD, ...
```

Run:

```bash
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever.out -q
```

---

## Output format (after `stb solve`)

Result files are text, with records such as:

| Tag | Content |
|-----|---------|
| `SPRP` | Section properties (computed) |
| `NDSP` | Nodal displacements (m, rad) |
| `REAC` | Reactions at constrained nodes (kN, kNm) |
| `EFRC` | Element end forces (kN, kNm) |

See `examples/cantilever.out` for a full example.

---

## Suggested order when writing a new file

1. `MATE`, `SECT`
2. `NODE`
3. `ELEM` (and optional `EJNT`)
4. `CONS`
5. `PLOD`, `ELOD`, `ALOD`, `GLOD` (and optional `LNME`, `LCMB`)
6. Optional `AXIS`, `PLOT` (mainly for GUI)

Validate before solving:

```bash
.venv/bin/stb validate mymodel.dat -v
```
