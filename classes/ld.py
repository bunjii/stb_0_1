import common
import math

import numpy as np
from shapely.geometry import Polygon
from scipy.spatial import Voronoi

class Lcase:
    def __init__(self, _lc, _lname):
        self.lc = _lc
        self.lname = _lname

    def OutputLnameInfo(self):

        props = ["LNME",
                 "{0: >4}".format(self.lc), 
                 "{0: >8}".format(self.lname), 
        ]

        lns = ', '.join(props) + "\n"

        return lns

class Lcmb:
    def __init__(self, _lc, _name, _fcs, _lcs):
        self.lc  = _lc
        self.name = _name
        self.fcs = _fcs # factors
        self.lcs = _lcs # lcases

    def OutputLcmbInfo(self):

        props = ["LCMB",
                 "{0: >4}".format(self.lc), 
                 "{0: >8}".format(self.name), 
        ]

        for i in range(len(self.fcs)):
            props.append("{0: >5}".format(self.fcs[i]))
            props.append("{0: >5}".format(self.lcs[i]))

        lns = ', '.join(props) + "\n"

        return lns

class PLd:

    def __init__(self, 
                 _nid: int, 
                 _lc: int, 
                 _px: float, 
                 _py: float, 
                 _pz: float, 
                 _mx: float, 
                 _my: float, 
                 _mz: float,
                 _combi=False):

        self.nid =  _nid
        self.lc  =  _lc 
        self.lds = [_px, _py, _pz, _mx, _my, _mz]
        self.pv  =   common.Vec(_px, _py, _pz) # point load vector
        self.mv  =   common.Vec(_mx, _my, _mz) # moment vector

        self.clc =   None
        self.nd  =   None
        self.combi = _combi

    def FindNd(self, _nds):

        self.nd =  list(filter(lambda n: n.id == self.nid, _nds))[0]

    def OutputLdInfo(self):

        props = ["PLOD",
                 "{0: >6}".format(self.nid), 
                 "{0: >4}".format(self.lc), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N] -> [kN], [Nm] -> [kNm]

        lns = ', '.join(props) + "\n"

        return lns
    
class ELd:

    def __init__(self, 
                 _eid: int, 
                 _lc: int, 
                 _isG: int,
                 _wxi: float, 
                 _wyi: float, 
                 _wzi: float, 
                 _wxj: float, 
                 _wyj: float, 
                 _wzj: float,
                 _combi=False):

        self.eid =  _eid
        self.lc  =  _lc
        self.isGlobal = _isG
        self.lds = [_wxi, _wyi, _wzi, _wxj, _wyj, _wzj] # can be in GCS or ECS

        self.len = math.sqrt(max([abs(_wxi), abs(_wxj)])**2 + max([abs(_wyi), abs(_wyj)])**2 + max([abs(_wzi), abs(_wzj)])**2)

        self.clc =   None
        self.elm =   None
        self.combi = _combi

    def FindElm(self, _elms):

        self.elm =  list(filter(lambda e: e.id == self.eid, _elms))[0]

    def OutputELdInfo(self):

        props = ["ELOD",
                 "{0: >6}".format(self.eid), 
                 "{0: >4}".format(self.lc), 
                 "{0: >4}".format(self.isGlobal), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N] -> [kN], [Nm] -> [kNm]

        lns = ', '.join(props) + "\n"

        return lns

