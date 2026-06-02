import os
import wx
import sys
import copy
import numpy as np

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, config
from ezdxf.addons.drawing import layout, pymupdf
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.enums import TextEntityAlignment
import matplotlib.pyplot as plt

from mdl  import Mdl
from common import Plane, PRES_ZERO
from nd import Nd


class Export:

    def __init__(self, _main_frame):
        self.main_frame = _main_frame
        self.mdl = self.main_frame.mdl

    def ExportResults(self):

        if self.main_frame.isModelSolved == False:
            print("Model is not solved.")
            return

        if not self.main_frame.filepath:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            initial_dir = desktop_path
        else:
            initial_dir = os.path.dirname(self.main_frame.filepath)

        with wx.FileDialog(None, "Save CSV file", defaultDir=initial_dir, wildcard="CSV files (*.csv)|*.csv",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                export_path = dialog.GetPath()
                if not export_path.endswith('.csv'):
                    export_path += '.csv'
                print(f"Selected file: {export_path}")
            else:
                print("No file selected.")
                return
        
        with open(export_path, 'w', newline='', encoding='utf-8') as file:
            file.write(self.main_frame.input_txt)
            file.write(self.main_frame.output_txt)
            file.write("END OF FILE \n")
        
        print(f"Exported to {export_path}")

        return

    def ClearPlt2dArr(self):

        for n in self.mdl.nds:
            n.plt2d_arr = None

    def DrawPages(self, width, height):

        self.doc = None
        self.msp = None
        self.hatch = None

        self.margin_h = 7.5     # paper margin horizontal
        self.margin_v = 5.0     # paper margin vertical
        self.height_v_band = 10.0 # height of bottom band

        self.offset_ax = 2.0    # offset value above the band-line
        self.rad_ax = 3.0       # radius of the circle symbol of each axis 
        self.offset_ax2= 8.0    # offset value above the band-line for the second group of axes
        # self.ln_ax = 10.0

        # self.gap_dim = 5.0

        self.offset_tag = 0.9

        elmids_jnts = list(map(lambda j: j.eid, self.mdl.ejnts))

        for p in self.mdl.plts: 

            self.doc = ezdxf.new('R2010', setup=True) 
            self.doc.header['$LTSCALE'] = 0.5
            self.doc.styles.add("MSゴシック", font="msgothic.ttc")
            # self.doc.linetypes.add(
            #     name="DASHED", 
            #     pattern=[1.0, -1.0]
            # )
            self.msp = self.doc.modelspace()
            self.msp.delete_all_entities()
            self.ClearPlt2dArr()

            self.hatch = self.msp.add_hatch(color=7)
            self.hatch_coloured = self.msp.add_hatch(color=7) #9

            self.doc.layers.new('01_Frame', dxfattribs={'color': 0}) 
            #self.hatch_coloured.dxf.dxfattribs = {'layer':'01_Frame'}

            drawing_name = p.name
            axis = list(filter(lambda a: a.id == p.axis_id, self.mdl.axes))[0]

            pln  = axis.pln
            type = p.type
            lc   = p.lc
            deffac = p.deffac

            elms = self.SelElms(axis)
            axes = self.SelAxes(axis)

            pts = []
            for e in elms: 

                if e.n0.plt2d_arr is None:
                    # project element's nodes to axis plane
                    proj_pt_n0 = Plane.ProjectNodeToPln(e.n0, pln)
                    # convert to the paper coordinate system
                    x0, y0 = Plane.ConvertToPlnCoordinates(proj_pt_n0, pln) 
                    # scale to the drawing scale
                    e.n0.plt2d_arr = np.array([x0, y0]) / p.scale * 1000
                    pts.append(e.n0.plt2d_arr)
                
                if e.n1.plt2d_arr is None:

                    proj_pt_n1 = Plane.ProjectNodeToPln(e.n1, pln) 
                    x1, y1 = Plane.ConvertToPlnCoordinates(proj_pt_n1, pln)                
                    e.n1.plt2d_arr = np.array([x1, y1]) / p.scale * 1000
                    pts.append(e.n1.plt2d_arr)

            # calculate bbox in the paper plane
            minx, miny = np.min(pts, axis=0)
            maxx, maxy = np.max(pts, axis=0)
            avex, avey = 0.5 * (maxx + minx) , 0.5 * (maxy + miny)
            
            shiftx, shifty = 0.5*width  - avex, 0.5*height - avey

            # paper margins
            margin_h = self.margin_h
            margin_v = self.margin_v
            ### height_v_band = self.height_v_band

            # draw element line
            # (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)
            if type == 0: lw = 13
            else: lw = 5

            # text
            page_name = ""
            
            page_name += f"Structural Toolbox 1.0.0 "
            page_name += f" {self.mdl.date_analysis} "
            page_name += f" {self.mdl.filepath} "

            pos = (margin_h + self.offset_tag, height - margin_v - self.offset_tag)

            self.msp.add_text(page_name, 
                            dxfattribs={
                                'style': 'MSゴシック',
                                'height': 2.0,
                                'width': 1.0
                            }).set_placement(pos, align=TextEntityAlignment.TOP_LEFT)
            
            page_name = ""

            # (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)
            if type == 0: # TYPE 0: MODEL
                page_name += f"解析モデル図 - {axis.name}"

            elif type == 1:
                pass

            elif type == 2:
                page_name += f"応力図 [{lc}] - {axis.name}"

            elif type == 3:
                pass 
            
            if axis.isHorizontal: # FUSE
                page_name += f"階 "
            else: # JIKU
                page_name += f"通 "

            pos = (margin_h + self.offset_tag, height - margin_v - self.offset_tag - 5.0)

            self.msp.add_text(page_name, 
                            dxfattribs={
                                'style': 'MSゴシック',
                                'height': 3.0,
                                'width': 1.0
                            }).set_placement(pos, align=TextEntityAlignment.TOP_LEFT)
            
            # axes
            for a in axes: 

                # obtain node of each axis
                nd = list(filter(lambda n: n.id == a.nid, self.mdl.nds))[0]
                # project node point to the paper plane
                proj_pt = Plane.ProjectNodeToPln(nd, pln) 
                # calculate point coordinate on the paper plane
                x, y = Plane.ConvertToPlnCoordinates(proj_pt, pln) 
                # adjust scale considering plot's scale and m -> mm
                pt_arr = np.array([x, y]) / p.scale * 1000 
                # register each axis' node point in paper scale
                a.pt_arr = pt_arr

                if axis.isHorizontal == False: #jiku

                    if a.isHorizontal == False:
                        pt_arr[0] += shiftx
                        pt_arr[1]  = self.margin_v + self.height_v_band + self.rad_ax + self.offset_ax  
                        
                    elif a.isHorizontal == True:
                        pt_arr[0]  = width - self.margin_h - self.rad_ax - self.offset_ax
                        pt_arr[1] += shifty
                
                else: #fuse
                    
                    if a.xdir == 0: # axis running in x-dir
                        pt_arr[0]  = width - self.margin_h - self.rad_ax - self.offset_ax
                        pt_arr[1] += shifty    

                    elif a.xdir == 1: # axis running in y-dir
                        pt_arr[0] += shiftx
                        pt_arr[1]  = self.margin_v + self.height_v_band + self.rad_ax + self.offset_ax  
                        # # pt_arr[1]+= miny + shifty - offset_ax

                # draw axis circle
                if axis.isHorizontal == False and a.isHorizontal:
                    self.msp.add_text(a.name, dxfattribs={
                                      'style': 'Standard',
                                      'height': 2.0,
                                      'width':  0.8,
                                      'lineweight': 5
                                  }).set_placement(pt_arr, 
                                                   align=TextEntityAlignment.MIDDLE_CENTER) 
                else:
                    self.msp.add_circle(pt_arr, radius=self.rad_ax, dxfattribs={'lineweight': 5}) 
                    self.msp.add_text(a.name, dxfattribs={
                                      'style': 'Standard',
                                      'height': 3.0,
                                      'width':  0.8,
                                      'lineweight': 5
                                  }).set_placement(pt_arr, 
                                                   align=TextEntityAlignment.MIDDLE_CENTER) 
                
            # dimension lines
            ## JIKU
            if axis.isHorizontal == False: 
                x_axes = list(filter(lambda a: a.isHorizontal == False, axes))
                sorted_x_axes = sorted(x_axes, key=lambda a: a.pt_arr[0])
                y_axes = list(filter(lambda a: a.isHorizontal, axes))
                sorted_y_axes = sorted(y_axes, key=lambda a: a.pt_arr[1])
            
            ## FUSE 
            else: 
                x_axes = list(filter(lambda a: a.xdir == 1, axes))
                sorted_x_axes = sorted(x_axes, key=lambda a: a.pt_arr[0])
                y_axes = list(filter(lambda a: a.xdir == 0, axes))
                sorted_y_axes = sorted(y_axes, key=lambda a: a.pt_arr[1])
            
            ## dimension lines - horizontal direction
            for i in range(len(sorted_x_axes)-1):
                sp = sorted_x_axes[i].pt_arr
                ep = sorted_x_axes[i+1].pt_arr

                p1 = (sp[0], sp[1]+self.rad_ax+self.offset_ax2)
                p2 = (ep[0], ep[1]+self.rad_ax+self.offset_ax2)

                self.msp.add_aligned_dim(
                    p1=p1, 
                    p2=p2,  
                    distance=4,
                    override={
                        "dimtxsty": "Standard",
                        "dimtxt": 2.0,
                        "dimlfac": p.scale,
                        
                        "dimdle": 2, # extension of dimension line in drawing units 
                        "dimlwd": 5, # line weight of dimension line

                        "dimlwe": 5, # line weight of extension line
                        "dimexe": 8, # extension beyond dimension line in drawing units
                        "dimexo": 2, # offset of extension line from measurement point

                        "dimtsz": 0, # tick size in drawing units, set to 0 to use arrows
                        "dimblk": "DOTSMALL", 
                        "dimasz": 3  # arrow size in drawing units

                    } 
                ).render()

                if i == len(sorted_x_axes)-2:
                    sp = sorted_x_axes[0].pt_arr
                    p1 = (sp[0], sp[1]+self.rad_ax+self.offset_ax)
                    p2 = (ep[0], ep[1]+self.rad_ax+self.offset_ax)

                    self.msp.add_aligned_dim(
                        p1=p1, 
                        p2=p2,  
                        distance=4,
                        override={
                            "dimtxsty": "Standard",
                            "dimtxt": 2.0,
                            "dimlfac": p.scale,
                            
                            "dimdle": 2, # extension of dimension line in drawing units 
                            "dimlwd": 5, # line weight of dimension line

                            "dimlwe": 5, # line weight of extension line
                            "dimexe": 4, # extension beyond dimension line in drawing units
                            "dimexo": 2, # offset of extension line from measurement point

                            "dimtsz": 0, # tick size in drawing units, set to 0 to use arrows
                            "dimblk": "DOTSMALL", 
                            "dimasz": 3  # arrow size in drawing units

                        } 
                    ).render()
            
            ## dimension lines - vertical direction
            for i in range(len(sorted_y_axes)-1):
                sp = sorted_y_axes[i].pt_arr
                ep = sorted_y_axes[i+1].pt_arr

                p1 = (sp[0]-self.rad_ax-self.offset_ax2, sp[1])
                p2 = (ep[0]-self.rad_ax-self.offset_ax2, ep[1])

                self.msp.add_aligned_dim(
                    p1=p1, 
                    p2=p2,  
                    distance=4,
                    override={
                        "dimtxsty": "Standard",
                        "dimtxt": 2.0,
                        "dimlfac": p.scale,
                        
                        "dimdle": 2, # extension of dimension line in drawing units 
                        "dimlwd": 5, # line weight of dimension line

                        "dimlwe": 5, # line weight of extension line
                        "dimexe": 8, # extension beyond dimension line in drawing units
                        "dimexo": 2, # offset of extension line from measurement point

                        "dimtsz": 0, # tick size in drawing units, set to 0 to use arrows
                        "dimblk": "DOTSMALL", 
                        "dimasz": 3  # arrow size in drawing units

                    } 
                ).render()

                if i == len(sorted_y_axes)-2:
                    sp = sorted_y_axes[0].pt_arr
                    p1 = (sp[0]-self.rad_ax-self.offset_ax, sp[1])
                    p2 = (ep[0]-self.rad_ax-self.offset_ax, ep[1])

                    self.msp.add_aligned_dim(
                        p1=p1, 
                        p2=p2,  
                        distance=4,
                        override={
                            "dimtxsty": "Standard",
                            "dimtxt": 2.0,
                            "dimlfac": p.scale,
                            
                            "dimdle": 2, # extension of dimension line in drawing units 
                            "dimlwd": 5, # line weight of dimension line

                            "dimlwe": 5, # line weight of extension line
                            "dimexe": 4, # extension beyond dimension line in drawing units
                            "dimexo": 2, # offset of extension line from measurement point

                            "dimtsz": 0, # tick size in drawing units, set to 0 to use arrows
                            "dimblk": "DOTSMALL", 
                            "dimasz": 3  # arrow size in drawing units

                        } 
                    ).render()

            # node
            for n in self.mdl.nds:

                if n.plt2d_arr is None: continue

                # adjust the 2d position to fit in the paper
                n.plt2d_arr[0] += shiftx 
                n.plt2d_arr[1] += shifty 

                # draw node circle
                self.msp.add_circle((n.plt2d_arr[0], n.plt2d_arr[1]), radius=0.3, 
                                    dxfattribs={
                                        'lineweight': 13
                                        })
                
                self.DrawCircularHatch((n.plt2d_arr[0], n.plt2d_arr[1]), radius=0.3)

                # draw node id
                # (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)
                if type == 0:
                    self.msp.add_text(f"{n.id}", 
                                    dxfattribs={
                                        'style': 'Standard',
                                        'height': 1.5,
                                        'width': 0.65
                                    }).set_placement((n.plt2d_arr[0] - self.offset_tag, 
                                                        n.plt2d_arr[1] - self.offset_tag ), 
                                                    align=TextEntityAlignment.TOP_RIGHT)
                
                # draw support
                if n.cons is not None:
                    self.DrawSupport(n, 1.5, lw) 

                ## if fuse: then draw column label. also draw a dashed line for wall/diagonal element
                if axis.isHorizontal:

                    connected_elms = list(filter(lambda e: (e.n0 == n or e.n1 == n), self.mdl.elms))
                    for ce in connected_elms:

                        if ce.n0.z <= axis.pln.n.z+PRES_ZERO and ce.n1.z <= axis.pln.n.z+PRES_ZERO:
                            continue

                        # vertical column
                        if abs(ce.n0.x - ce.n1.x) < PRES_ZERO and abs(ce.n0.y - ce.n1.y) < PRES_ZERO:
                            # draw elem's sec id
                            self.msp.add_text(f"{ce.sec.name}", 
                                            dxfattribs={
                                                'style': 'Standard',
                                                'height': 1.5,
                                                'width': 0.65
                                            }).set_placement(n.plt2d_arr, align=TextEntityAlignment.BOTTOM_LEFT) 
                                                            
                            
                        # non-vertical element
                        else: 
                            # draw dashed line 
                            if ce.n0 == n:
                                spt = copy.deepcopy(ce.n0.plt2d_arr)

                                proj_n = Plane.ProjectNodeToPln(ce.n1, pln)
                                x0, y0 = Plane.ConvertToPlnCoordinates(proj_n, pln)
                                ept = np.array([x0, y0]) / p.scale * 1000
                            
                            else:
                                spt = copy.deepcopy(ce.n1.plt2d_arr)

                                proj_n = Plane.ProjectNodeToPln(ce.n0, pln)
                                x0, y0 = Plane.ConvertToPlnCoordinates(proj_n, pln)
                                ept = np.array([x0, y0]) / p.scale * 1000
                            
                            ept[0] += shiftx
                            ept[1] += shifty
                            
                            ev = ept - spt 
                            rotation_matrix = np.array([[0,-1], [1,0]])
                            nv  = rotation_matrix @ ev
                            nv /= np.linalg.norm(nv) 

                            spt_new  = spt
                            ept_new  = spt + 0.2*ev # 20% of projected elem length
                            
                            offset_ln= 0.5 
                            vx = np.array((1.0, 0.0))
                            vy = np.array((0.0, 1.0)) 
            
                            if (abs(np.cross(ev, vx)) < PRES_ZERO or 
                                abs(np.cross(ev, vy)) < PRES_ZERO):

                                spt_new += offset_ln*nv
                                spt_new += 0.05*ev
                                ept_new += offset_ln*nv

                                ept_new_tag = ept_new + ev / np.linalg.norm(ev) * 1.0 + 0.75*nv
                            
                            else:
                                spt_new += 0.05*ev 
                                ept_new_tag = ept_new + ev / np.linalg.norm(ev) * 1.0

                            self.msp.add_line(spt_new, ept_new, 
                                                dxfattribs={'layer': '01_Frame',
                                                            'lineweight':'5',
                                                            'linetype':"DASHED"
                                                            })

                            # draw elem's sec id
                            if ev[0] < PRES_ZERO: ev *= -1
                            deg = Export.DegBetweenVecs(vx, ev)
                            if deg > 90: deg = 180 - deg
                            if ev[1] < PRES_ZERO: deg *= -1

                            self.msp.add_text(f"{ce.sec.name}", 
                                            dxfattribs={
                                                'style': 'Standard',
                                                'height': 1.5,
                                                'width': 0.65, 
                                                'rotation': deg
                                            }).set_placement(ept_new_tag, align=TextEntityAlignment.MIDDLE_CENTER) 
                                     
            # element
            for e in elms: 

                self.msp.add_line(e.n0.plt2d_arr, e.n1.plt2d_arr, 
                     dxfattribs={#'layer': '01_Frame',
                                 'lineweight': lw})
                
                # draw sec name and elem id 
                elmpt = 0.4 * e.n0.plt2d_arr + 0.6 * e.n1.plt2d_arr

                ev = e.n1.plt2d_arr - e.n0.plt2d_arr
                if ev[0] < PRES_ZERO: ev *= -1
                rotation_matrix = np.array([[0, -1], [1, 0]])
                nv  = rotation_matrix @ ev 
                nv /= np.linalg.norm(nv)

                if nv[1] < 0: nv = -1 * nv

                elmpt += nv * (1.5)

                vx = np.array([1.0, 0.0])
                deg = Export.DegBetweenVecs(vx, ev)

                if deg > 90: deg = 180 - deg
                if ev[1] < PRES_ZERO: deg *= -1

                # (TYPE 0: MODEL, 1: LOAD, 2: FORCE, 3: UTIL)
                if type == 0:
                    self.msp.add_text(f"{e.sec.name}:{e.id}", 
                                    dxfattribs={
                                        'style': 'Standard',
                                        'height': 1.5,
                                        'width': 0.65,
                                        'rotation': deg
                                    }).set_placement(elmpt, 
                                                    align=TextEntityAlignment.MIDDLE_CENTER) 
                
                # element joint
                if e.id in elmids_jnts and type == 0: 
                    jnt = list(filter(lambda j: j.eid == e.id, self.mdl.ejnts))[0]

                    sn_pt   = e.n0.plt2d_arr
                    en_pt   = e.n1.plt2d_arr
                    rad_jnt = 0.4
                    rad_nd  = 0.3
                    elen    = e.len / p.scale * 1000
                    t       = (rad_jnt * 2 +rad_nd)/elen
                    s_ptarr = (1-t) * sn_pt + t * en_pt
                    e_ptarr = t * sn_pt + (1-t) * en_pt

                    if ((jnt.ryi == 0.0  and jnt.rzi == 0.0) or 
                        (jnt.ryi is None and jnt.rzi == 0.0) or
                        (jnt.ryi == 0.0  and jnt.rzi is None)): 
                        # Draw single circle
                        self.DrawCircularColouredHatchAndCircle(s_ptarr, radius=rad_jnt) 
                    
                    elif jnt.ryi is None and jnt.rzi is None:
                        # Draw nothing
                        pass
                    else: 
                        # Draw double circles
                        print(f"id: {e.id} i-else")
                        self.DrawCircularColouredHatchAndCircle(s_ptarr, radius=rad_jnt)
                        self.msp.add_circle(s_ptarr, radius=rad_jnt*1.8, dxfattribs={'lineweight': 13})


                    if ((jnt.ryj == 0.0  and jnt.rzj == 0.0) or 
                        (jnt.ryj is None and jnt.rzj == 0.0) or
                        (jnt.ryj == 0.0  and jnt.rzj is None)): 
                        # Draw single circle
                        self.DrawCircularColouredHatchAndCircle(e_ptarr, radius=rad_jnt)
                        
                    elif jnt.ryj == None and jnt.rzj == None:
                        # Draw nothing
                        pass
                    else: 
                        # Draw double circles
                        print(f"id: {e.id} j-else")
                        self.DrawCircularColouredHatchAndCircle(e_ptarr, radius=rad_jnt)
                        self.msp.add_circle(e_ptarr, radius=rad_jnt*1.6, dxfattribs={'lineweight': 13})

                    #print(f"eid: {e.id}, jnt={[jnt.ryi, jnt.rzi, jnt.ryj, jnt.rzj]}")

            # Force
            if type == 2:
                self.DrawForce(lc, deffac, elms, p)

            self.DrawDXF(width, height, drawing_name)
        
        print(f"draw model page done: {len(elms)}")

        return

    def DrawCircularHatch(self, center, radius):
        # center: (x, y) tuple for the center of the circle
        # radius: radius of the circle
        # color: color index (ACI) for the fill color

        # Define the boundary path as a circle
        edge_path = self.hatch.paths.add_edge_path()
        edge_path.add_arc(center=center, radius=radius, start_angle=0, end_angle=360)

        return #hatch
    
    def DrawCircularColouredHatchAndCircle(self, center, radius):
        # center: (x, y) tuple for the center of the circle
        # radius: radius of the circle
        # color: color index (ACI) for the fill color

        self.msp.add_circle(center, radius=radius, 
                                    dxfattribs={
                                        'layer': '01_Frame',
                                        'lineweight': 13
                                        })

        # Define the boundary path as a circle
        edge_path = self.hatch_coloured.paths.add_edge_path()
        edge_path.add_arc(center=center, radius=radius, start_angle=0, end_angle=360)
        

        return #hatch
    
    def DrawSupport(self, nd, height, lw):

        pt0 = nd.plt2d_arr
        pt1 = pt0 + np.array([-0.5*height, -height])
        pt2 = pt0 + np.array([+0.5*height, -height])

        self.msp.add_line(pt0, pt1, dxfattribs={'lineweight': lw})
        self.msp.add_line(pt1, pt2, dxfattribs={'lineweight': lw})
        self.msp.add_line(pt2, pt0, dxfattribs={'lineweight': lw})


    @staticmethod
    def DegBetweenVecs(v1, v2):

        dp = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        cos_angle = dp / (norm_v1 * norm_v2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_radians = np.arccos(cos_angle)
        angle_degrees = np.degrees(angle_radians)

        return angle_degrees

    def SelElms(self, axis): 

        elms = self.mdl.elms 
        sel_elms = []
        for e in elms:
            dist0 = Plane.DistToNode(axis.pln, e.n0)
            dist1 = Plane.DistToNode(axis.pln, e.n1)

            if dist0 + dist1 > PRES_ZERO * 2: continue

            sel_elms.append(e)

        return sel_elms
    
    def SelAxes(self, axis):

        axes = self.mdl.axes

        for a in axes:
            if axis.isHorizontal:
                lst = list(filter(lambda a: a.isHorizontal == 0, axes))
                return lst
            elif axis.xdir == 0: 
                lst = list(filter(lambda a: a.xdir == 1, axes))
                lst.extend(list(filter(lambda a: a.isHorizontal, axes)))
                return lst
            elif axis.xdir == 1:
                lst = list(filter(lambda a: a.xdir == 0, axes))
                lst.extend(list(filter(lambda a: a.isHorizontal, axes)))
                return lst
            else:
                print("something is wrong: SelAxes()")
        return

    def DrawDXF(self, width, height, _filename):

        filepath_pdf = f"{_filename}.pdf" 
        filepath_dxf = f"{_filename}.dxf" 
        self.DrawFrame(width, height) 

        # 1. create the render context
        context = RenderContext(self.doc)
        # 2. create the backend
        backend = pymupdf.PyMuPdfBackend()
        # 3. create the frontend
        cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
        frontend = Frontend(context, backend, config=cfg)
        # 4. draw the modelspace
        frontend.draw_layout(self.msp)
        # 5. create a page layout
        page = layout.Page(width, height, layout.Units.mm, margins=layout.Margins.all(0))
        # 6. get the PDF rendering as bytes
        pdf_bytes = backend.get_pdf_bytes(page)

        with open(filepath_pdf, "wb") as fp:
            fp.write(pdf_bytes)

        self.doc.saveas(filepath_dxf) 
        print("pdf created.")

        # fig = plt.figure()
        # ax = fig.add_axes([0,0,3,3])
        # ctx = RenderContext(self.doc)
        # out = MatplotlibBackend(ax)
        # Frontend(ctx, out).draw_layout(self.msp, finalize=True)
        # fig.show()

        return

    def DrawFrame(self, width, height):

        margin_h = self.margin_h
        margin_v = self.margin_v
        height_v_band = self.height_v_band

        self.msp.add_lwpolyline([(10, 0), (0, 0), (0, 10)], 
                           dxfattribs={'layer': '01_Frame', 'lineweight': 5})
        self.msp.add_lwpolyline([(width-10, 0), (width, 0), (width, 10)], 
                           dxfattribs={'layer': '01_Frame', 'lineweight': 5})
        self.msp.add_lwpolyline([(width, height-10), (width, height), (width-10, height)], 
                           dxfattribs={'layer': '01_Frame', 'lineweight': 5})
        self.msp.add_lwpolyline([(10, height), (0, height), (0, height-10)], 
                           dxfattribs={'layer': '01_Frame', 'lineweight': 5})

        self.msp.add_lwpolyline([(margin_h, margin_v), 
                            (width-margin_h, margin_v), 
                            (width-margin_h, height-margin_v),
                            (margin_h, height-margin_v),
                            (margin_h, margin_v)
                            ], dxfattribs={'layer': '01_Frame', 'lineweight': 5})
        
        self.msp.add_line((margin_h, margin_v+height_v_band), (width-margin_h, margin_v+height_v_band), 
                     dxfattribs={'layer': '01_Frame', 'lineweight': 5})
        
        return 
    
    def DrawForce(self, _lc, _deffac, _elms, _plt): 
            
            clc = self.mdl.lcs.index(_lc) 
            disp_fac = _deffac / _plt.scale
            relevant_elms = _elms
            div_num = 8 
            ax = list(filter(lambda a: a.id == _plt.axis_id, self.mdl.axes))[0]
            
            if clc == None: return

            for e in relevant_elms:

                isElmYDir = False

                els = list(filter(lambda el: (el.clc == clc) and (el.eid == e.id), self.mdl.elds))
                lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

                for el in els: 

                    el_lds = np.array(el.lds).reshape(6, 1)
                    if el.isGlobal == True: el_lds = e.tm[0:6, 0:6] @ el_lds
                    for i in range(6): lds[i] += el_lds[i, 0]
                
                if e.glds is not None: lds += e.glds[:, clc]

                if e.alds is not None: lds += e.alds[:, clc]

                vz = np.array([e.pln.vz.v[0], e.pln.vz.v[2], 0.0]) # drawing direction of the element

                if e.isVxZ: 

                    deg = Export.DegBetweenVecs(vz, ax.pln.vx.v)
                    if abs(deg) > 45: 
                        vz = np.array([e.pln.vy.v[1], e.pln.vy.v[2], 0.0])
                        isElmYDir = True
                    else:
                        vz *= -1

                    deg = Export.DegBetweenVecs(vz, ax.pln.vx.v)
                    print(f"column deg: {deg}")

                
                p0 = np.array([e.n0.plt2d_arr[0], e.n0.plt2d_arr[1], 0.0]) #np.array([e.n0.x, e.n0.y, e.n0.z])
                p1 = np.array([e.n1.plt2d_arr[0], e.n1.plt2d_arr[1], 0.0]) #np.array([e.n1.x, e.n1.y, e.n1.z])
                
                wzi = lds[2]
                wzj = lds[5]
                
                qzi = e.forces[2][clc]
                qzj = e.forces[8][clc]
                myi = e.forces[4][clc]
                myj = e.forces[10][clc]

                wyi = lds[1]
                wyj = lds[4]
                qyi = e.forces[1][clc]
                qyj = e.forces[7][clc]
                mzi = e.forces[5][clc]
                mzj = e.forces[11][clc]

                ni  = e.forces[0][clc]
                nj  = e.forces[6][clc]

                wz_xc= wzi + (wzj - wzi) * 0.5
                my_xc= myi + qzi * 0.5 * e.len + 1.0 / 6.0 * (wzi + 2.0 * wz_xc) * (0.5*e.len)**2 

                wy_xc= wyi + (wyj - wyi) * 0.5
                mz_xc= mzi - qyi * 0.5 * e.len - 1.0 / 6.0 * (wyi + 2.0 * wy_xc) * (0.5*e.len)**2 

                mp = 0.5 * p0 + 0.5 * p1 

                spline_pts = []
                qy_max = 0.0
                qz_max = 0.0
                n_max  = 0.0
                for i in range(div_num+1):
                    t   = i / div_num
                    x   = t * e.len
                    pt  = (1-t) * p0 + t * p1

                    wz_x = wzi + (wzj - wzj) * t 
                    qz_x = -1.0 * qzi - 0.5 * (wzi + wz_x) * x
                    if abs(qz_x) > abs(qz_max):
                        qz_max = qz_x
                    my_x = myi + qzi * x + 1.0 / 6.0 * (wzi + 2.0 * wz_x) * x**2

                    wy_x = wyi + (wyj - wyi) * t
                    qy_x = -1.0 * qyi - 0.5 * (wyi + wy_x) * x
                    if abs(qy_x) > abs(qy_max):
                        qy_max = qy_x
                    mz_x = mzi - qyi * x - 1.0 / 6.0 * (wyi + 2.0 * wy_x) * x**2

                    n_x = ni + (nj - ni) * t 
                    if abs(n_x) > abs(n_max):
                        n_max = n_x

                    pt_fy = pt - disp_fac * my_x * vz 
                    pt_fz = pt - disp_fac * mz_x * vz

                    if isElmYDir == False:
                        pt_f = pt_fy
                    else:
                        pt_f = pt_fz

                    if i == 0 or i == div_num:
                        self.msp.add_line(pt, pt_f, dxfattribs={
                            "color": 1, 
                            'lineweight':'13',
                            })
                    
                    spline_pts.append([pt_f[0], pt_f[1]]) 

                for i in range(len(spline_pts)-1):
                    #print(f"{i}: {spline_pts[i]}, {spline_pts[i+1]}")
                    self.msp.add_line(spline_pts[i], spline_pts[i+1], 
                                      dxfattribs={
                                          "color": 1, 
                                          'lineweight':'13',
                                          })
                    
                vx = np.array([1.0, 0.0])
                ev = e.n1.plt2d_arr - e.n0.plt2d_arr 
                deg = Export.DegBetweenVecs(vx, ev)
                if deg > 90: deg = 180 - deg
                if ev[1] < PRES_ZERO: deg *= -1
                if ev[0] < PRES_ZERO: deg *= -1

                ### value text - bending moment (Mz or My)
                for i in range(3):

                    if (e.sec.name.startswith("V")): continue

                    if i == 0: 

                        tpt = p0.copy()
                        
                        if isElmYDir == False:
                            val = myi
                        else:
                            val = mzi

                        if e.isVxZ or e.sec.name.startswith("C"):
                            
                            if e.n0.plt2d_arr[1] > e.n1.plt2d_arr[1]: # column, top to btm
                                ali = TextEntityAlignment.TOP_RIGHT 
                            else:
                                tpt += np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.BOTTOM_LEFT
                            deg = 0.0
                        else: # beam
                            
                            if e.n0.plt2d_arr[0] > e.n1.plt2d_arr[0]:
                                ali = TextEntityAlignment.BOTTOM_RIGHT # beam, right side is n0
                            else:
                                ali = TextEntityAlignment.TOP_LEFT
                    elif i == 1: 

                        tpt  = mp.copy()

                        if isElmYDir == False:
                            val = my_xc
                        else:
                            val = mz_xc
                        
                        if e.isVxZ or e.sec.name.startswith("C"):
                            ali = TextEntityAlignment.MIDDLE_RIGHT
                        else:
                            ali = TextEntityAlignment.TOP_CENTER

                    else: # i==2

                        tpt  = p1.copy()
                        
                        if isElmYDir == False:
                            val = myj
                        else:
                            val = mzj

                        if e.isVxZ or e.sec.name.startswith("C"):
                            
                            if e.n0.plt2d_arr[1] > e.n1.plt2d_arr[1]: 
                                tpt += np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.BOTTOM_LEFT
                            else:
                                ali = TextEntityAlignment.TOP_RIGHT
                            deg = 0.0
                        else:
                            if e.n0.plt2d_arr[0] > e.n1.plt2d_arr[0]: # beam, left side is n1
                                ali = TextEntityAlignment.TOP_LEFT
                            else:
                                ali = TextEntityAlignment.BOTTOM_RIGHT

                    if abs(val) < PRES_ZERO: 
                        val = "0"
                    else: 
                        val = f"{val * 1e-3:.1f}" 

                    self.msp.add_text(f"{val}", 
                                    dxfattribs={
                                        'style': 'Standard',
                                        'height': 1.5,
                                        'width': 0.65,
                                        'rotation': deg 
                                    }).set_placement(tpt, align=ali) 
                
                ### value text - normal forces (N)
                val = n_max
                tptn  = mp.copy()
                if e.isVxZ or e.sec.name.startswith("C"):
                    ali = TextEntityAlignment.MIDDLE_LEFT
                else:
                    ali = TextEntityAlignment.BOTTOM_CENTER

                if abs(val) < PRES_ZERO: 
                        val = "0"
                else: 
                    val = f"{val * 1e-3:.1f}N" 

                self.msp.add_text(f"{val}", 
                                dxfattribs={
                                    'style': 'Standard',
                                    'height': 1.5,
                                    'width': 0.65,
                                    'rotation': deg 
                                }).set_placement(tptn, align=ali) 

                ### value text - shearing forces (Vz or Vy)
                for i in range(2):

                    if (e.sec.name.startswith("V")): continue

                    if i == 0: 

                        tpts = p0.copy()

                        if isElmYDir == False:
                            val = qzi
                            if abs(val) < PRES_ZERO: val = "0"
                            else: val = f"({val * 1e-3:.1f})" 

                        else:
                            val = qyi
                            if abs(val) < PRES_ZERO: val = "0"
                            else: val = f"({val * 1e-3:.1f})" 

                        if e.isVxZ or e.sec.name.startswith("C"):
                            
                            if e.n0.plt2d_arr[1] > e.n1.plt2d_arr[1]: # column, top to btm
                                tpts -= np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.TOP_RIGHT 
                            else:
                                ali = TextEntityAlignment.BOTTOM_LEFT # column, btm to top

                            deg = 0.0

                        else: # beam
                            if e.n0.plt2d_arr[0] > e.n1.plt2d_arr[0]:
                                tpts += np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.BOTTOM_RIGHT
                            else:
                                tpts -= np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.TOP_LEFT
                    else: # i==1

                        tpts = p1.copy()

                        if isElmYDir == False:
                            val = qzj
                            if abs(val) < PRES_ZERO: val = "0"
                            else: val = f"({val * 1e-3:.1f})" 

                        else:
                            val = qyj
                            if abs(val) < PRES_ZERO: val = "0"
                            else: val = f"({val * 1e-3:.1f})" 

                        if e.isVxZ or e.sec.name.startswith("C"):

                            if e.n0.plt2d_arr[1] > e.n1.plt2d_arr[1]:
                                ali = TextEntityAlignment.BOTTOM_LEFT
                            else:
                                tpts -= np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.TOP_RIGHT

                            deg = 0.0
                        else:
                            if e.n0.plt2d_arr[0] > e.n1.plt2d_arr[0]:
                                tpts -= np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.TOP_LEFT
                            else:
                                tpts += np.array([0, 1.8, 0])
                                ali = TextEntityAlignment.BOTTOM_RIGHT

                    #np.set_printoptions(precision=1, suppress=True)
                    #print(f"tpts: {tpts}, e: {e.id}, i: {i}, p0: {p0}, p1: {p1}")
                    self.msp.add_text(f"{val}", 
                                    dxfattribs={
                                        'style': 'Standard',
                                        'height': 1.5,
                                        'width': 0.65,
                                        'rotation': deg 
                                    }).set_placement(tpts, align=ali)
                    
