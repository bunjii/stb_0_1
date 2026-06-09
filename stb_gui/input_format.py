"""Comment templates for Structural Toolbox input file formats."""

NEW_MODEL_TEMPLATE = """# --- NEW MODEL ---
# Structural Toolbox input file
#
# TYPE OF ANALYSIS: 3D LINEAR STATIC
#
# --- MATERIAL(MATE) ---
#         ID,       NAME,        E,        G,    Gamma,    Alpha,       Fy
#                           (N/mm2)   (N/mm2)   (kN/m3)       (-)   (N/mm2)
# MATE,      0,    STEEL,   205000,    79000,     78.5,  1.2e-05,      235
#
# --- DIAPHRAGM MATERIAL(DMAT) ---
#         ID,       NAME,        Ex,        Ey,       Gxy,      Nuxy,    Gamma,    Alpha
#                           (N/mm2)   (N/mm2)   (N/mm2)       (-)  (kN/m3)       (-)
# DMAT,      0,   SLAB01,    25500,    25500,  10625.0,     0.20,     0.0,     0.0
#
# --- SECTION(SECT) ---
#         ID,       NAME,    MAT,   TYPE,  DIM 1,  DIM 2,  DIM 3,  DIM 4
#                                            (mm)    (mm)    (mm)    (mm)
#   (TYPE 0: RECT., 1: CIRC., 2: I, 3: CHS, 4: RHS)
# SECT,      0,     RECT,      0,      0,  200.0,  300.0
#
# --- NODE ---
#         ID,         X,         Y,         Z
#                    (m)        (m)        (m)
# NODE,      0,       0.0,       0.0,       0.0,
# NODE,      1,       2.0,       0.0,       0.0,
#
# --- ELEMENT(ELEM) ---
#         ID,     Ni,     Nj,    SEC,     Beta
#                                         (deg)
# ELEM,      0,      0,      1,      0,      0.0
#
# --- DIAPHRAGM REGION(DIAP) ---
#         ID,       NAME,    TYPE,     DMAT/PRESET,        T,    THETA
#     TYPE: RIGID, SEMI/SEMI_RIGID, FLEX/FLEXIBLE
# DIAP,      1,  RC_SLAB,     SEMI,  DMAT=0,  T=150,  THETA=0
# DIAP,     10,  2F_MAIN,     SEMI,  TIMBER_FLOOR,  FLOOR_MAG=2.0,  THETA=0,  HMAX=1820
# DIAP,     20,   ROOF_A,     SEMI,  TIMBER_ROOF,   ROOF_MAG=1.0,   THETA=30, HMAX=1820
# DIAP,     30,  RIGID2F,    RIGID
#
# --- DIAPHRAGM OUTER POLYGON(DREG) ---
#    DIAP ID,  NODE1,  NODE2,  NODE3, ...
# DREG,      1,      0,      1,      2,      3
#
# --- DIAPHRAGM OPENING(DOPN) ---
#    DIAP ID,  NODE1,  NODE2,  NODE3, ...
# DOPN,      1,      4,      5,      6
#
# --- DIAPHRAGM MEMBRANE ELEMENT(DMEM) ---
#         ID,    DIAP,     N1,     N2,     N3
# DMEM,      1,      1,      0,      1,      2
#
# --- DIAPHRAGM CONNECTION(DCON) ---
#    DIAP ID,  TARGET,  [MEMBER ID],  TYPE,  TOL=...
# DCON,      1,     AUTO,  CONNECTED_RIGID,  TOL=0.01
# DCON,      1,   MEMBER,      0,  CONNECTED_RIGID,  TOL=0.01
# DCON,      1,   MEMBER,      1,  DISCONNECTED
# DCON,      1,     NODE,     35,  CONNECTED_RIGID,  TOL=0.01
#
# --- DIAPHRAGM LOAD(DLOD) ---
#    DIAP ID,    LC,            TYPE,  PX/PY or MASS/WEIGHT
#         AREA: kN/m2, LINE: kN/m, WEIGHT: kN/m2, MASS: kg/m2
# DLOD,      1,     1,            AREA,  PX=1.0, PY=0.0
# DLOD,      1,     1,            LINE,  N1=0, N2=1, PX=2.0, PY=0.0
# DLOD,      1,     1,          WEIGHT,  WEIGHT=3.0, AX=1.0, AY=0.0
#
# --- WOOD RATED WALL(WOOD_RATED_WALL) ---
#         ID,       NAME, MODEL=EQUIVALENT_BRACE/SHEAR_PANEL/MEMBRANE_WALL,
#                         M=wall multiplier, L=wall length(m), H=wall height(m),
#                         DIR=X/Y, RA=reference drift, N1..N4=wall corner nodes
# WOOD_RATED_WALL,  1,  W1_X,  MODEL=EQUIVALENT_BRACE,  M=2.0,  L=1.82,  H=2.73,
#                      DIR=X,  RA=0.0083333333,  N1=11,  N2=12,  N3=22,  N4=21,  DIAP=10
# WOOD_RATED_WALL,  2,  W2_Y,  MODEL=SHEAR_PANEL,  M=2.5,  L=1.82,  H=2.73,
#                      DIR=Y,  RA=0.0083333333,  N1=12,  N2=13,  N3=23,  N4=22,  DIAP=10
#
# --- ELEMENT JOINT(EJNT) ---
#    ELEM ID,      Ryi,      Rzi,      Ryj,      Rzj
#             (kNm/rad) (kNm/rad) (kNm/rad) (kNm/rad)
# EJNT,      0,      0.0,         ,      0.0,
#
# --- CONSTRAINT(CONS) ---
#    NODE ID,   TX,   TY,   TZ,   RX,   RY,   RZ
#   (0:FREE, 1:FIXED)
# CONS,      0,    1,    1,    1,    1,    1,    1
#
# --- LOAD NAME(LNME) ---
#       LC,     NAME
# LNME,      0,       DL
#
# --- LOAD COMBINATION(LCMB) ---
#       LC,     NAME,   FC1,   LC1,   FC2,   LC2, ...
# LCMB,      2,    EX(+),   2.0,     0,   1.0,     1
#
# --- POINT LOAD(PLOD) ---
#    NODE ID,   LC,     PX,     PY,     PZ,     MX,     MY,     MZ
#                      (kN)    (kN)    (kN)   (kNm)   (kNm)   (kNm)
# PLOD,      1,    0,    0.00,   0.00,  -5.00,   0.00,   0.00,   0.00
#
# --- ELEMENT LOAD(ELOD) ---
#    ELEM ID,   LC,  E/G,    WXi,    WYi,    WZi,    WXj,    WYj,    WZj
#                          (kN/m)  (kN/m)  (kN/m)  (kN/m)  (kN/m)  (kN/m)
#   (E/G: Element(=0) or Global(=1) Coordinate System)
# ELOD,      0,    0,    0,   0.00,   0.00, -10.00,   0.00,   0.00, -10.00
#
# --- AREA LOAD(ALOD) ---
#         LC,     PX,     PY,     PZ,   E1,   E2,   E3,   E4
#             (kN/m2) (kN/m2) (kN/m2)
# ALOD,      0,   0.00,   0.00,  -5.00,    0,    1,    2,    3
#
# --- GRAVITY LOAD(GLOD) ---
#         LC,     Vec X,     Vec Y,     Vec Z
#                 (m/s2)     (m/s2)     (m/s2)
# GLOD,      0,  0.000000,  0.000000,  -9.806650
#
# --- AXIS (AXIS) ---
#         ID,       NAME,    V/H,    NID,  x-DIR(if V)
#                  (V/H 0:V, 1:H)     (x-DIR 0:X, 1:Y)
# AXIS,      0,       A1,      0,      0,      0
#
# --- PLOT (PLOT) ---
#         ID,       NAME,   AXIS,   TYPE,     LC,  SCALE, DEFFAC
#             (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)
# PLOT,      0,     MDL1,      0,      0,      0,     50,   50.0

"""

EJNT_EDITOR_HEADER = """# --- ELEMENT JOINT (EJNT) ---
#    ELEM ID,      Ryi,      Rzi,      Ryj,      Rzj
#             (kNm/rad) (kNm/rad) (kNm/rad) (kNm/rad)
# Empty field = default rigid offset. Delete a line to remove EJNT (rigid joint).

"""