class ALd:
    def __init__(self, _lc, _px, _py, _pz, _e1, _e2, _e3, _e4, _combi=False):
        self.lc = _lc
        self.lds = [_px, _py, _pz]
        self.eids = [_e1, _e2, _e3, _e4]
        self.combi = _combi

        self.clc = None  # will be set by mdl

        self.nds = None  # will be set by SetLdPropsByVolonoiDivision in mdl
        self.elms = None # will be set by mdl
        self.nds_areas = None # will be set by SetLdPropsByVolonoiDivision in mdl
        self.elms_areas = None # will be set by SetLdPropsByVolonoiDivision in mdl

        # self.SetLdPropsByVolonoiDivision()

    def SetLdPropsByVolonoiDivision(self):

        # Identify the vertices of the quadrilateral or triangle
        vertices_3d = []
        elms = self.elms
        nds = []

        for e in elms:
            if e.n0 not in nds:
                nds.append(e.n0)
            if e.n1 not in nds:
                nds.append(e.n1)

        for nd in nds:
            vertices_3d.append([nd.x, nd.y, nd.z])
        
        vertices_3d = np.array(vertices_3d)

        # Verify we have at least 3 vertices
        if len(vertices_3d) < 3:
            raise ValueError("Need at least 3 vertices to form a polygon")

        # Calculate transformation matrix from 3D to 2D
        v1 = vertices_3d[1] - vertices_3d[0]  # First edge vector
        v2 = vertices_3d[2] - vertices_3d[0]  # Second edge vector (using third vertex for triangle)
        normal = np.cross(v1, v2)
        normal = normal / np.linalg.norm(normal)

        e1 = v1 / np.linalg.norm(v1)  # First basis vector
        e2 = np.cross(normal, e1)  # Second basis vector (perpendicular to e1)

        transform_matrix = np.vstack([e1, e2])  # Matrix for 3D to 2D projection

        # Project 3D vertices to 2D
        origin = vertices_3d[0]  # Origin point for the projection
        vertices_2d = np.array([
            transform_matrix @ (vertex - origin) for vertex in vertices_3d
        ])

        # Define boundary polygon
        boundary_polygon = Polygon(vertices_2d)  # 2D polygon object

        # Generate points by dividing each edge and include vertices
        num_div = 8  # Number of divisions for each edge
        points_2d = []  # List to store 2D points
        points_3d = []  # List to store 3D points
        n_vertices = len(vertices_3d)  # Get number of vertices

        # Add vertices first
        for vertex_2d, vertex_3d in zip(vertices_2d, vertices_3d):
            points_2d.append(vertex_2d)
            points_3d.append(vertex_3d)

        # Add points on edges
        for i in range(n_vertices):
            start_2d = vertices_2d[i]
            end_2d = vertices_2d[(i+1)%n_vertices]
            start_3d = vertices_3d[i]
            end_3d = vertices_3d[(i+1)%n_vertices]
            
            for j in range(1, num_div):
                t = j / num_div
                point_2d = start_2d + t * (end_2d - start_2d)
                points_2d.append(point_2d)
                point_3d = start_3d + t * (end_3d - start_3d)
                points_3d.append(point_3d)

        points_2d = np.array(points_2d)
        points_3d = np.array(points_3d)

        # points_3d: [x, y, z] all points in 3D
        # 

        # Calculate bounding box for 2D projected vertices
        min_x, min_y = np.min(vertices_2d, axis=0)  # Minimum coordinates of the bounding box
        max_x, max_y = np.max(vertices_2d, axis=0)  # Maximum coordinates of the bounding box

        # Set margin and extra points for Voronoi calculation
        margin = max(max_x - min_x, max_y - min_y) * 2  # Margin size for extra points
        extra_points = []  # List to store points outside the polygon for proper Voronoi computation
        n_extra = 4  # Number of extra points along each direction

        for i in range(n_extra):
            for j in range(n_extra):
                x = min_x - margin + (max_x - min_x + 2*margin) * i/(n_extra-1)
                y = min_y - margin
                extra_points.append([x, y])
                y = max_y + margin
                extra_points.append([x, y])
            y = min_y - margin + (max_y - min_y + 2*margin) * i/(n_extra-1)
            extra_points.append([min_x - margin, y])
            extra_points.append([max_x + margin, y])

        extra_points = np.array(extra_points)
        all_points_2d = np.vstack([points_2d, extra_points])

        # Generate Voronoi diagram
        vor = Voronoi(all_points_2d)  # Voronoi diagram object

        # Calculate total area based on polygon type
        n_vertices = len(vertices_3d)
        if n_vertices == 3:  # Triangle case
            total_area_3d = np.linalg.norm(np.cross(v1, v2)) / 2
        elif n_vertices == 4:  # Quadrilateral case
            # Calculate area using two triangles
            v3 = vertices_3d[3] - vertices_3d[0]
            total_area_3d = (np.linalg.norm(np.cross(v1, v2)) + np.linalg.norm(np.cross(v2, v3))) / 2
        else:
            raise ValueError("Only triangles and quadrilaterals are supported")

        total_area_2d = boundary_polygon.area
        scale_factor = total_area_3d / total_area_2d

        total_area_2d = boundary_polygon.area
        scale_factor = total_area_3d / total_area_2d
        areas_2d = []  # List to store areas of 2D regions
        areas_3d = []  # List to store areas of 3D regions

        for i in range(len(points_2d)):
            region_idx = vor.point_region[i]
            region = vor.regions[region_idx]
            
            if -1 in region or len(region) < 3:
                continue
            
            vertices_2d = vor.vertices[region]
            region_polygon = Polygon(vertices_2d)
            clipped_region = region_polygon.intersection(boundary_polygon)
            
            if clipped_region.area > 0:
                area_2d = clipped_region.area
                areas_2d.append(area_2d)
                area_3d = area_2d * scale_factor
                areas_3d.append(area_3d)

        # Print areas
        # print(f"Individual 3D areas: {[f'{a:.2f}' for a in areas_3d]}")

        self.nds = nds

        # node areas
        node_areas = []
        for nd in nds:

            nd_pos = [nd.x, nd.y, nd.z]

            for i in range(len(points_3d)):
                if np.linalg.norm(points_3d[i] - nd_pos) < common.PRES_LEN:
                    node_areas.append(areas_3d[i])
                    break

        self.nds_areas = node_areas

        # element areas
        elms_areas = []
        for e in elms:
            sp = np.array([e.n0.x, e.n0.y, e.n0.z])
            ep = np.array([e.n1.x, e.n1.y, e.n1.z])
            elm_areas = []
            for i in range(num_div-1):
                t = (i + 1) / num_div
                p = (1-t) * sp + t * ep

                for j in range(len(points_3d)):
                    if np.linalg.norm(points_3d[j] - p) < common.PRES_LEN:
                        elm_areas.append(areas_3d[j])
                        break

            elms_areas.append(elm_areas)

        self.elms = elms
        self.elms_areas = elms_areas

        return

    def OutputALdInfo(self):
        props = ["ALOD",
                 "{0: >6}".format(self.lc), 
        ]

        for l in self.lds:
            props.append("{0: >6.2f}".format(l * 1e-3)) # [N/m2] -> [kN/m2]

        for eid in self.eids:
            props.append("{0: >4}".format(eid)) 

        lns = ', '.join(props) + "\n"

        return lns

class GLd:

    def __init__(self, 
                 _lc:   int, 
                 _gx: float,
                 _gy: float, 
                 _gz: float,
                 _combi=False):
        
        self.lc = _lc
        self.gx = _gx
        self.gy = _gy
        self.gz = _gz 

        self.clc =   None
        self.combi = _combi
        
    def OutputGLdInfo(self):

        props = ["GLOD",
                 "{0: >6}".format(self.lc), 
                 "{0: >9.6f}".format(self.gx),
                 "{0: >9.6f}".format(self.gy),
                 "{0: >9.6f}".format(self.gz)
        ]

        lns = ', '.join(props) + "\n"

        return lns