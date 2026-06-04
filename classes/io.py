import datetime

from nd   import Nd
from elm  import Elm1D
from ejnt import EJnt
from mat  import Mat
from sec  import Sec
from cons import Cons
from ld   import PLd, ELd, ALd, GLd, Lcase, Lcmb
from mdl  import Mdl
from axis import Axis
from plt  import Plt 
from diaphragm import (
    DiaphragmMaterial, DiaphragmRegion, DiaphragmPolygon, DiaphragmOpening,
    CSTMembrane3, DiaphragmConnection
)
import common


def _clean_items(line):
    return [item.strip() for item in line.split(',')]


def _kv_items(items):
    out = {}
    positional = []
    for item in items:
        s = item.strip()
        if not s:
            continue
        if "=" in s:
            k, v = s.split("=", 1)
            out[k.strip().upper()] = v.strip()
        else:
            positional.append(s)
    return out, positional


def _find_by_id(seq, id_value, label):
    found = list(filter(lambda x: x.id == id_value, seq))
    if not found:
        raise ValueError("{0} id not found: {1}".format(label, id_value))
    return found[0]


def ReadLines(_lns):

    nds   = []
    elms  = []
    ejnts = []
    mats  = []
    secs  = []
    cons  = []
    lds   = [] 
    elds  = []
    alds  = []
    glds  = []
    axes  = []
    plts  = []
    lcases= []
    lcmbs = []
    dmats = []
    diaps = []
    dregs = []
    dopns = []
    dcons = []
    dmem_specs = []

    for i in range(len(_lns)):

        l = _lns[i]

        if l.startswith('#'): continue

        items = _clean_items(l)
        key = items[0].upper() if items and items[0] else ""

        if l.startswith("MATE") or l.startswith("m") :

            id   =   int(items[1])
            name =   str(items[2]).strip()
            e    = float(items[3]) * 1e6  # [N/mm2] -> [N/m2] 
            g    = float(items[4]) * 1e6  # [N/mm2] -> [N/m2] 
            gm   = float(items[5]) * 1e3  # [kN/m3] -> [N/m3] 
            al   = float(items[6])
            fy   = float(items[7]) * 1e6  # [N/mm2] -> [N/m2] 

            mats.append(Mat(id, name, e, g, gm, al, fy))

        elif key == "DMAT" or key == "DM":

            id    = int(items[1])
            name  = str(items[2]).strip()
            ex    = float(items[3]) * 1e6  # [N/mm2] -> [N/m2]
            ey    = float(items[4]) * 1e6  # [N/mm2] -> [N/m2]
            gxy   = float(items[5]) * 1e6  # [N/mm2] -> [N/m2]
            nuxy  = float(items[6])
            gamma = float(items[7]) * 1e3 if len(items) > 7 and items[7] != "" else 0.0
            alpha = float(items[8]) if len(items) > 8 and items[8] != "" else 0.0

            dmats.append(DiaphragmMaterial(id, name, ex, ey, gxy, nuxy, gamma, alpha))

        elif l.startswith("SECT")  or l.startswith("s") :

            id   = int(items[1])
            name = str(items[2]).strip()
            mat  = list(filter(lambda n: n.id == int(items[3]), mats))[0]
            type = int(items[4])
            dims = list(map(lambda d: float(d) * 1e-3, items[5:])) # [mm] -> [m]
            
            secs.append(Sec(id, name, mat, type, dims))

        elif l.startswith("NODE") or l.startswith("n"):

            id =   int(items[1]) 
            x  = float(items[2]) # [m]
            y  = float(items[3]) # [m]
            z  = float(items[4]) # [m]

            nds.append(Nd(id, x, y, z))

        elif l.startswith("ELEM") or l.startswith("ele"):

            id  = int(items[1])
            n0  = list(filter(lambda n: n.id == int(items[2]), nds))[0]
            n1  = list(filter(lambda n: n.id == int(items[3]), nds))[0]
            sec = list(filter(lambda s: s.id == int(items[4]), secs))[0]
            if len(items) > 5:
                theta = float(items[5])
            else:
                theta = 0.0

            elms.append(Elm1D(id, n0, n1, sec, theta)) 

        elif l.startswith("EJNT") or l.startswith("ej"):

            eid  = int(items[1])
            jnts = [0.0] * 4

            #for i in range(12):
            for i in range(4):
                try:
                    jnts[i] = float(items[i+2]) * 1e3 # [kNm/rad] -> [kNm2/rad] or [kNm] -> [Nm]
                except ValueError:
                    jnts[i] = None  

            ejnts.append(EJnt(eid, jnts))

        elif key == "DIAP" or key == "DI":

            id   = int(items[1])
            name = str(items[2]).strip()
            type = str(items[3]).strip().upper()
            kv, pos = _kv_items(items[4:])

            mat_id = None
            if "DMAT" in kv:
                mat_id = int(kv["DMAT"])
            elif len(pos) > 0:
                mat_id = int(pos[0])

            if "T" in kv:
                thick = float(kv["T"]) * 1e-3  # [mm] -> [m]
            elif "THICK" in kv:
                thick = float(kv["THICK"]) * 1e-3
            elif len(pos) > 1:
                thick = float(pos[1]) * 1e-3
            else:
                raise ValueError("DIAP thickness is required")

            if "THETA" in kv:
                theta = float(kv["THETA"])
            elif len(pos) > 2:
                theta = float(pos[2])
            else:
                theta = 0.0

            mat = _find_by_id(dmats, mat_id, "DMAT")
            diaps.append(DiaphragmRegion(id, name, type, mat, thick, theta))

        elif key == "DREG" or key == "DR":

            diap_id = int(items[1])
            node_ids = [int(v) for v in items[2:] if v != ""]
            dregs.append(DiaphragmPolygon(diap_id, node_ids))

        elif key == "DOPN" or key == "DO":

            diap_id = int(items[1])
            node_ids = [int(v) for v in items[2:] if v != ""]
            dopns.append(DiaphragmOpening(diap_id, node_ids))

        elif key == "DMEM" or key == "DME":

            id = int(items[1])
            diap_id = int(items[2])
            nids = [int(items[3]), int(items[4]), int(items[5])]
            dmem_specs.append((id, diap_id, nids))

        elif key == "DCON" or key == "DC":

            diap_id = int(items[1])
            target_type = str(items[2]).strip().upper()
            kv, pos = _kv_items(items[3:])

            target_id = None
            connection_type = "CONNECTED_RIGID"
            if target_type in ["MEMBER", "ELEM", "ELEMENT"]:
                if len(pos) < 2:
                    raise ValueError("DCON MEMBER needs member id and connection type")
                target_id = int(pos[0])
                connection_type = str(pos[1]).strip().upper()
            else:
                if len(pos) > 0:
                    connection_type = str(pos[0]).strip().upper()

            tolerance = float(kv["TOL"]) if "TOL" in kv else common.PRES_LEN
            spacing = None
            if "SPACING" in kv:
                spacing = float(kv["SPACING"])
            elif "HMAX" in kv:
                spacing = float(kv["HMAX"])

            dcons.append(DiaphragmConnection(
                diap_id, target_type, target_id, connection_type,
                tolerance, spacing
            ))

        elif l.startswith("CONS") or l.startswith("c"):

            nid =      int(items[1])
            tx  = bool(int(items[2]))
            ty  = bool(int(items[3]))
            tz  = bool(int(items[4]))
            rx  = bool(int(items[5]))
            ry  = bool(int(items[6]))
            rz  = bool(int(items[7]))

            cons.append(Cons(nid, tx, ty, tz, rx, ry, rz))

        elif l.startswith("PLOD") or l.startswith("plo"):

            nid =   int(items[1])
            lc  =   int(items[2])
            px  = float(items[3]) * 1e3 # [kN]  --> [N]
            py  = float(items[4]) * 1e3 # [kN]  --> [N]
            pz  = float(items[5]) * 1e3 # [kN]  --> [N]
            mx  = float(items[6]) * 1e3 # [kNm] --> [Nm]
            my  = float(items[7]) * 1e3 # [kNm] --> [Nm]
            mz  = float(items[8]) * 1e3 # [kNm] --> [Nm]

            lds.append(PLd(nid, lc, px, py, pz, mx, my, mz)) 

        elif l.startswith("ELOD") or l.startswith("elo"):

            eid =   int(items[1])
            lc  =   int(items[2])
            isGlobal = int(items[3])
            wxi  = float(items[4]) * 1e3 # [kN/m] --> [N/m]
            wyi  = float(items[5]) * 1e3 # [kN/m] --> [N/m]
            wzi  = float(items[6]) * 1e3 # [kN/m] --> [N/m]
            wxj  = float(items[7]) * 1e3 # [kN/m] --> [N/m]
            wyj  = float(items[8]) * 1e3 # [kN/m] --> [N/m]
            wzj  = float(items[9]) * 1e3 # [kN/m] --> [N/m]

            elds.append(ELd(eid, lc, isGlobal, wxi, wyi, wzi, wxj, wyj, wzj)) 

        elif l.startswith("ALOD") or l.startswith("al"):

            lc = int(items[1])
            px = float(items[2]) * 1e3 # [kN/m2] --> [N/m2]
            py = float(items[3]) * 1e3 # [kN/m2] --> [N/m2]
            pz = float(items[4]) * 1e3 # [kN/m2] --> [N/m2]
            e1 = int(items[5])
            e2 = int(items[6])
            e3 = int(items[7])

            if len(items) > 8:
                e4 = int(items[8])
            else:
                e4 = None

            alds.append(ALd(lc, px, py, pz, e1, e2, e3, e4))
        
        elif l.startswith("GLOD") or l.startswith("gl"):

            lc =   int(items[1])
            gx = float(items[2])
            gy = float(items[3])
            gz = float(items[4])

            glds.append(GLd(lc, gx, gy, gz))

        elif l.startswith("LNME"):
            lid   = int(items[1])
            lname = str(items[2]).strip()

            lcases.append(Lcase(lid, lname))

        elif l.startswith("LCMB"):

            fcs = []
            lcs = []

            lc  = int(items[1])
            name = str(items[2]).strip()

            datalen = len(items)-3

            for i in range(datalen):
                if i % 2 == 0:
                    fcs.append(float(items[i+3]))
                else:
                    lcs.append(int(items[i+3]))

            lcmbs.append(Lcmb(lc, name, fcs, lcs))

        elif l.startswith("AXIS") or l.startswith("ax"):

            id   = int(items[1])
            name = str(items[2]).strip()
            isHorizontal = bool(int(items[3]))
            nid  = int(items[4])

            if len(items) > 5:
                try: 
                    xdir = int(items[5])
                except ValueError:
                    xdir = None
            else:
                xdir = None

            axes.append(Axis(id, name, isHorizontal, nid, xdir))

        elif l.startswith("PLOT") or l.startswith("plt"):

            id   = int(items[1])
            name = str(items[2]).strip()
            axis = int(items[3])
            type = int(items[4])
            
            try:
                lc = int(items[5])
            except ValueError:
                lc = None

            scale = int(items[6]) 

            if len(items) > 7:
                deffac = float(items[7])
            else:
                deffac = 0

            plts.append(Plt(id, name, axis, type, lc, scale, deffac))
      
    dmems = []
    for id, diap_id, nids in dmem_specs:
        diap = _find_by_id(diaps, diap_id, "DIAP")
        ns = [_find_by_id(nds, nid, "NODE") for nid in nids]
        dmems.append(CSTMembrane3(id, diap, ns[0], ns[1], ns[2]))

    date_input = str(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
                     
    mdl = Mdl(
        nds, elms, ejnts, mats, secs, cons, lds, elds, alds, glds,
        lcases, lcmbs, axes, plts, date_input,
        dmats, diaps, dregs, dopns, dmems, dcons
    )

    return mdl

def RegisterInputData(_mdl: Mdl):
    
    nds  = sorted(_mdl.nds,   key=lambda n: n.id)
    elms = sorted(_mdl.elms,  key=lambda e: e.id)
    ejnts= sorted(_mdl.ejnts, key=lambda e: e.eid)
    mats = sorted(_mdl.mats,  key=lambda m: m.id)
    secs = sorted(_mdl.secs,  key=lambda s: s.id)
    dmats= sorted(_mdl.dmats, key=lambda m: m.id)
    diaps= sorted(_mdl.diaps, key=lambda d: d.id)
    dregs= list(_mdl.dregs)
    dopns= list(_mdl.dopns)
    dmems= sorted(_mdl.dmems, key=lambda m: m.id)
    dcons= list(getattr(_mdl, "dcons", []))
    cons = sorted(_mdl.cons,  key=lambda c: c.nid)

    lds_w_o_combi = [l for l in _mdl.lds if not l.combi]
    lds  = sorted(lds_w_o_combi,   key=lambda l: l.nid)

    elds_w_o_combi = [l for l in _mdl.elds if not l.combi]
    elds = sorted(elds_w_o_combi,  key=lambda l: l.eid)

    alds = sorted(_mdl.alds,  key=lambda l: l.lc)

    glds_w_o_combi = [l for l in _mdl.glds if not l.combi]
    glds = sorted(glds_w_o_combi,  key=lambda g: g.lc)

    lcases = sorted(_mdl.lcases, key=lambda l: l.lc)
    lcmbs = sorted(_mdl.lcmbs, key=lambda l: l.lc)
    axes = sorted(_mdl.axes,  key=lambda a: a.id)
    plts = sorted(_mdl.plts,  key=lambda p: p.id)
    
    lns  = ""

    ## header
    lns += "# --- HEADER INPUT ---\n"
    lns += "\n"
    lns += "# DATE OF INPUT DATA: " + _mdl.date_input 
    lns += "\n"
    lns += "# NUM. OF MATERIALS: " + str(len(mats)) + "\n"
    lns += "# NUM. OF DIAPHRAGM MATERIALS: " + str(len(dmats)) + "\n"
    lns += "# NUM. OF CROSS-SECTIONS " + str(len(secs)) + "\n" 
    lns += "# NUM. OF NODES: " + str(len(nds)) + "\n"
    lns += "# NUM. OF ELEMENTS: " + str(len(elms)) + "\n"
    lns += "# NUM. OF CONSTRAINED NODES: " + str(len(cons)) + "\n"
    lns += "# NUM. OF LOADS: " + str(len(lds)) + "\n"
    lns += "# NUM. OF ELEMENT LOADS: " + str(len(elds)) + "\n"
    lns += "\n"

    lns += "### <INPUT DATA> ### \n\n"

    ## analysis type
    lns += "# TYPE OF ANALYSIS: 3D LINEAR STATIC\n"
    lns += "\n"

    ## material
    lns += "# --- MATERIAL(MATE) ---\n"
    lns += "#         ID,       NAME,        E,        G,    Gamma,    Alpha,       Fy\n"
    lns += "#                           (N/mm2)   (N/mm2)   (kN/m3)       (-)   (N/mm2)\n"
    for m in mats:
        lns += m.OutputMatInfo()
    lns += "\n"

    ## diaphragm material
    lns += "# --- DIAPHRAGM MATERIAL(DMAT) ---\n"
    lns += "#         ID,       NAME,        Ex,        Ey,       Gxy,      Nuxy,    Gamma,    Alpha\n"
    lns += "#                           (N/mm2)   (N/mm2)   (N/mm2)       (-)  (kN/m3)       (-)\n"
    for m in dmats:
        lns += m.OutputDMatInfo()
    lns += "\n"

    ## cross section
    lns += "# --- SECTION(SECT) ---\n"
    lns += "#         ID,       NAME,    MAT,   TYPE,  DIM 1,  DIM 2,  DIM 3,  DIM 4\n"
    lns += "#                                            (mm)    (mm)    (mm)    (mm)\n"
    lns += "#       (TYPE 0: RECT., 1: CIRC., 2: I, 3: CHS, 4: RHS) \n"
    for s in secs:
        lns += s.OutputSecInfo()
    lns += "\n"

    ## node 
    lns += "# --- NODE ---\n"
    lns += "#         ID,         X,         Y,         Z,  CONST.\n"
    lns += "#                    (m)        (m)        (m)\n"
    for n in nds:
        lns += n.OutputNdInfo()
    lns += "\n"

    ## element
    lns += "# --- ELEMENT(ELEM) ---\n"
    lns += "#         ID,     Ni,     Nj,    SEC,     Beta\n"
    lns += "#                                         (deg)\n"
    for e in elms:
        lns += e.OutputElmInfo()
    lns += "\n"

    ## diaphragms and membrane elements
    lns += "# --- DIAPHRAGM REGION(DIAP) ---\n"
    lns += "#         ID,       NAME,    TYPE,     DMAT,        T,    THETA\n"
    lns += "#                                             (mm)     (deg)\n"
    for d in diaps:
        lns += d.OutputDiapInfo()
    lns += "\n"

    lns += "# --- DIAPHRAGM OUTER POLYGON(DREG) ---\n"
    lns += "#    DIAP ID,  NODE1,  NODE2,  NODE3, ...\n"
    for r in dregs:
        lns += "DREG, {0: >6}".format(r.diap_id)
        for nid in r.node_ids:
            lns += ", {0: >6}".format(nid)
        lns += "\n"
    lns += "\n"

    lns += "# --- DIAPHRAGM OPENING(DOPN) ---\n"
    lns += "#    DIAP ID,  NODE1,  NODE2,  NODE3, ...\n"
    for o in dopns:
        lns += "DOPN, {0: >6}".format(o.diap_id)
        for nid in o.node_ids:
            lns += ", {0: >6}".format(nid)
        lns += "\n"
    lns += "\n"

    lns += "# --- DIAPHRAGM MEMBRANE ELEMENT(DMEM) ---\n"
    lns += "#         ID,    DIAP,     N1,     N2,     N3\n"
    for m in dmems:
        lns += m.OutputDMemInfo()
    lns += "\n"

    lns += "# --- DIAPHRAGM CONNECTION(DCON) ---\n"
    lns += "#    DIAP ID,  TARGET,  [MEMBER ID],  TYPE,  TOL=...\n"
    for dc in dcons:
        lns += dc.OutputDConInfo()
    lns += "\n"

    ## element joints

    lns += "# --- ELEMENT JOINT(EJNT) ---\n"
    # lns += "#    ELEM ID,      Txi,      Tyi,      Tzi,      Rxi,      Ryi,      Rzi,      Txj,      Tyj,      Tzj,      Rxj,      Ryj,      Rzj\n"
    # lns += "#                (kN/m)    (kN/m)    (kN/m) (kNm/rad) (kNm/rad) (kNm/rad)    (kN/m)    (kN/m)    (kN/m) (kNm/rad) (kNm/rad) (kNm/rad)\n"
    lns += "#    ELEM ID,      Ryi,      Rzi,      Ryj,      Rzj\n"
    lns += "#             (kNm/rad) (kNm/rad) (kNm/rad) (kNm/rad)\n"
    for j in ejnts:
        lns += j.OutputElmJntInfo()
    lns += "\n"

    ## constraint
    lns += "# --- CONSTRAINT(CONS) ---\n"
    lns += "#    NODE ID,   TX,   TY,   TZ,   RX,   RY,   RZ\n"
    lns += "#   (0:FREE, 1:FIXED)\n"
    for c in cons:
        lns += c.OutputConstInfo()
    lns += "\n"

    ## load name
    lns += "# --- LOAD NAME(LNME) ---\n"
    lns += "#       LC,     NAME\n"
    for l in lcases:
        lns += l.OutputLnameInfo()
    lns += "\n"

    ## load combination
    lns += "# --- LOAD COMBINATION(LCMB) ---\n"
    lns += "#       LC,     NAME,   FC1,   LC1,   FC2,   LC2,   FC3,   LC3,...\n"
    for l in lcmbs:
        lns += l.OutputLcmbInfo()
    lns += "\n"

    ## load
    lns += "# --- POINT LOAD(PLOD) ---\n"
    lns += "#    NODE ID,   LC,     PX,     PY,     PZ,     MX,     MY,     MZ\n"
    lns += "#                      (kN)    (kN)    (kN)   (kNm)   (kNm)   (kNm)\n"
    for l in lds:
        lns += l.OutputLdInfo()
    lns += "\n"

    ## element load
    lns += "# --- ELEMENT LOAD(ELOD) ---\n"
    lns += "#    ELEM ID,   LC,  E/G,    WXi,    WYi,    WZi,    WXj,    WYj,    WZj\n"
    lns += "#                          (kN/m)  (kN/m)  (kN/m)  (kN/m)  (kN/m)  (kN/m)\n"
    lns += "#   (E/G: Element(=0) or Global(=1) Coordinate System)\n"
    for el in elds:
        lns += el.OutputELdInfo()
    
    lns += "\n"

    ## area load
    lns += "# --- AREA LOAD(ALOD) ---\n"
    lns += "#         LC,     PX,     PY,     PZ,   E1,   E2,   E3,   E4\n"
    lns += "#             (kN/m2) (kN/m2) (kN/m2)\n"
    for al in alds:
        lns += al.OutputALdInfo()
    lns += "\n"

    ## gravity load
    lns += "# --- GRAVITY LOAD(GLOD) ---\n"
    lns += "#         LC,     Vec X,     Vec Y,     Vec Z\n"
    lns += "#                 (m/s2)     (m/s2)     (m/s2)\n"
    for gl in glds:
        lns += gl.OutputGLdInfo()

    lns += "\n" 

    ## axis 
    lns += "# --- AXIS (AXIS) ---\n"
    lns += "#         ID,       NAME,    V/H,    NID,  x-DIR(if V)\n"
    lns += "#                  (V/H 0:V, 1:H)     (x-DIR 0:X, 1:Y)\n"
    for a in axes:
        lns += a.OutputAxisInfo()

    lns += "\n"

    ## plot
    lns += "# --- PLOT (PLOT) ---\n"
    lns += "#         ID,       NAME,   AXIS,   TYPE,     LC,  SCALE, DEFFAC\n"
    lns += "#             (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)\n"

    for p in plts:
        lns += p.OutputPltInfo()
    
    lns += "\n\n"

    # lns += "### <END OF INPUT DATA> ### \n\n"

    return lns

def RegisterResultData(_mdl: Mdl):

    nds  = sorted(_mdl.nds,  key=lambda n: n.id)
    elms = sorted(_mdl.elms, key=lambda e: e.id)
    #mats = sorted(_mdl.mats, key=lambda m: m.id)
    secs = sorted(_mdl.secs, key=lambda s: s.id)
    #cons = sorted(_mdl.cons, key=lambda c: c.nid)
    #lds  = sorted(_mdl.lds,  key=lambda l: l.nid)
    #elds = sorted(_mdl.elds, key=lambda l: l.eid)
    #glds = sorted(_mdl.glds, key=lambda g: g.lc)

    lcs  = sorted(_mdl.lcs)

    lns  = ""

    ## header
    # lns += "# --- HEADER ---\n"
    # lns += "\n"
    # lns += "# DATE OF ANALYSIS: " + _mdl.date_analysis 
    # lns += "\n"
    # lns += "# NUM. OF MATERIALS: " + str(len(mats)) + "\n"
    # lns += "# NUM. OF CROSS-SECTIONS " + str(len(secs)) + "\n" 
    # lns += "# NUM. OF NODES: " + str(len(nds)) + "\n"
    # lns += "# NUM. OF ELEMENTS: " + str(len(elms)) + "\n"
    # lns += "# NUM. OF CONSTRAINED NODES: " + str(len(cons)) + "\n"
    # lns += "# NUM. OF LOADS: " + str(len(lds)) + "\n"
    # lns += "# NUM. OF ELEMENT LOADS: " + str(len(elds)) + "\n"
    # lns += "\n"

    lns += "# --- HEADER OUTPUT --- \n" 
    lns += "# DATE OF ANALYSIS: " + _mdl.date_analysis + "\n\n"

    ## section properties
    lns += "# --- SECTION PROPS ---\n"
    lns += "#      SEC,          A,       Asy,       Asz,         J,        Iy,        Iz,        Wy,        Wz,        iy,        iz\n"
    lns += "#                 (mm2)      (mm2)      (mm2)      (mm4)      (mm4)      (mm4)      (mm3)      (mm3)       (mm)       (mm)\n"

    for s in secs:
        props = ["SPRP",
                 "{: >6}".format(s.id), 
                 "{:10.3e}".format(s.A * 1e6), 
                 "{:10.3e}".format(s.Asy * 1e6), 
                 "{:10.3e}".format(s.Asz * 1e6),
                 "{:10.3e}".format(s.J * 1e12),  
                 "{:10.3e}".format(s.Iy * 1e12), 
                 "{:10.3e}".format(s.Iz * 1e12), 
                 "{:10.3e}".format(s.Wy * 1e9), 
                 "{:10.3e}".format(s.Wz * 1e9), 
                 "{:10.3e}".format(s.iy * 1e3), 
                 "{:10.3e}".format(s.iz * 1e3), 
                 ]
        lns += ','.join(props) + "\n"
    
    lns += "\n"

    ## nodal displacements
    lns += "# --- NODAL DISPLACEMENT ---\n"
    lns += "#        LC,  NODE,         X,         Y,         Z,   Theta X,   Theta Y,   Theta Z\n"
    lns += "#                          (m)        (m)        (m)      (rad)      (rad)      (rad)\n"
    
    for lc in lcs:
        # lc : loadcase
        # clc: computational loadcase id 

        clc = _mdl.lcs.index(lc) 
        for n in nds: 
            ds = n.disps[:, clc]
            props = ["NDSP", 
                     "{: >6}".format(lc), 
                     "{: >6}".format(n.id), 
                     "{:10.3e}".format(ds[0]), 
                     "{:10.3e}".format(ds[1]), 
                     "{:10.3e}".format(ds[2]), 
                     "{:10.3e}".format(ds[3]), 
                     "{:10.3e}".format(ds[4]), 
                     "{:10.3e}".format(ds[5])]
            lns += ','.join(props) + "\n"

    lns += "\n"

    ## reaction forces
    lns += "# --- REACTION FORCE ---\n"
    lns += "#        LC,  NODE,        RX,        RY,        RZ,       RMX,       RMY,       RMZ\n"
    lns += "#                         (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)\n"
    
    for i in range(len(_mdl.lcs)): 
        lc   = _mdl.lcs[i]
        #csts = list(filter(lambda l: l.lc == lc, _))

        for c in _mdl.cons:
            nid   = c.nd.id
            rs    = c.nd.reacts[i] # [lc][vals]
            props = ["REAC",
                     "{: >6}".format(lc), 
                     "{: >6}".format(nid), 
                     "{:10.3e}".format(rs[0] * 1e-3),
                     "{:10.3e}".format(rs[1] * 1e-3),
                     "{:10.3e}".format(rs[2] * 1e-3),
                     "{:10.3e}".format(rs[3] * 1e-3),
                     "{:10.3e}".format(rs[4] * 1e-3),
                     "{:10.3e}".format(rs[5] * 1e-3)
                    ]

            lns += ','.join(props) + "\n"
    lns += "\n"            

    ## element forces
    lns += "# --- ELEMENT FORCE ---\n"
    # lns += "#        LC,  ELEM,        Pi,       Vyi,       Vzi,       Mxi,       Myi,       Mzi         Pj,       Vyj,       Vzj,       Mxj,       Myj,       Mzj,       Myc,       Mzc\n"
    lns += "#        LC,  ELEM,        Ni,       Qyi,       Qzi,       Mxi,       Myi,       Mzi         Nj,       Qyj,       Qzj,       Mxj,       Myj,       Mzj,       Myc,       Mzc\n"
    lns += "#                         (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)       (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)      (kNm)      (kNm)\n"
    
    for lc in lcs:
        # lc : loadcase
        # clc: computational loadcase id 

        clc = _mdl.lcs.index(lc) 
        for e in elms: 
            ef = e.forces[:, clc]

            fs = [] # forces
            for i in range(14):
                if abs(ef[i]) < common.PRES_ZERO:
                    fs.append(0)
                else:
                    fs.append(ef[i])
                    
            props = ["EFRC", 
                     "{: >6}".format(lc), 
                     "{: >6}".format(e.id), 
                     "{:10.3e}".format(fs[0] * 1e-3), 
                     "{:10.3e}".format(fs[1] * 1e-3), 
                     "{:10.3e}".format(fs[2] * 1e-3), 
                     "{:10.3e}".format(fs[3] * 1e-3), 
                     "{:10.3e}".format(fs[4] * 1e-3), 
                     "{:10.3e}".format(fs[5] * 1e-3), 
                     "{:10.3e}".format(fs[6] * 1e-3), 
                     "{:10.3e}".format(fs[7] * 1e-3), 
                     "{:10.3e}".format(fs[8] * 1e-3), 
                     "{:10.3e}".format(fs[9] * 1e-3), 
                     "{:10.3e}".format(fs[10]* 1e-3), 
                     "{:10.3e}".format(fs[11]* 1e-3), 
                     "{:10.3e}".format(fs[12]* 1e-3), 
                     "{:10.3e}".format(fs[13]* 1e-3)    ]

            lns += ','.join(props) + "\n"

    lns += "\n"

    ## membrane element strains, stresses and membrane forces
    if getattr(_mdl, "dmems", None):
        lns += "# --- MEMBRANE ELEMENT STRESS ---\n"
        lns += "#        LC,  DMEM,       EXX,       EYY,      GXY,        SX,        SY,       TXY,        NX,        NY,       NXY\n"
        lns += "#                           (-)       (-)       (-)   (N/mm2)   (N/mm2)   (N/mm2)    (kN/m)    (kN/m)    (kN/m)\n"
        for lc in lcs:
            clc = _mdl.lcs.index(lc)
            for m in _mdl.dmems:
                if m.strains is None or m.stresses is None or m.mforces is None:
                    continue
                strain = m.strains[:, clc]
                stress = m.stresses[:, clc]
                mforce = m.mforces[:, clc]
                props = [
                    "MSTR",
                    "{: >6}".format(lc),
                    "{: >6}".format(m.id),
                    "{:10.3e}".format(strain[0]),
                    "{:10.3e}".format(strain[1]),
                    "{:10.3e}".format(strain[2]),
                    "{:10.3e}".format(stress[0] * 1e-6),
                    "{:10.3e}".format(stress[1] * 1e-6),
                    "{:10.3e}".format(stress[2] * 1e-6),
                    "{:10.3e}".format(mforce[0] * 1e-3),
                    "{:10.3e}".format(mforce[1] * 1e-3),
                    "{:10.3e}".format(mforce[2] * 1e-3),
                ]
                lns += ','.join(props) + "\n"
        lns += "\n"

    return lns
