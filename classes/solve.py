import nd, elm, mat, sec, cons, common, mdl, io
from ld import PLd, ALd, ELd, Lcase, Lcmb
import copy
import numpy as np
import datetime

from scipy.sparse.linalg import spsolve
from scipy.sparse import csc_matrix

#from classes.elm import Elm1D

class Solve:

    def __init__(self, _mdl):
        
        self.mdl     = _mdl 
        self.ndof    = 6
        self.num_row = None
        self.num_lcs = None

        self.kG_orig =  None

        # solve
        self.solve()

    def solve(self):

        # register date analysis
        self.mdl.date_analysis = str(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))

        # global stiffness and load matrices before support constraints
        kG  = self.CreateGlobalStiffMX(apply_constraints=False)

        lm  = self.CreateLoadMx(apply_constraints=False)
        self.InitConstrainedReactions(lm)

        mpcs = getattr(self.mdl, "mpcs", [])
        if mpcs:
            T, reduced_dofs = self.BuildMPCTransformation()
            kG = T.T @ kG @ T
            lm = T.T @ lm
            kG, lm = self.ApplySupportConstraints(kG, lm, reduced_dofs)
        else:
            T = None
            kG, lm = self.ApplySupportConstraints(kG, lm)

        # Solve
        kG = csc_matrix(kG)
        lm = csc_matrix(lm) 
        
        x  = spsolve(kG, lm, use_umfpack=True) # scipy sparce matrix
                # x = np.linalg.solve(kG, lm)

        if T is not None:
            if np.ndim(x) == 1:
                x = T @ x
            else:
                x = T @ x
        
        self.SetNodalDisps(x) 
        self.CalcElemForces()
        self.CalcMembraneForces()
        self.CalcReactions(x)

        self.isModelSolved = True

        return

    def CalcMembraneForces(self):
        for m in getattr(self.mdl, "dmems", []):
            m.CalcResults(self.num_lcs)

        return
    
    def CalcReactions(self, _disps):

        kG_orig = self.kG_orig

        if np.ndim(_disps) == 1:
            U = np.expand_dims(_disps, axis=1)
        else:
            U = _disps.toarray()

        # KU = F
        for c in self.mdl.cons: 

            ind = c.nd.cid * self.ndof 

            for i in range(self.ndof): # each of 6 dof

                if c.csts[i] == False:

                    continue

                for j in range(self.num_lcs): # each load case 

                    f = kG_orig[ind + i] @ U[:, j]
                    c.nd.reacts[j, i] += f

        return


    @staticmethod
    def SetElemDisps(_mdl, _scale, _num_ediv): 

        elms    = _mdl.elms 
        scale   = _scale
        num_div = _num_ediv

        # if elms[0].ndisps is None: 
        #     print ("no elem disp result. Solve first.")
        #     return

        max_clc_pld  = max(list(map(lambda l: l.clc, _mdl.lds))) if _mdl.lds else 0
        max_clc_eld  = max(list(map(lambda l: l.clc, _mdl.elds))) if _mdl.elds else 0
        max_clc_gld  = max(list(map(lambda l: l.clc, _mdl.glds))) if _mdl.glds else 0
        num_lcs = max([max_clc_pld, max_clc_eld, max_clc_gld])+1 


        np.set_printoptions(precision=1, linewidth=np.inf, suppress=True, formatter={'float': '{: 0.1e}'.format})  

        # for each element
        for e in elms:

            # element's transformation matrix
            T  = e.tm

            #np.set_printoptions(precision=1, linewidth=np.inf, suppress=True, formatter={'float': '{: 0.1e}'.format})  

            # identify the both ends' nodal disps in element coordinate system
            # nd_ecs for nodal displacements in element coordinate system
            # [2 * ndof, num_lcs]

            nd_ecs = np.matmul(T, e.ndisps) # e.ndisps: GCS

            # print(f"nd_ecs=\n{nd_ecs}")

            lyi  = e.lyi       # lambda
            lyj  = e.lyj       
            lzi  = e.lzi       
            lzj  = e.lzj       
            PHIy = e.PHIy      
            PHIz = e.PHIz 

            L    = e.len

            rlyi  = 1 - lyi
            rlyj  = 1 - lyj
            rlzi  = 1 - lzi
            rlzj  = 1 - lzj

            # based on Fujii eq.(2.81)
            Av_inv_x_B = (1.0 + PHIy) / (2.0 + (2.0 + PHIy) * lzi + (2.0 + PHIy) * lzj + 4.0 * PHIy * lzi * lzj) * np.array([
                [-2.0 * rlzi * (1.0 + 2.0 * lzj) / L, (4.0 + PHIy + (2.0 + 5.0 * PHIy) * lzj) * lzi, 2.0 * rlzi * (1.0 + 2.0 * lzj) / L, -(2.0 - PHIy) * rlzi * lzj],
                [-2.0 * rlzj * (1.0 + 2.0 * lzi) / L, -(2.0 - PHIy) * rlzj * lzi, 2.0 * rlzj * (1.0 + 2.0 * lzi) / L, (4.0 + PHIy + (2.0 + 5.0 * PHIy) * lzi) * lzj]
            ])

            Aw_inv_x_B = (1.0 + PHIz) / (2.0 + (2.0 + PHIz) * lyi + (2.0 + PHIz) * lyj + 4.0 * PHIz * lyi * lyj) * np.array([
                [2.0 * rlyi * (1.0 + 2.0 * lyj) / L, (4.0 + PHIz + (2.0 + 5.0 * PHIz) * lyj) * lyi, -2.0 * rlyi * (1.0 + 2.0 * lyj) / L, -(2.0 - PHIz) * rlyi * lyj],
                [2.0 * rlyj * (1.0 + 2.0 * lyi) / L, -(2.0 - PHIz) * rlyj * lyi, -2.0 * rlyj * (1.0 + 2.0 * lyi) / L, (4.0 + PHIz + (2.0 + 5.0 * PHIz) * lyi) * lyj]
            ])

            disps = []
            # for each load case
            for i in range(num_lcs):
        
                dv = np.array([
                    [nd_ecs[ 1,  i]],
                    [nd_ecs[ 5,  i]],
                    [nd_ecs[ 7,  i]],
                    [nd_ecs[11,  i]]
                ])

                dw = np.array([
                    [nd_ecs[ 2,  i]],
                    [nd_ecs[ 4,  i]],
                    [nd_ecs[ 8,  i]],
                    [nd_ecs[10,  i]]
                ])

                theta_zp_zq = Av_inv_x_B @ dv
                theta_yp_yq = Aw_inv_x_B @ dw

                #print(f"theta_zp_zq: {theta_zp_zq}")
                #print(f"theta_yp_yq: {theta_yp_yq}")
                # need to implement edge moment Myp, Myq, Mzp, Mzq

                disp = []
                # for each division point
                for j in range(num_div + 1): 

                    # shape function: see also Kassimali 1999 pp537-538 sec 5.3 
                    
                    n  = j / num_div

                    ue = (1 - n) * nd_ecs[0, i] + n * nd_ecs[6, i]
                    
                    ve =  (1 - 3 * n ** 2 + 2 * n ** 3) * nd_ecs[1,  i] \
                    + e.len * (n - 2 * n ** 2 + n ** 3) * theta_zp_zq[0][0] \
                    +         (3 * n ** 2 - 2 * n ** 3) * nd_ecs[7,  i] \
                    + e.len * ( (-1) * n ** 2 + n ** 3) * theta_zp_zq[1][0]
                    
                    we =  (1 - 3 * n ** 2 + 2 * n ** 3) * nd_ecs[2,  i] \
                    - e.len * (n - 2 * n ** 2 + n ** 3) * theta_yp_yq[0][0] \
                    +         (3 * n ** 2 - 2 * n ** 3) * nd_ecs[8,  i] \
                    - e.len * ( (-1) * n ** 2 + n ** 3) * theta_yp_yq[1][0] 
                    
                    ug = T[0, 0] * ue + T[1, 0] * ve +  T[2, 0] * we
                    vg = T[0, 1] * ue + T[1, 1] * ve +  T[2, 1] * we
                    wg = T[0, 2] * ue + T[1, 2] * ve +  T[2, 2] * we

                    xg = (1 - n) * (e.n0.x) + n * (e.n1.x) + ug * scale
                    yg = (1 - n) * (e.n0.y) + n * (e.n1.y) + vg * scale
                    zg = (1 - n) * (e.n0.z) + n * (e.n1.z) + wg * scale

                    pnt = common.Pnt(xg, yg, zg) 
                    disp.append(pnt)

                disps.append(disp) 
            
            e.edisps = disps 

        return

    def SetNodalDisps(self, _disps):

        mdl  = self.mdl
        ndof = self.ndof

        if np.ndim(_disps) == 1:
            disps = np.expand_dims(_disps, axis=1)
        else:
            disps = _disps.toarray()
            
        cnt = 0 # loop counter
        while cnt * ndof < self.num_row:

            cid   = cnt
            s_row = cid * ndof
            e_row = s_row + ndof

            nd = mdl.FindNodeFromCid(cid) 
            nd.disps = disps[s_row:e_row, :]
  
            cnt += 1 

        return
    
    def CalcElemForces(self): 

        for e in self.mdl.elms: 

            e_disp = np.zeros((2 * self.ndof, self.num_lcs), dtype = np.float64)

            e_disp[0         :     self.ndof, : ] = e.n0.disps
            e_disp[self.ndof : 2 * self.ndof, : ] = e.n1.disps

            e.ndisps = e_disp # in Global Coorditate System

            e.forces = np.matmul(e.ek, np.matmul(e.tm, e_disp)) # 12x(num_lcs)

            if e.elds is not None: # elds are defined already with ECS
                e.forces = e.forces - e.elds

            # extend force matrix to 14x to store my_center and mz_center
            # added on 2025-01-22
            new_rows = np.zeros((2, e.forces.shape[1]), dtype = np.float64)
            e.forces = np.vstack((e.forces, new_rows))
            #
            #

            vert_bl = e.isVxZ * (e.pln.vx.v[2] > 0)
            for i in range(self.num_lcs):

                for j in range(12):
                    flip_bl = False
                    if j == 0:
                        flip_bl = True
                    if j == 1:
                        if vert_bl == 1: flip_bl = True    
                    if j == 2:
                        if vert_bl == 1: flip_bl = True
                    if j == 3: 
                        flip_bl = True
                    if j == 4:
                        if vert_bl == 1: flip_bl = True
                    if j == 5:
                        if vert_bl == 1: flip_bl = True

                    if j == 6: continue
                    if j == 7: 
                        if vert_bl == 0: flip_bl = True
                    if j == 8: 
                        if vert_bl == 0: flip_bl = True
                    if j == 9: continue
                    if j == 10: 
                        if vert_bl == 0: flip_bl = True
                    if j == 11:
                        #if vert_bl == 1: flip_bl = True 
                        flip_bl = True 

                    if flip_bl:
                        e.forces[j, i] = -e.forces[j, i]

                    # if j in [0, 3, 5, 7, 8, 10]:
                    #     # Ni', Qyi , Qzi , Mxi', Myi , Mzi'
                    #     # Nj , Qyj', Qzj', Mxj , Myj', Mzj
                    #     #forces[j] = -forces[j]
                    #     e.forces[j, i] = -e.forces[j, i]

        # adding central forces # on 2025-01-20

        elds = self.mdl.elds
        for e in self.mdl.elms:

            for i in range(len(self.mdl.lcs)): 

                lds = self.EffectiveElemLocalWLoads(e, i)

                wzi, wzj = lds[2], lds[5]
                qzi = e.forces[2][i]
                myi = e.forces[4][i]

                wyi, wyj = lds[1], lds[4]
                qyi = e.forces[1][i]
                mzi = e.forces[5][i]

                w_xc= wzi + (wzj - wzi) * 0.5 
                m_yc= myi + qzi * (0.5 * e.len) + 1.0 / 6.0 * (wzi + 2 * w_xc) * (0.5*e.len)**2 
                e.forces[12, i] = m_yc

                w_xc= wyi + (wyj - wyi) * 0.5
                m_zc= mzi - qyi * (0.5 * e.len) - 1.0 / 6.0 * (wyi + 2 * w_xc) * (0.5*e.len)**2 
                e.forces[13, i] = m_zc

                # print(f"lc: {self.mdl.lcs[i]}, e.id: {e.id}, m_yi: {myi}, m_yc: {m_yc}, m_zi: {mzi}, m_zc: {m_zc}")
        
        ###

        return

    def EffectiveElemLocalWLoads(self, _e, _lc_idx):
        """Element local distributed loads after diaphragm boundary transfer."""

        lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)

        for el in self.mdl.elds:
            if (el.clc != _lc_idx) or (el.eid != _e.id):
                continue
            el_lds = np.array(el.lds, dtype=np.float64).reshape(6, 1)
            if el.isGlobal == True:
                el_lds = _e.tm[0:6, 0:6] @ el_lds
            lds += el_lds.reshape(6)

        if _e.glds is not None and _lc_idx < _e.glds.shape[1]:
            lds += _e.glds[:, _lc_idx]

        if _e.alds is not None and _lc_idx < _e.alds.shape[1]:
            lds += _e.alds[:, _lc_idx]

        if self._connected_boundary_assoc(_e) is not None:
            # The in-plane transverse member load is carried by the diaphragm.
            # Keep axial and vertical components on the member.
            lds[1] = 0.0
            lds[4] = 0.0

        return lds
    
    def InitConstrainedReactions(self, _lm):

        for c in self.mdl.cons:
            reacts = np.zeros((self.num_lcs, self.ndof))
            ind = c.nd.cid * self.ndof
            for i in range(self.ndof):
                if c.csts[i] == False:
                    continue
                for j in range(self.num_lcs):
                    reacts[j, i] = -1 * _lm[ind + i, j]
            c.nd.reacts = reacts

        return

    def ApplySupportConstraints(self, _kG, _lm, _reduced_dofs=None):

        kG = _kG
        lm = _lm
        row_map = None
        if _reduced_dofs is not None:
            row_map = {dof: i for i, dof in enumerate(_reduced_dofs)}

        for c in self.mdl.cons:
            ind = c.nd.cid * self.ndof

            for i in range(self.ndof):
                if c.csts[i] == False:
                    continue

                full_dof = ind + i
                if row_map is None:
                    row = full_dof
                else:
                    row = row_map.get(full_dof)
                    if row is None:
                        continue

                for j in range(kG.shape[0]):
                    if row == j:
                        kG[row, j] = 1
                    else:
                        kG[row, j] = 0
                        kG[j, row] = 0
                lm[row, :] = 0

        return kG, lm

    def BuildMPCTransformation(self):

        mpcs = getattr(self.mdl, "mpcs", [])
        slave_dofs = set([m.slave_dof for m in mpcs])
        reduced_dofs = [i for i in range(self.num_row) if i not in slave_dofs]
        reduced_index = {dof: i for i, dof in enumerate(reduced_dofs)}

        T = np.zeros((self.num_row, len(reduced_dofs)), dtype=np.float64)
        for dof in reduced_dofs:
            T[dof, reduced_index[dof]] = 1.0

        for m in mpcs:
            if abs(getattr(m, "constant_term", 0.0)) > common.PRES_ZERO:
                raise ValueError("MPC constant terms are not supported yet")
            if m.slave_dof not in slave_dofs:
                continue
            for mdof, coeff in zip(m.master_dofs, m.coefficients):
                if mdof in slave_dofs:
                    raise ValueError("Nested MPC master DOF is not supported")
                ridx = reduced_index.get(mdof)
                if ridx is None:
                    continue
                T[m.slave_dof, ridx] += coeff

        return T, reduced_dofs

    def CreateGlobalStiffMX(self, apply_constraints=True):

        mdl   = self.mdl
        ndof  = self.ndof 
 
        nsize = len(mdl.nds)
        self.num_row = ndof * nsize

        kG = np.zeros((self.num_row, self.num_row), dtype = np.float64)
        for e in mdl.elms:

            sid = ndof * e.n0.cid
            eid = ndof * e.n1.cid

            for i in range(ndof):

                for j in range(ndof):
                    
                    kG[sid + i, sid + j] += e.ekG[i       , j]          # K11' part of Aoyama
                    kG[sid + i, eid + j] += e.ekG[i       , ndof + j]   # K12'
                    kG[eid + i, sid + j] += e.ekG[ndof + i, j]          # K21'
                    kG[eid + i, eid + j] += e.ekG[ndof + i, ndof + j]   # K22'

        for m in getattr(mdl, "dmems", []):
            nodes = [m.n0, m.n1, m.n2]
            dofs = []
            for n in nodes:
                base = ndof * n.cid
                dofs += [base, base + 1, base + 2]

            for i in range(9):
                for j in range(9):
                    kG[dofs[i], dofs[j]] += m.ekG[i, j]

        for w in getattr(mdl, "wshears", []):
            dof = w.dof()
            nodes = w.nodes()
            ws = w.stiffness_weights()
            for i in range(4):
                ri = ndof * nodes[i].cid + dof
                for j in range(4):
                    rj = ndof * nodes[j].cid + dof
                    kG[ri, rj] += w.k * ws[i] * ws[j]

        self.kG_orig = kG.copy() # this is for calculating reactions later.

        # apply constraints
        if apply_constraints:
            kG, _ = self.ApplySupportConstraints(
                kG, np.zeros((self.num_row, max(self.num_lcs or 1, 1)), dtype=np.float64)
            )

        return kG
    
    def CreateLoadMx(self, apply_constraints=True):

        # max_clc_pld  = max(list(map(lambda l: l.clc, self.mdl.lds))) if self.mdl.lds else 0
        # max_clc_eld  = max(list(map(lambda l: l.clc, self.mdl.elds))) if self.mdl.elds else 0
        # max_clc_gld  = max(list(map(lambda l: l.clc, self.mdl.glds))) if self.mdl.glds else 0
        # max_clc_ald  = max(list(map(lambda l: l.clc, self.mdl.alds))) if self.mdl.alds else 0
        # self.num_lcs = max([max_clc_pld, max_clc_eld, max_clc_gld, max_clc_ald])+1 

        self.num_lcs = self.mdl.max_clc

        #
        # Area loads (ALOD) -- tributary-area method.
        #
        # The panel pressure is distributed to its boundary members as an
        # equivalent linearly-varying member load that reproduces the exact
        # tributary resultant and its centroid (hence exact global equilibrium
        # and reactions), including the member-axial pressure component.
        # The equivalent intensities are accumulated in e.alds (ECS, N/m) and
        # the corresponding consistent fixed-end forces in e.elds (ECS).
        #
        for al in self.mdl.alds:

            col  = al.clc # should have been set at mdl
            elms = al.elms

            if elms is None:
                continue

            for idx, e in enumerate(elms):

                area = al.elms_areas[idx]  # tributary area [m^2]
                dc   = al.elms_dc[idx]     # centroid distance [m] from e.n0
                L    = e.len

                if area <= 0.0 or L <= 0.0:
                    continue

                # pressure vector in ECS [N/m^2]
                p_ecs = e.tm[0:3, 0:3] @ np.array(al.lds)

                # equivalent linear tributary width [m] at the two ends so that
                #   integral(w) = area, centroid(w) = dc
                S  = 2.0 * area / L
                wi = S * (2.0 - 3.0 * dc / L)
                wj = S * (3.0 * dc / L - 1.0)

                # ECS line-load intensities [N/m] at i (n0) and j (n1)
                wxi, wyi, wzi = wi * p_ecs
                wxj, wyj, wzj = wj * p_ecs

                # consistent fixed-end forces for a linearly-varying load (ECS),
                # same convention as ELOD/gravity (axial included).
                fwe = np.zeros((self.ndof * 2, 1), dtype=np.float64)
                fwe[ 0] =  L / 6.0  * (2.0 * wxi + 1.0 * wxj)       # fxi
                fwe[ 1] =  L / 20.0 * (7.0 * wyi + 3.0 * wyj)       # fyi
                fwe[ 2] =  L / 20.0 * (7.0 * wzi + 3.0 * wzj)       # fzi
                fwe[ 3] =  0.0                                      # mxi
                fwe[ 4] = -L**2 / 60.0 * (3.0 * wzi + 2.0 * wzj)    # myi
                fwe[ 5] =  L**2 / 60.0 * (3.0 * wyi + 2.0 * wyj)    # mzi

                fwe[ 6] =  L / 6.0  * (1.0 * wxi + 2.0 * wxj)       # fxj
                fwe[ 7] =  L / 20.0 * (3.0 * wyi + 7.0 * wyj)       # fyj
                fwe[ 8] =  L / 20.0 * (3.0 * wzi + 7.0 * wzj)       # fzj
                fwe[ 9] =  0.0                                      # mxj
                fwe[10] =  L**2 / 60.0 * (2.0 * wzi + 3.0 * wzj)    # myj
                fwe[11] = -L**2 / 60.0 * (2.0 * wyi + 3.0 * wyj)    # mzj

                if e.elds is None:
                    e.elds = np.zeros((self.ndof * 2, self.num_lcs), dtype=np.float64)
                e.elds[:, col] += fwe.reshape(-1)  ### ECS

                if e.alds is None:
                    e.alds = np.zeros((6, self.num_lcs), dtype=np.float64)
                e.alds[:, col] += np.array([wxi, wyi, wzi, wxj, wyj, wzj])  ### ECS

        nr= self.num_row  # self.num_row = ndof * nsize @ stiffness matrix
        lm = np.zeros((nr, self.num_lcs), dtype = np.float64)

        #
        # for point load
        #
        for l in self.mdl.lds:

            row = l.nd.cid * self.ndof
            col = l.clc

            for i in range(self.ndof): 

                ld = l.lds[i]           
                lm[row + i, col] += ld

        self.AddDiaphragmLoads(lm)

        #
        # for element load
        #
        for el in self.mdl.elds:

            fwe     = np.zeros((self.ndof*2, 1), dtype = np.float64)

            col     = el.clc
            e       = el.elm
            lds     = el.lds # self.lds = [_wxi, _wyi, _wzi, _wxj, _wyj, _wzj]

            if el.isGlobal == True:
                lds = e.tm[0:6, 0:6] @ np.array(lds) 
            else: 
                lds = np.array(lds)

            # all lds are now in ECS
            fwe[ 0] =  0.0                                                # fxi
            fwe[ 1] =  e.len / 20.0 * (7.0 * lds[1] + 3.0 * lds[4])       # fyi
            fwe[ 2] =  e.len / 20.0 * (7.0 * lds[2] + 3.0 * lds[5])       # fzi
            fwe[ 3] =  0.0                                                # mxi
            fwe[ 4] = -e.len**2 / 60.0 * (3.0 * lds[2] + 2.0 * lds[5]) #+ # myi
            fwe[ 5] =  e.len**2 / 60.0 * (3.0 * lds[1] + 2.0 * lds[4])    # mzi -

            fwe[ 6] =  0.0                                                # fxj
            fwe[ 7] =  e.len / 20.0 * (3.0 * lds[1] + 7.0 * lds[4])       # fyj
            fwe[ 8] =  e.len / 20.0 * (3.0 * lds[2] + 7.0 * lds[5])       # fzj
            fwe[ 9] =  0.0                                                # mxj
            fwe[10] =  e.len**2 / 60.0 * (2.0 * lds[2] + 3.0 * lds[5]) #- # myj
            fwe[11] = -e.len**2 / 60.0 * (2.0 * lds[1] + 3.0 * lds[4])    # mzj +
            
            if e.elds is None:
                e.elds = np.zeros((self.ndof*2, self.num_lcs), dtype = np.float64)
            e.elds[:, col] += fwe.reshape(-1)  ### ECS 
        
        #
        # Gravity loads
        #
        for g in self.mdl.glds:

            col = g.clc

            for e in self.mdl.elms: 
                # m = e.sec.A * e.len * e.sec.mat.gamma / common.GRAVITY # [kg] 
                m = e.sec.A * e.sec.mat.gamma / common.GRAVITY # [kg/m] 
                lds = e.tm[0:6, 0:6] @ np.array([m*g.gx, m*g.gy, m*g.gz, m*g.gx, m*g.gy, m*g.gz])

                #print(f"e.id: {e.id}, mg_array: {[m*g.gx, m*g.gy, m*g.gz, m*g.gx, m*g.gy, m*g.gz]}")
                #print(f"e.id: {e.id}, lds: {lds}, clc: {g.clc}")

                fwe     =  np.zeros((self.ndof*2, 1), dtype = np.float64)
                
                # all lds are now in ECS
                fwe[ 0] =  e.len / 6.0  * (2.0 * lds[0] + 1.0 * lds[3])       # fxi
                fwe[ 1] =  e.len / 20.0 * (7.0 * lds[1] + 3.0 * lds[4])       # fyi
                fwe[ 2] =  e.len / 20.0 * (7.0 * lds[2] + 3.0 * lds[5])       # fzi
                fwe[ 3] =  0.0                                                # mxi
                fwe[ 4] = -e.len**2 / 60.0 * (3.0 * lds[2] + 2.0 * lds[5]) #+ # myi
                fwe[ 5] =  e.len**2 / 60.0 * (3.0 * lds[1] + 2.0 * lds[4])    # mzi -

                fwe[ 6] =  e.len / 6.0  * (1.0 * lds[0] + 2.0 * lds[3])       # fxj
                fwe[ 7] =  e.len / 20.0 * (3.0 * lds[1] + 7.0 * lds[4])       # fyj
                fwe[ 8] =  e.len / 20.0 * (3.0 * lds[2] + 7.0 * lds[5])       # fzj
                fwe[ 9] =  0.0                                                # mxj
                fwe[10] =  e.len**2 / 60.0 * (2.0 * lds[2] + 3.0 * lds[5]) #- # myj
                fwe[11] = -e.len**2 / 60.0 * (2.0 * lds[1] + 3.0 * lds[4])    # mzj +

                if e.elds is None:
                    e.elds = np.zeros((self.ndof*2, self.num_lcs), dtype = np.float64)
                
                e.elds[:, col] += fwe.reshape(-1)  ### ECS 

                if e.glds is None:
                    e.glds = np.zeros((6, self.num_lcs), dtype = np.float64)
                
                e.glds[:, col] += lds  ### ECS 

                # print(f"elem {e.id} lds: \n {lds}")
                # print(f"elem {e.id} fwe: \n {fwe}")
                
        for e in self.mdl.elms:

            if e.elds is None: continue 

            for i in range(2):
                
                if i==0:
                    row = e.n0.cid * self.ndof
                    f = e.elds[:self.ndof, :] 
                else:
                    row = e.n1.cid * self.ndof
                    f = e.elds[self.ndof:2*self.ndof, :]

                f_gcs = e.tm[0:6, 0:6].T @ f
                self.RedirectConnectedBoundaryMemberLoads(e, i, f, f_gcs, lm)
                lm[row:row+self.ndof, :] += f_gcs
            
            #print(f"e.elds: \n{e.elds}")

        if apply_constraints:
            self.InitConstrainedReactions(lm)
            _, lm = self.ApplySupportConstraints(
                np.eye(self.num_row, dtype=np.float64), lm
            )

        return lm

    def AddDiaphragmLoads(self, lm):
        by_diap = {d.id: d for d in getattr(self.mdl, "diaps", [])}
        by_node = {n.id: n for n in getattr(self.mdl, "nds", [])}
        for dl in getattr(self.mdl, "dloads", []):
            col = dl.clc
            if col is None:
                continue
            if dl.load_type == "AREA":
                for node, fx, fy in self._diaphragm_area_nodal_loads(dl, by_diap):
                    self._add_xy_load(lm, node, col, fx, fy)
            elif dl.load_type == "LINE":
                if len(dl.node_ids) < 2:
                    continue
                n0 = by_node.get(dl.node_ids[0])
                n1 = by_node.get(dl.node_ids[1])
                if n0 is None or n1 is None:
                    continue
                L = math.sqrt((n1.x - n0.x) ** 2 + (n1.y - n0.y) ** 2 + (n1.z - n0.z) ** 2)
                fx = dl.px * L * 0.5
                fy = dl.py * L * 0.5
                self._add_xy_load(lm, n0, col, fx, fy)
                self._add_xy_load(lm, n1, col, fx, fy)
            elif dl.load_type in ["MASS", "WEIGHT"]:
                px = dl.mass * dl.ax + dl.weight / common.GRAVITY * dl.ax
                py = dl.mass * dl.ay + dl.weight / common.GRAVITY * dl.ay
                if abs(px) < common.PRES_ZERO and abs(py) < common.PRES_ZERO:
                    continue
                mass_load = copy.copy(dl)
                mass_load.px = px
                mass_load.py = py
                for node, fx, fy in self._diaphragm_area_nodal_loads(mass_load, by_diap):
                    self._add_xy_load(lm, node, col, fx, fy)

    def _add_xy_load(self, lm, node, col, fx, fy):
        row = node.cid * self.ndof
        lm[row + 0, col] += fx
        lm[row + 1, col] += fy

    def _diaphragm_area_nodal_loads(self, dl, by_diap):
        diap = by_diap.get(dl.diap_id)
        if diap is None:
            return []

        loads = []
        dmems = [m for m in getattr(self.mdl, "dmems", []) if m.diap.id == dl.diap_id]
        if dmems:
            for m in dmems:
                f = m.area / 3.0
                for n in [m.n0, m.n1, m.n2]:
                    loads.append((n, dl.px * f, dl.py * f))
            return loads

        for reg in getattr(self.mdl, "dregs", []):
            if reg.diap_id != dl.diap_id:
                continue
            nodes = []
            for nid in reg.node_ids:
                n = self.mdl.FindNodeFromId(nid)
                if n != -1:
                    nodes.append(n)
            if len(nodes) < 3:
                continue
            area = 0.0
            for i in range(len(nodes)):
                n0 = nodes[i]
                n1 = nodes[(i + 1) % len(nodes)]
                area += n0.x * n1.y - n0.y * n1.x
            area = abs(area) * 0.5
            if area <= common.PRES_ZERO:
                continue
            f = area / float(len(nodes))
            for n in nodes:
                loads.append((n, dl.px * f, dl.py * f))
        return loads

    def _connected_boundary_assoc(self, _e):
        for a in getattr(self.mdl, "dassocs", []):
            if a.member_id != _e.id:
                continue
            if a.connection_type != "CONNECTED_RIGID":
                continue
            if a.association_type != "boundary_member":
                continue
            return a
        return None

    def RedirectConnectedBoundaryMemberLoads(self, _e, _end_index, _f_ecs, _f_gcs, _lm):
        """For connected boundary members, transfer horizontal line-load resultants
        from member end DOFs to diaphragm host nodes.

        This suppresses spurious weak-axis beam bending due façade/wind line loads
        when the diaphragm tie is intended to carry the in-plane action.
        """

        assoc = self._connected_boundary_assoc(_e)
        if assoc is None:
            return

        end_node = _e.n0 if _end_index == 0 else _e.n1
        cp = None
        for p in assoc.generated_constraint_points:
            if getattr(p, "target_node", None) is end_node:
                cp = p
                break
        if cp is None:
            return

        # Transfer only horizontal force components (global ux, uy).
        transferred = False
        for dof in [0, 1]:
            vals = _f_gcs[dof, :].copy()
            if np.max(np.abs(vals)) < common.PRES_ZERO:
                continue

            for n, w in zip(cp.host_nodes, cp.shape_function_weights):
                if abs(w) < common.PRES_ZERO:
                    continue
                host_row = n.cid * self.ndof + dof
                _lm[host_row, :] += w * vals

            _f_gcs[dof, :] = 0.0
            transferred = True

        if not transferred:
            return

        # Drop global Rz nodal couple from redirected horizontal line loads.
        # This is an MVP approximation to avoid keeping weak-axis member bending
        # while in-plane forces are redirected to diaphragm nodes.
        _f_gcs[5, :] = 0.0
        # Also drop associated local weak-axis force/moment components so
        # member-force postprocessing does not retain redirected load effects.
        _f_ecs[1, :] = 0.0
        _f_ecs[5, :] = 0.0