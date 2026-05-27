import math
import numpy as np
import copy

PRES_LEN   = 0.001 # in meter
PRES_ANGLE = 0.001 # radian 0.001 ~ ca. 0.0573 degree
PRES_ZERO  = 1e-10 
GRAVITY    = 9.80665 # [m/s^2]


def CalcBounds(pts):
    """Axis-aligned bounds for (x, y, z) points: xmin, xmax, ymin, ymax, zmin, zmax."""

    if pts == None or len(pts) == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    arr = np.array(pts, dtype=float)

    return (
        float(np.min(arr[:, 0])),
        float(np.max(arr[:, 0])),
        float(np.min(arr[:, 1])),
        float(np.max(arr[:, 1])),
        float(np.min(arr[:, 2])),
        float(np.max(arr[:, 2])),
    )

class Plane:

    def __init__(self, _n, _vx, _vy, _vz):

        self.n = _n 
        self.vx   = Vec(_vx[0], _vx[1], _vx[2]) # _vx #np.array
        self.vy   = Vec(_vy[0], _vy[1], _vy[2]) # _vy #np.array
        self.vz   = Vec(_vz[0], _vz[1], _vz[2]) # _vz #np.array

    @staticmethod
    def DistToNode(pln, nd):

        normal_vector = np.cross(pln.vx.v, pln.vy.v)
        normal_vector /= np.linalg.norm(normal_vector)
        
        d = -np.dot(normal_vector, np.array([pln.n.x, pln.n.y, pln.n.z]))
        
        numerator = abs(np.dot(normal_vector, np.array([nd.x, nd.y, nd.z])) + d)
        denominator = np.linalg.norm(normal_vector)

        return numerator / denominator
    
    @staticmethod
    def ProjectNodeToPln(nd, pln): 

        ptarr = np.array([nd.x, nd.y, nd.z]) 
        pln_nvec = pln.vz.v
        pln_orig  = np.array([pln.n.x, pln.n.y, pln.n.z])
    
        point_to_plane_vector = ptarr - pln_orig
        
        distance = np.dot(point_to_plane_vector, pln_nvec) / np.linalg.norm(pln_nvec)
        
        projected_point = ptarr - distance * pln_nvec

        return projected_point
    
    @staticmethod
    def ConvertToPlnCoordinates(projected_point, pln):

        plane_x = pln.vx.v
        plane_y = pln.vy.v
        
        x_coordinate = np.dot(projected_point, pln.vx.v) / np.linalg.norm(pln.vx.v)
        y_coordinate = np.dot(projected_point, pln.vy.v) / np.linalg.norm(pln.vy.v)
        
        return x_coordinate, y_coordinate
    
class Vec:

    def __init__(self, _vx, _vy, _vz):

        self.v = np.array([_vx, _vy, _vz])
        self.len = np.linalg.norm(self.v)

        return
    
    @staticmethod
    def amplify(_v, _value): 

        # if (type(_v) is not Vec):
        #     print(f"*** amplify type(_v) is not Vec: {type(_v)}")

        vec = copy.deepcopy(_v)
        # print(f"*** amplify type(vec) : {type(vec)}")

        if vec.len - PRES_ZERO < 0:
            return Vec(0, 0, 0)
        else:
            newlen = vec.v / vec.len * _value
        
        vec.v = newlen
        vec.len = np.linalg.norm(vec.v)
        #print(f"vec.len: {vec.len}")

        return vec
    
    def isParallel(self, _v):
        
        cross_p = np.cross(self.v, _v.v)
        return np.allclose(cross_p, np.zeros(3))
    
class Pnt:

    def __init__(self, _x, _y, _z):

        self.x = _x
        self.y = _y
        self.z = _z

        self.arr = np.array([self.x, self.y, self.z])

