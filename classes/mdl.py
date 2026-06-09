from cons import Cons
import numpy as np
import copy

from ejnt import EJnt
from axis import Axis
import ld
import common
import math
from diaphragm import build_diaphragm_mpcs
class Mdl:

    def __init__(self, 
                 _nds   = None, 
                 _elms  = None, 
                 _ejnts = None, 
                 _mats  = None, 
                 _secs  = None, 
                 _cons  = None, 
                 _lds   = None,
                 _elds  = None,
                 _alds  = None,
                 _glds  = None,
                 _lcases= None,
                 _lcmbs = None,
                 _axes  = None,  
                 _plts  = None,
                 _date_i= None,
                 _dmats = None,
                 _diaps = None,
                 _dregs = None,
                 _dopns = None,
                 _dmems = None,
                 _dcons = None,
                 _dloads = None,
                 _wwalls = None,
                 _wshears = None):

        self.nds        = _nds
        self.elms       = _elms
        self.ejnts      = _ejnts
        self.mats       = _mats
        self.secs       = _secs
        self.cons       = _cons
        #self.inilds     = _lds
        self.lds        = _lds #.copy()
        self.elds       = _elds
        self.glds       = _glds
        self.axes       = _axes
        self.plts       = _plts
        self.lcases     = _lcases # added 250104
        self.lcmbs      = _lcmbs  # added 250104
        self.alds       = _alds   # added 250113
        self.dmats      = _dmats if _dmats is not None else []
        self.diaps      = _diaps if _diaps is not None else []
        self.dregs      = _dregs if _dregs is not None else []
        self.dopns      = _dopns if _dopns is not None else []
        self.dmems      = _dmems if _dmems is not None else []
        self.dcons      = _dcons if _dcons is not None else []
        self.dloads     = _dloads if _dloads is not None else []
        self.wwalls     = _wwalls if _wwalls is not None else []
        self.wshears    = _wshears if _wshears is not None else []
        self.dassocs    = []
        self.mpcs       = []
        self.lcs        =  None
        self.bounds     =  None
        self.max_clc    =  0      # added 250125

        self.date_input    = _date_i
        self.date_analysis = None
        self.filepath   =  None

        # assign element joints to elements
        self.AssignElemJoints()
        self.CalcElemMatrices()

        # create combined loads & area loads
        self.CreateCombinedLoads()

        # asssign "computational ids" to nd, elm, mat, sec, lds
        self.AssignCompIds()

        # find node and register for each constraint
        self.FindNodeForCons()
        self.FindNodeElmForLd()

        # find elements for each area load
        self.FindElmsForAld()

        self.BuildDiaphragmConnections()

        self.SetBounds()

        self.SetPlnToAxis()

        return

    def BuildDiaphragmConnections(self):
        build_diaphragm_mpcs(self)

        return
    
    def FindElmsForAld(self):

        for al in self.alds:
            al.elms = list(filter(lambda e: e.id in al.eids, self.elms)) 
            al.SetMemberAreaLoads()

        return
    
    def CreateCombinedLoads(self):

        # create combined loads and area loads

        for c in self.lcmbs:
            #print(f"c.lc: {c.lc}, c.name: {c.name}, c.fcs: {c.fcs}, c.lcs: {c.lcs}")
            for i in range(len(c.fcs)):
                factor = c.fcs[i]
                lc = c.lcs[i]
                # pld, eld, gld
                # find all lds with lc
                relevant_plds = list(filter(lambda ld: ld.lc == lc, self.lds))
                relevant_elds = list(filter(lambda el: el.lc == lc, self.elds))
                relevant_glds = list(filter(lambda gl: gl.lc == lc, self.glds))
                relevant_alds = list(filter(lambda al: al.lc == lc, self.alds))
                relevant_dloads = list(filter(lambda dl: dl.lc == lc, self.dloads))
                relevant_lds = relevant_plds + relevant_elds + relevant_glds + relevant_alds + relevant_dloads

                # print(f"self.lds: {[l.id for l in self.lds]}")
                # create combined load
                for l in relevant_lds:
                    newld = copy.deepcopy(l)
                    newld.combi = True
                    newld.lc = c.lc

                    if type(l) == ld.PLd:
                        newld.lds = [factor * e for e in newld.lds]
                        #print(f"type(newld.pv) before amplify: {type(newld.pv)}")
                        newld.pv = common.Vec.amplify(newld.pv, factor)
                        #print(f"type(newld.pv) after amplify: {type(newld.pv)}")
                        newld.mv = common.Vec.amplify(newld.mv, factor)
                        self.lds.append(newld)

                    elif type(l) == ld.ELd:
                        newld.lds = [factor * e for e in newld.lds]
                        newld.len = math.sqrt(
                            max([abs(newld.lds[0]), abs(newld.lds[3])])**2 + 
                            max([abs(newld.lds[1]), abs(newld.lds[4])])**2 + 
                            max([abs(newld.lds[2]), abs(newld.lds[5])])**2
                        )
                        self.elds.append(newld)

                    elif type(l) == ld.GLd:
                        newld.gx = factor * newld.gx
                        newld.gy = factor * newld.gy
                        newld.gz = factor * newld.gz
                        self.glds.append(newld)

                    elif type(l) == ld.ALd:
                        newld.lds = [factor * e for e in newld.lds]
                        newld.elms = None
                        newld.elms_areas = None
                        newld.elms_dc = None
                        newld.elms_b0 = None
                        newld.elms_b1 = None
                        newld.elms_t = None
                        newld.elms_b = None
                        self.alds.append(newld)

                    elif type(l).__name__ == "DiaphragmLoad":
                        newld.px *= factor
                        newld.py *= factor
                        newld.mass *= factor
                        newld.weight *= factor
                        self.dloads.append(newld)

        # # create area loads

        # for al in self.alds:

        #     nds = []
        #     for eid in al.eids:
        #         elm = self.FindElemFromEid(eid)
        #         el_nds = [elm.n0, elm.n1]

        #         for e_nd in el_nds:
        #             if e_nd not in nds:
        #                 nds.append(e_nd)
            
        #     pts = [[nd.x, nd.y, nd.z] for nd in nds]
        #     print(f"pts: {pts}")

        #     # create area load
        #     #for elm in relevant_elms:
        #     #    elm.ald = al
                    
        return

    def SetPlnToAxis(self):

        for a in self.axes:

            a.pln = Axis.CalcPln(a, self)

        return

    def AssignElemJoints(self):
    
        jnts = self.ejnts

        for j in jnts:

            e = self.FindElemFromEid(j.eid) 

            if j.ryi == None:   j.Ryi = e.sec.mat.E * e.sec.Iy 
            else:               j.Ryi = j.ryi * e.len
            if j.rzi == None:   j.Rzi = e.sec.mat.E * e.sec.Iz 
            else:               j.Rzi = j.ryi * e.len

            if j.ryj == None:   j.Ryj = e.sec.mat.E * e.sec.Iy 
            else:               j.Ryj = j.ryj * e.len
            if j.rzj == None:   j.Rzj = e.sec.mat.E * e.sec.Iz
            else:               j.Rzj = j.rzj * e.len

            e.jnt = j

        self.FillElemJoints()

        return
    
    def FillElemJoints(self):

        elms = self.elms
        # rigidjnts =  [1e20] * 12
        rigidjnts =  [None] * 4

        for e in elms:

            if e.jnt == None: 
                
                e.jnt = EJnt(e.id, rigidjnts)

                e.jnt.Ryi = e.sec.mat.E * e.sec.Iy 
                e.jnt.Rzi = e.sec.mat.E * e.sec.Iz 
                e.jnt.Ryj = e.sec.mat.E * e.sec.Iy 
                e.jnt.Rzj = e.sec.mat.E * e.sec.Iz 

        return
    
    def CalcElemMatrices(self):

        for e in self.elms:

            e.ek  = e.ElmStiffMX()
            e.tm  = e.ElmTransMX()
            e.ekG = np.matmul(np.matmul(e.tm.T, e.ek), e.tm)


        return
    
    def AssignCompIds(self):

        #nd
        cid = 0
        for n in self.nds:
            n.cid = cid
            cid += 1

        #elm
        cid = 0
        for e in self.elms:
            e.cid = cid
            cid += 1

        #pld
        self.max_clc = 0
        lcs = []
        for l in self.lds:
            if l.lc not in lcs:
                lcs.append(l.lc)
                l.clc = self.max_clc
                self.max_clc += 1
            else:
                l.clc = lcs.index(l.lc)
        
        #eld
        for el in self.elds:
            if el.lc not in lcs:
                lcs.append(el.lc)
                el.clc = self.max_clc
                self.max_clc += 1
            else:
                el.clc = lcs.index(el.lc)
        
        #gld
        for gl in self.glds:
            if gl.lc not in lcs:
                lcs.append(gl.lc)
                gl.clc = self.max_clc
                self.max_clc += 1
            else:
                gl.clc = lcs.index(gl.lc)

        #ald
        for al in self.alds:
            if al.lc not in lcs:
                lcs.append(al.lc)
                al.clc = self.max_clc
                self.max_clc += 1
            else:
                al.clc = lcs.index(al.lc)

        # diaphragm loads
        for dl in self.dloads:
            if dl.lc not in lcs:
                lcs.append(dl.lc)
                dl.clc = self.max_clc
                self.max_clc += 1
            else:
                dl.clc = lcs.index(dl.lc)

        # diaphragm materials, regions and membrane elements
        cid = 0
        for dm in self.dmats:
            dm.cid = cid
            cid += 1

        cid = 0
        for d in self.diaps:
            d.cid = cid
            cid += 1

        cid = 0
        for m in self.dmems:
            m.cid = cid
            cid += 1
        
        self.lcs = lcs

        return

    def FindNodeFromId(self, _id):

        nd = list(filter(lambda n: n.id == _id, self.nds))
        if nd:
            return nd[0]
        else:
            return -1
    
    def FindNodeFromCid(self, _cid):

        nd = list(filter(lambda n: n.cid == _cid, self.nds))
        if nd:
            return nd[0]
        else:
            return -1

    def FindElemFromEid(self, _eid):

        elm = list(filter(lambda e: e.id == _eid, self.elms))
        if elm:
            return elm[0]
        else:
            return -1
    
    def FindNodeForCons(self):

        nds = self.nds
        cons = self.cons

        for c in cons:
            c.FindNd(nds)

        return
    
    def FindNodeElmForLd(self):

        nds = self.nds
        lds = self.lds

        for l in lds:
            l.FindNd(nds)

        elms = self.elms
        elds = self.elds

        for el in elds:
            el.FindElm(elms)

        return
    
    def SetBounds(self):

        pts = list(map(lambda n: (n.x, n.y, n.z), self.nds))
        self.bounds = common.CalcBounds(pts)

        return

    def ResetStrData(self): 

        self.nds  = []
        self.elms = []
        self.dmems = []
        self.dmats = []
        self.diaps = []
        self.dregs = []
        self.dopns = []
        self.dcons = []
        self.dloads = []
        self.wwalls = []
        self.wshears = []
        self.dassocs = []
        self.mpcs = []
        self.mats = []
        self.secs = []
        self.cons = []
        self.lds  = []

        return
    