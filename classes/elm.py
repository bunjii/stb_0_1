import numpy as np
import math

import vedo

import common

from nd   import Nd
from mat  import Mat
from sec  import Sec
from ejnt import EJnt

class Elm1D:

    def __init__(self, 
                 _id, 
                 _n0, 
                 _n1, 
                 _sec, 
                 _theta,
                 _bucklen: float = None):
        
        self.id      = _id
        self.n0      = _n0 # node class instance
        self.n1      = _n1 # node class instance
        self.sec     = _sec
        self.theta   = _theta # in degree
        self.jnt     =  None
        
        # self.vecz    =  Elm1D.CalcVecZ(_vecz)
        self.bucklen = _bucklen

        self.pln     =  None
        self.len     =  self.CalcLen()
        self.weight  =  self.CalcWeight()
        self.beta    =  self.CalcBeta()
        # self.pln   is set in CalcBeta()
        # self.isVxZ is set in CalcBeta()

        self.ek      =  None # self.ElmStiffMX()
        self.tm      =  None # self.ElmTransMX()
        self.sub_tm1 =  None
        self.sub_tm2 =  None
        self.ekG     =  None # np.matmul(np.matmul(self.tm.T, self.ek), self.tm)
        
        self.ndisps  =  None # nodal displacements
        self.edisps  =  None 
        self.forces  =  None
        # self.elds    =  None # element forces defined in GCS
        self.elds    =  None # element forces defined in ECS 
        self.glds    =  None
        self.alds    =  None # added on 2025-01-19

        self.cy      =  None
        self.cz      =  None
        self.lyi     =  None
        self.lyj     =  None
        self.lzi     =  None
        self.lzj     =  None
        self.PHIy    =  None
        self.PHIz    =  None

    def CalcLen(self):

        len = self.n0.DistanceTo(self.n1)

        return len
    
    def CalcWeight(self):

        a = self.sec.A          
        v = self.len * a        
        d = self.sec.mat.gamma  

        w = v*d                 

        return w 
    
    def CalcBeta(self):

        X = np.array([1.0, 0.0, 0.0])
        Y = np.array([0.0, 1.0, 0.0])
        Z = np.array([0.0, 0.0, 1.0])

        n0 = np.array([self.n0.x, self.n0.y, self.n0.z])
        n1 = np.array([self.n1.x, self.n1.y, self.n1.z])

        vx = n1 - n0
        vx = vx / np.linalg.norm(vx) # normalised
        theta_rad = np.radians(self.theta)

        self.isVxZ = False
        angle = Elm1D.CalcAngle(vx, Z) 

        if (abs(angle) < common.PRES_ANGLE) or (abs(angle - math.pi) < common.PRES_ANGLE): 
            self.isVxZ = True
            #print("isVxZ True")
        
        # parallel to Z-axis 
        if self.isVxZ:

            if abs(angle - math.pi) < common.PRES_ANGLE:
                alpha = 0.5 * math.pi
            else:
                alpha =-0.5 * math.pi

            #vz   = X 
            vy   = X * np.cos(theta_rad + alpha) + np.cross(vx, X) * np.sin(theta_rad + alpha) + vx * np.dot(vx, X) * (1 - np.cos(theta_rad + alpha))
            vz   = np.cross(vx, vy)
            vz   = vz / np.linalg.norm(vz)
            beta = theta_rad + alpha
            
        # not parallel to Z-axis
        else: 

            vy   = np.cross(Z, vx)
            vy   = vy / np.linalg.norm(vy) 
            vy   = vy * np.cos(theta_rad) + np.cross(vx, vy) * np.sin(theta_rad) + vx * np.dot(vx, vy) * (1 - np.cos(theta_rad))
            vz   = np.cross(vx, vy) 
            vz   = vz / np.linalg.norm(vz)
            beta = theta_rad
        
        # plane 
        #print(f"vx:{vx}, vy:{vy}, vz:{vz}")
        self.pln = common.Plane(self.n0, vx, vy, vz)
        #print(f"elemid: {self.id}, beta= {math.degrees(beta)}")
        return beta
    
    @staticmethod
    def CalcAngle(_v1: np.array, _v2: np.array):
        
        dp = np.dot(_v1, _v2) / ( np.linalg.norm(_v1) * np.linalg.norm(_v2)) 
        a  = np.arccos(dp)                            # in radian

        return a
    
    def ElmTransMX(self):

        tm      = np.zeros((12, 12), dtype = np.float64) 
        sub_tm  = np.zeros(( 3,  3), dtype = np.float64)
        sub_tm1 = np.zeros(( 3,  3), dtype = np.float64)
        sub_tm2 = np.zeros(( 3,  3), dtype = np.float64)

        l       = (self.n1.x - self.n0.x) / self.len
        m       = (self.n1.y - self.n0.y) / self.len
        n       = (self.n1.z - self.n0.z) / self.len
        lm      = math.sqrt(l**2 + m**2)

        #print(f"self.beta = {self.beta}")

        sub_tm1[0, 0] =  1.0
        sub_tm1[1, 1] =  1.0 * math.cos(self.beta)
        sub_tm1[1, 2] =  1.0 * math.sin(self.beta)
        sub_tm1[2, 1] = -1.0 * math.sin(self.beta)
        sub_tm1[2, 2] =  1.0 * math.cos(self.beta) 

        # parallel to Z-Axis
        #if self.isVxZ:
        if lm < common.PRES_ZERO:
            self.isVxZ = True

            #print(f"elem parallel to Z")

            sub_tm2[0, 2] = n
            sub_tm2[1, 0] = n
            sub_tm2[2, 1] = 1.0
        
        # not parallel to Z-Axis
        else: 
            sub_tm2[0, 0] =  l
            sub_tm2[0, 1] =  m
            sub_tm2[0, 2] =  n
            sub_tm2[1, 0] = -m / lm
            sub_tm2[1, 1] =  l / lm
            sub_tm2[2, 0] = -l * n / lm 
            sub_tm2[2, 1] = -m * n / lm
            sub_tm2[2, 2] =  lm

        sub_tm = np.matmul(sub_tm1, sub_tm2)
        
        for i in range(4):
            tm[3 * i : 3 * (i + 1), 3 * i : 3 * (i + 1)] = sub_tm

        self.sub_tm1 = sub_tm1
        self.sub_tm2 = sub_tm2

        return tm

    def SS0_ElmStiffMX(self):

        esm  = np.zeros((12, 12), dtype = np.float64)

        L    = self.len                     #         # m
        EA   = self.sec.mat.E * self.sec.A  #         # N/mm2 * mm2 = N 
        EIy  = self.sec.mat.E * self.sec.Iy #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        EIz  = self.sec.mat.E * self.sec.Iz #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        GJ   = self.sec.mat.G * self.sec.J  #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2

        # axial direction
        esm[ 0,  0] =  EA / L 
        esm[ 0,  6] = -1.0 * esm[ 0,  0]
        esm[ 6,  0] = -1.0 * esm[ 0,  0]
        esm[ 6,  6] =  1.0 * esm[ 0,  0]

        # bending around z-axis
        esm[ 1,  1] = 12.0 * EIz / L ** 3 
        esm[ 1,  7] = -1.0 * esm[ 1,  1]
        esm[ 7,  1] = -1.0 * esm[ 1,  1]
        esm[ 7,  7] =  1.0 * esm[ 1,  1]

        esm[ 1,  5] =  6.0 * EIz / L ** 2 
        esm[ 5,  1] =  1.0 * esm[ 1,  5]
        esm[ 5,  7] = -1.0 * esm[ 1,  5]
        esm[ 7,  5] = -1.0 * esm[ 1,  5]

        esm[ 1, 11] =  6.0 * EIz / L ** 2 
        esm[11,  1] =  1.0 * esm[ 1, 11]
        esm[ 7, 11] = -1.0 * esm[ 1, 11] 
        esm[11,  7] = -1.0 * esm[ 1, 11]

        esm[ 5,  5] =  4.0 * EIz / L 
        esm[11, 11] =  1.0 * esm[ 5,  5] 
        esm[ 5, 11] =  2.0 * EIz / L
        esm[11,  5] =  1.0 * esm[ 5, 11] 

        # bending around y-axis
        esm[ 2,  2] = 12.0 * EIy / L ** 3 
        esm[ 2,  8] = -1.0 * esm[ 2,  2]
        esm[ 8,  2] = -1.0 * esm[ 2,  2]
        esm[ 8,  8] =  1.0 * esm[ 2,  2]

        esm[ 2,  4] = -6.0 * EIy / L ** 2 
        esm[ 4,  2] =  1.0 * esm[ 2,  4]
        esm[ 4,  8] = -1.0 * esm[ 2,  4]
        esm[ 8,  4] = -1.0 * esm[ 2,  4]

        esm[ 2, 10] = -6.0 * EIy / L ** 2 
        esm[10,  2] =  1.0 * esm[ 2, 10]
        esm[ 8, 10] = -1.0 * esm[ 2, 10]
        esm[10,  8] = -1.0 * esm[ 2, 10]

        esm[ 4,  4] =  4.0 * EIy / L
        esm[10, 10] =  1.0 * esm[ 4,  4]
        esm[ 4, 10] =  2.0 * EIy / L 
        esm[10,  4] =  1.0 * esm[ 4, 10]

        # torsion
        esm[ 3,  3] =  GJ / L
        esm[ 3,  9] = -1.0 * esm[ 3,  3]
        esm[ 9,  3] = -1.0 * esm[ 3,  3]
        esm[ 9,  9] =  1.0 * esm[ 3,  3]

        return esm

    def ElmStiffMX(self):

        esm  = np.zeros((12, 12), dtype = np.float64)

        L    = self.len                     #         # m
        EA   = self.sec.mat.E * self.sec.A  #         # N/mm2 * mm2 = N 
        EIy  = self.sec.mat.E * self.sec.Iy #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        EIz  = self.sec.mat.E * self.sec.Iz #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2
        GJ   = self.sec.mat.G * self.sec.J  #* 1e-6   # N/mm2 * mm4 * 1e-6 = Nm2

        # considering shear deformation
        # according to Przemieniecki-Theory-of-matrix-structural-analysis
        PHIy = 12.0 * self.sec.mat.E * self.sec.Iz / (self.sec.mat.G * self.sec.Asy * L ** 2) #* 1e-6 
        PHIz = 12.0 * self.sec.mat.E * self.sec.Iy / (self.sec.mat.G * self.sec.Asz * L ** 2) #* 1e-6 

        # according to Fujii, Matsumoto Excel-Fem (2021)
        lyi = self.jnt.Ryi / EIy # lambda_yi
        lzi = self.jnt.Rzi / EIz # lambda_zi
        lyj = self.jnt.Ryj / EIy # lambda_yj
        lzj = self.jnt.Rzj / EIz # lambda_zj

        lz1 = 1.0 + lzi + lzj
        ly1 = 1.0 + lyi + lyj

        cz = EIz / L ** 3
        cy = EIy / L ** 3

        # axial direction
        esm[ 0,  0] =  EA / L ###
        esm[ 0,  6] = -1.0 * esm[ 0,  0]
        esm[ 6,  0] = -1.0 * esm[ 0,  0]
        esm[ 6,  6] =  1.0 * esm[ 0,  0]

        # bending around z-axis
        esm[ 1,  1] = 6.0 *  cz * (lzi + lzj + 4.0 * lzi * lzj) / lz1 / (1.0 + PHIy)
        # = 12.0 * EIz / L ** 3 / (1.0 + PHIy)
        esm[ 1,  7] = -1.0 * esm[ 1,  1]
        esm[ 7,  1] = -1.0 * esm[ 1,  1]
        esm[ 7,  7] =  1.0 * esm[ 1,  1]

        esm[ 1,  5] =  6.0 * cz * lzi * (1.0 + 2.0 * lzj) * L / lz1 / (1.0 + PHIy)
        # =  6.0 * EIz / L ** 2 / (1.0 + PHIy)
        esm[ 5,  1] =  1.0 * esm[ 1,  5]
        esm[ 5,  7] = -1.0 * esm[ 1,  5]
        esm[ 7,  5] = -1.0 * esm[ 1,  5]

        esm[ 1, 11] =  6.0 * cz * (1.0 + 2.0 * lzi) * lzj * L / lz1 / (1.0 + PHIy)
        # =  6.0 * EIz / L ** 2 / (1.0 + PHIy)
        esm[11,  1] =  1.0 * esm[ 1, 11]
        esm[ 7, 11] = -1.0 * esm[ 1, 11] 
        esm[11,  7] = -1.0 * esm[ 1, 11]

        esm[ 5,  5] = (4.0 + PHIy) / (1.0 + PHIy) * cz * lzi * (1.0 + lzj) / lz1 * 3.0 / 2.0 * L ** 2
        # = (4.0 + PHIy) * EIz / L / (1.0 + PHIy) 
        esm[11, 11] = (4.0 + PHIy) / (1.0 + PHIy) * cz * (1.0 + lzi) * lzj / lz1 * 3.0 / 2.0 * L ** 2
        # =  1.0 * esm[ 5,  5] 
        esm[ 5, 11] = (2.0 - PHIy) / (1.0 + PHIy) * cz * lzi * lzj / lz1 * 3.0 * L ** 2 
        # = (2.0 - PHIy) * EIz / L / (1.0 + PHIy)
        esm[11,  5] =  1.0 * esm[ 5, 11] 

        # bending around y-axis
        esm[ 2,  2] =  6.0 * cy * (lyi + lyj + 4.0 * lyi * lyj) / ly1 / (1.0 + PHIz)
        # = 12.0 * EIy / L ** 3 / (1.0 + PHIz)
        esm[ 2,  8] = -1.0 * esm[ 2,  2]
        esm[ 8,  2] = -1.0 * esm[ 2,  2]
        esm[ 8,  8] =  1.0 * esm[ 2,  2]

        esm[ 2,  4] = -6.0 * cy * lyi * (1.0 + 2.0 * lyj) * L / ly1 / (1.0 + PHIz)
        # = -6.0 * EIy / L ** 2 / (1.0 + PHIz)
        esm[ 4,  2] =  1.0 * esm[ 2,  4]
        esm[ 4,  8] = -1.0 * esm[ 2,  4]
        esm[ 8,  4] = -1.0 * esm[ 2,  4]

        esm[ 2, 10] = -6.0 * cy * (1.0 + 2.0 * lyi) * lyj * L / ly1 / (1.0 + PHIz)
        # = -6.0 * EIy / L ** 2 / (1.0 + PHIz)
        esm[10,  2] =  1.0 * esm[ 2, 10]
        esm[ 8, 10] = -1.0 * esm[ 2, 10]
        esm[10,  8] = -1.0 * esm[ 2, 10]

        esm[ 4,  4] = (4.0 + PHIz) / (1.0 + PHIz) * cy * lyi * (1.0 + lyj) / ly1 * 3.0 / 2.0 * L ** 2 
        # = (4.0 + PHIz) * EIy / L / (1.0 + PHIz)
        esm[10, 10] = (4.0 + PHIz) / (1.0 + PHIz) * cy * (1.0 + lyi) * lyj / ly1 * 3.0 / 2.0 * L ** 2 
        # =  1.0 * esm[ 4,  4]
        esm[ 4, 10] = (2.0 - PHIz) / (1.0 + PHIz) * cy * lyi * lyj / ly1 * 3.0 * L ** 2 
        # = (2.0 - PHIz) * EIy / L / (1.0 + PHIz)
        esm[10,  4] =  1.0 * esm[ 4, 10]

        # torsion
        esm[ 3,  3] =  GJ / L
        esm[ 3,  9] = -1.0 * esm[ 3,  3]
        esm[ 9,  3] = -1.0 * esm[ 3,  3]
        esm[ 9,  9] =  1.0 * esm[ 3,  3]

        self.cy      =  cy
        self.cz      =  cz
        self.lyi     =  lyi
        self.lyj     =  lyj
        self.lzi     =  lzi
        self.lzj     =  lzj
        self.PHIy    =  PHIy
        self.PHIz    =  PHIz

        return esm

    def SS_ElmStiffMX(self):

        # based on Aoyama and Takemura

        E    = self.sec.mat.E
        G    = self.sec.mat.G
        A    = self.sec.A
        Iy   = self.sec.Iy
        Iz   = self.sec.Iz
        J    = self.sec.J
        L    = self.len 
        EA   = E * A 
        EIy  = E * Iy 
        EIz  = E * Iz 
        GJ   = G * J  

        # considering shear deformation
        # according to Aoyama
        gy = 6.0 * EIz / (G * self.sec.Asy * L ** 2) 
        gz = 6.0 * EIy / (G * self.sec.Asz * L ** 2) 

        # this considers rigid zone of beam, springs at beams ends
        # Takemura 2009 "Structural Mechanics for Biophysics and Architecture"
        
        K    = np.zeros((12, 12), dtype = np.float64) 
        Ci   = np.zeros(( 6,  6), dtype = np.float64) # coefficient of joint stiffness
        Cj   = np.zeros(( 6,  6), dtype = np.float64)
        H    = np.zeros(( 6,  6), dtype = np.float64) # equilibrium matrix
        Fm   = np.zeros(( 6,  6), dtype = np.float64) 

        Ci[0, 0] = self.jnt.Txi
        Ci[1, 1] = self.jnt.Tyi
        Ci[2, 2] = self.jnt.Tzi
        Ci[3, 3] = self.jnt.Rxi
        Ci[4, 4] = self.jnt.Ryi
        Ci[5, 5] = self.jnt.Rzi 

        Cj[0, 0] = self.jnt.Txj
        Cj[1, 1] = self.jnt.Tyj
        Cj[2, 2] = self.jnt.Tzj
        Cj[3, 3] = self.jnt.Rxj
        Cj[4, 4] = self.jnt.Ryj
        Cj[5, 5] = self.jnt.Rzj

        H[ 0, 0] =  1
        H[ 1, 1] =  1
        H[ 2, 2] =  1
        H[ 3, 3] =  1
        H[ 4, 4] =  1
        H[ 5, 5] =  1
        H[ 4, 2] = -1.0 * L
        H[ 5, 1] =  1.0 * L

        self.Fci = np.linalg.inv(Ci)
        self.Fcj = np.linalg.inv(Cj)

        Fm[0, 0] =   L / EA
        Fm[1, 1] =  (1.0 + 0.5 * gy) * L ** 3 / (3.0 * EIz) # shear term
        Fm[1, 5] =   1.0 * L ** 2 / (2.0 * EIz)
        Fm[2, 2] =  (1.0 + 0.5 * gz) * L ** 3 / (3.0 * EIy) # shear term
        Fm[2, 4] =  -1.0 * L ** 2 / (2.0 * EIy)
        Fm[3, 3] =   L / GJ
        Fm[4, 4] =   L / EIy
        Fm[5, 5] =   L / EIz 
        Fm[4, 2] =   Fm[2, 4]
        Fm[5, 1] =   Fm[1, 5]

        F    =  np.matmul(np.matmul(H.T, self.Fci), H) + Fm + self.Fcj 
        Finv =  np.linalg.inv(F)

        K11  =  np.matmul(np.matmul(H, Finv), H.T)
        K12  = -1.0 * np.matmul(H, Finv)
        K21  =  K12.T 
        K22  =  Finv

        K[0: 6, 0: 6] = K11
        K[0: 6, 6:12] = K12
        K[6:12, 0: 6] = K21
        K[6:12, 6:12] = K22

        return K
        
    def OutputElmInfo(self):

        props = ["ELEM",
            "{0: >6}".format(self.id),
            "{0: >6}".format(self.n0.id),
            "{0: >6}".format(self.n1.id),
            "{0: >6}".format(self.sec.id),
            "{0: >8}".format(self.theta)
            ]
        
        lns = ', '.join(props) + "\n"

        return lns
    
    #@staticmethod
    def DrawForceDiagram(self, _mdl, _lc, disp_fac, div_num):

        #for e in relevant_elms:
        e    = self
        clc  = _mdl.lcs.index(_lc)
        elds = _mdl.elds

        els = list(filter(lambda el: (el.clc == clc) and (el.eid == e.id), elds))
        
        lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        for el in els: 

            el_lds = np.array(el.lds).reshape(6, 1)
            if el.isGlobal == True: el_lds = e.tm[0:6, 0:6] @ el_lds
            for i in range(6): lds[i] += el_lds[i, 0]
        
        if e.glds is not None: lds += e.glds[:, self.clc]

        vz = e.pln.vz.v # drawing direction of the element

        if e.isVxZ: vz = -1 * vz
        
        p0 = np.array([e.n0.x, e.n0.y, e.n0.z])
        p1 = np.array([e.n1.x, e.n1.y, e.n1.z])
        
        wzi = lds[2]
        wzj = lds[5]
        
        qzi = e.forces[2][self.clc]
        myi = e.forces[4][self.clc]
        myj = e.forces[10][self.clc]

        w_xc= wzi + (wzj - wzi) * 0.5
        m_xc= myi + qzi * 0.5 * e.len + 1.0 / 6.0 * (wzi + 2.0 * w_xc) * (0.5*e.len)**2 
        mp = 0.5 * p0 + 0.5 * p1 - (disp_fac * m_xc) * vz

        spline_pts = []
        vertical_ln_pts = []
        for i in range(div_num+1):
            t   = i / div_num
            x   = t * e.len
            pt  = (1-t) * p0 + t * p1
            w_x = wzi + (wzj - wzj) * t
            m_x = myi + qzi * x + 1.0 / 6.0 * (wzi + 2.0 * w_x) * x**2

            pt_f = pt - disp_fac * m_x * vz
            #frc_graphics.append(vedo.Line(pt, pt_f, lw=self.size["line-weight-thin"], c=self.colors["force-d"]))
            spline_pts.append(pt_f) 
            vertical_ln_pts.append((pt, pt_f))

        #frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))
        
        return [spline_pts, vertical_ln_pts]