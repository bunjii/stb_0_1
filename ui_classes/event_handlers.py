import sys
#import resource
sys.path.append('./classes')
sys.path.append('./ui_classes')

import numpy as np
import wx
import vedo
import pickle

from classes.io import ReadLines, RegisterInputData, RegisterResultData
from classes.solve import Solve
from classes.export import Export

class EventHandlersMixin:

    def ToggleResultsDisplay(self):
        if self.tabs_results.IsShown():
            self.tabs_results.Hide()
            self.splitter_r.SetSashPosition(self.GetSize().GetHeight())
        else:
            self.tabs_results.Show()
            self.splitter_r.SetSashPosition(-300)  

        self.splitter_r.Layout() 
        self.tabR1.Layout() 

    def OnResize(self, event):
        if hasattr(self, 'splitter_r'):
            new_size = self.GetSize()
            self.splitter_r.SetSashPosition(new_size[1] - 300, True)
            self.splitter_r.UpdateSize()
        event.Skip()  

    def OnViewXYPlane(self, event):

        if self.plt is not None:
            self.plt.camera.SetPosition(0, 0, 1)
            self.plt.camera.SetViewUp(0, 1, 0)
            self.plt.camera.SetFocalPoint(0, 0, 0)
            self.plt.reset_camera()
            self.plt.interactor.Render()

        return
    
    def OnViewYZPlane(self, event):

        if self.plt is not None:
            self.plt.camera.SetPosition(1, 0, 0)
            self.plt.camera.SetViewUp(0, 0, 1)
            self.plt.camera.SetFocalPoint(0, 0, 0)
            self.plt.reset_camera()
            self.plt.interactor.Render()

        return
    
    def OnViewZXPlane(self, event):

        if self.plt is not None:
            self.plt.camera.SetPosition(0, -1, 0)
            self.plt.camera.SetViewUp(0, 0, 1)
            self.plt.camera.SetFocalPoint(0, 0, 0)
            self.plt.reset_camera()
            self.plt.interactor.Render()

        return

    def OnViewEntity(self, event):

        if self.plt is not None:
            self.plt.reset_camera()
            self.plt.interactor.Render()

        return
        
    def OnClickOpenFile(self, e):
        dlg = wx.FileDialog(None, u"Select file")
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()

            if path.endswith('.stb'): 
                with open(path, 'rb') as f:
                    data = pickle.load(f)

                self.SetData(data)

            elif path.endswith('.dat') or path.endswith('.csv'):  
                with open(path, 'r') as f:
                    txt = f.read()

                self.OnClickNew(None)
                self.wx_txt_input.SetText(txt)
                self.tabs_results.SetSelection(0)

        dlg.Destroy()

    def OnClickSave(self, e): 

        if self.filepath == None:

            dlg = wx.FileDialog(
                parent = None, 
                message = "Save File As", 
                defaultFile =  "new file 1.stb", 
                wildcard="STB files (*.stb)|*.stb|All files (*.*)|*.*", 
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
                )
            
            if dlg.ShowModal() == wx.ID_OK:

                self.filepath = dlg.GetPath()

            dlg.Destroy()

        data = self.CreateDataToSave()
        sys.setrecursionlimit(10**6)
        with open(self.filepath, 'wb') as f:
            pickle.dump(data, f)
        
        self.SetTitle(f"Structural Toolbox :: {self.filepath}")

        return
    
    def OnClickSaveAs(self, e):

        dlg = wx.FileDialog(
            parent = None, 
            message = "Save File As", 
            defaultFile =  "new file 1.stb",
            wildcard="STB files (*.stb)|*.stb|All files (*.*)|*.*", 
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )
        
        if dlg.ShowModal() == wx.ID_OK:

            self.filepath = dlg.GetPath()

        dlg.Destroy()

        data = self.CreateDataToSave()
        sys.setrecursionlimit(10**6)
        with open(self.filepath, 'wb') as f:
            pickle.dump(data, f)

        self.SetTitle(f"Structural Toolbox :: {self.filepath}")

        return
    
    def OnRadioJnt(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioJnt(id)

        return
    
    def OnRadioLd(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioLd(id)

        return
    
    def OnToggleDisp(self, e):

        if self.tab_post_rbs[0].GetValue() == True:
            self.RadioDisp(1)
            self.tab_post_rbs[1].SetValue(True)

        elif self.tab_post_rbs[1].GetValue() == True:
            self.RadioDisp(0)
            self.tab_post_rbs[0].SetValue(True)

        return
    
    def OnDef0SliderScroll(self, e):
        
        self.UpdateEDisp()

        return

    def OnDef1SliderScroll(self, e):
        
        self.UpdateEDisp()

        return

    def OnRadioFrcGroup(self, e):
        
        id = e.GetEventObject().GetId()
        id = id%10 

        self.frc_factor = self.sld3.GetValue()

        self.RadioForce(id)

        return
    
    def OnFrcDviSliderScroll(self, e): 
        
        id = self.GetRadioForceId()
        self.RadioForce(id)

        return

    def OnFrcSliderScroll(self, e):

        val = e.GetEventObject().GetValue()
        self.frc_factor = val

        id = self.GetRadioForceId()

        self.RadioForce(id)

        return

    def OnRadioDisp(self, e):
        
        id = e.GetEventObject().GetId()
        self.RadioDisp(id)

        return
    
    def OnRadioNID(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioNID(id)

        return
    
    def OnRadioEID(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioEID(id)

        return
    
    def OnRadioMID(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioMID(id)

        return
    
    def OnRadioSID(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioSID(id)

        return
    
    def OnRadioCons(self, e):

        id = e.GetEventObject().GetId()
        id = id%10
        self.RadioCons(id)

        return

    def OnClickPlot(self, e):

        self._init_vedo_plotter_if_needed()
        self.plt.clear()

        if self.mdl == None: 
            return
        
        self.vedo_frame_objs = []

        # relevant elements

        if self.incl_lst is None: 
            incl_elms = self.mdl.elms
        elif len(self.incl_lst) == 0:
            incl_elms = self.mdl.elms
        else:
            incl_elms = list(filter(lambda e: e.sec.name in self.incl_lst, self.mdl.elms))

        if self.excl_lst is None:
            relevant_elms = incl_elms
        elif len(self.excl_lst) == 0:
            relevant_elms = incl_elms
        else:
            relevant_elms = list(filter(lambda e: e.sec.name not in self.excl_lst, incl_elms))

        ### plot axis ### 
        self.DrawAxes()
        
        ### plot node ###
        nds = self.mdl.nds
        cons = self.mdl.cons 
        cons_nds = list(map(lambda c: c.nd, cons))
        nds_free = list(filter(lambda n: n not in cons_nds, nds))
        # nds_to_plot = []
        # for n in nds_free:
        #     if any(e in n.elms for e in relevant_elms):
        #         nds_to_plot.append(n)
        relevant_nds = []
        for e in relevant_elms:
            if e.n0 not in relevant_nds: relevant_nds.append(e.n0)
            if e.n1 not in relevant_nds: relevant_nds.append(e.n1)

        pts_free = []
        for n in nds_free:
            if n in relevant_nds:
                pts_free.append((n.x, n.y, n.z))

        #pts_free = list(map(lambda n: (n.x, n.y, n.z) , nds_to_plot))

        if len(pts_free) != 0:
            self.vedo_frame_objs.append(vedo.Spheres(pts_free, r=self.size["node-radius"], c=self.colors["node"])) 
        
        ### plot support ###
        nds_fixed = list(map(lambda c: c.nd, cons)) 
        # nds_fixed_to_plot = []
        # for n in nds_fixed:
        #     if any(e in n.elms for e in relevant_elms):
        #         nds_fixed_to_plot.append(n)

        # pts_fixed = list(map(lambda n: (n.x, n.y, n.z) , nds_fixed_to_plot))

        pts_fixed = []
        for n in nds_fixed:
            if n in relevant_nds:
                pts_fixed.append((n.x, n.y, n.z))

        for pf in pts_fixed:
            self.vedo_frame_objs.append(vedo.Cube(pf, side=2.0*self.size["node-radius"], c=self.colors["support"]))

        ### plot element ###
        # sps = list(map(lambda e: (e.n0.x, e.n0.y, e.n0.z), self.mdl.elms))
        # eps = list(map(lambda e: (e.n1.x, e.n1.y, e.n1.z), self.mdl.elms))
        sps = list(map(lambda e: (e.n0.x, e.n0.y, e.n0.z), relevant_elms))
        eps = list(map(lambda e: (e.n1.x, e.n1.y, e.n1.z), relevant_elms))
        self.vedo_frame_objs.append(vedo.Lines(sps, eps, lw=self.size["line-weight"], c=self.colors["element"]))

        self.plt.add(self.vedo_frame_objs)
        
        if self.isdrawn == False:
            self.plt.reset_camera()

        self.isdrawn = True

        self.ApplyButtonStates()
        self.plt.interactor.Render()
        
        return

    def OnClickUpdate(self, e): 

        lns = self.wx_txt_input.GetText().split("\n")
        self.mdl = ReadLines(lns)
        self.input_txt = RegisterInputData(self.mdl)
        self.wx_txt_input.SetText(self.input_txt)
        self.isModelSolved = False

        self.OnClickPlot(e) 

        return
    
    def OnTxtDefFacEnterPressed(self, e):

        try:
            value = int(self.txtCtrl0.GetValue())
            if 0 <= value <= 200:  
                self.sld1.SetValue(value)
                self.UpdateEDisp()
                
            else:
                wx.MessageBox('Value between 1 and 200 is accepted', 'Error', wx.OK | wx.ICON_ERROR)
        
        except ValueError:
            wx.MessageBox('Input a valid integer value.', 'Error', wx.OK | wx.ICON_ERROR)

        return
    
    def OnTxtInclPressed(self, e): 

        try:
            val0 = self.txtCtrl00.GetValue()
            self.incl_lst = [x.strip() for x in val0.split(',') if x.strip()]
            #print(f"incl_lst: {self.incl_lst}, listlen: {len(self.incl_lst)}")

            val1 = self.txtCtrl01.GetValue()
            self.excl_lst = [x.strip() for x in val1.split(',') if x.strip()]
            #print(f"excl_lst: {self.excl_lst}, listlen: {len(self.excl_lst)}")

        except ValueError:
            #print(self.incl_lst)
            wx.MessageBox('Input is not valid.', 'Error', wx.OK | wx.ICON_ERROR)
        
        self.OnClickPlot(e)
        self.UpdateEDisp()
        id = self.GetRadioForceId()
        self.RadioForce(id)

        return
    
    def OnLoadSliderScroll(self, e):

        if self.tab_view_rbs[50].GetValue() == False:
            self.PlotLoad()

        return
        
    
    def OnChoice_lc(self, event): 

        id = event.GetEventObject().GetSelection()

        self.clc = id
        self.lc = self.mdl.lcs[id]

        # synchronise both choices
        self.choice_lc.SetSelection(id)
        self.choice_lc_view.SetSelection(id)

        # if Load is not hidden, plot load
        if self.tab_view_rbs[50].GetValue() == False:
            self.PlotLoad()

        # if deformation is not Hide:
        if self.tab_post_rbs[1].GetValue() == True and self.isModelSolved:
            self.PlotDisp()

        # if forces is not None:
        id = self.GetRadioForceId()
        self.RadioForce(id)

        return


    def OnClickSolve(self, e):

        if self.mdl == None:
            print("model does not exist.")
        
        else:
            lns = self.wx_txt_input.GetText().split("\n")
            self.mdl = ReadLines(lns)
            self.input_txt = RegisterInputData(self.mdl) # added 20240219

            self.mdl.filepath = self.filepath

            Solve(self.mdl, True)
            self.isModelSolved = True

            self.choice_lc.SetItems([str(item) for item in self.mdl.lcs])
            self.choice_lc.SetSelection(0)
            self.choice_lc_view.SetItems([str(item) for item in self.mdl.lcs])
            self.choice_lc_view.SetSelection(0)
            self.lc = self.mdl.lcs[0]
            self.clc = self.mdl.lcs.index(self.lc)

            self.UpdateEDisp()
            self.ApplyButtonStates()
            
            self.output_txt = RegisterResultData(self.mdl)
            self.wx_txt_output.SetText(self.output_txt)

            #self.choice_lc.SetItems([str(item) for item in self.mdl.lcs])
            
        return
    
    def OnClickNew(self, e):

        self.wx_txt_output.SetText("")
        self.wx_txt_input.SetText("")
        self.choice_lc.Clear()

        if self.widget is None and getattr(self, "_vtk_placeholder", None) is not None:
            self.Layout()
            self._mount_wxvtk_render_widget()
        if self.widget is None:
            self.Reset()
            return

        self.plt = vedo.Plotter(N=1, bg=self.colors["background"], wx_widget=self.widget)
        self._configure_embedded_vtk_render_window()
        self._apply_fixed_mouse_style()
        self.plt.interactor.Render()

        self.Reset()

    def OnClickQuit(self, e):

        dlgResult = wx.MessageBox("Are you sure to quit the program?", "confirm quitting", wx.ICON_QUESTION | wx.YES_NO, self)

        if dlgResult == wx.YES:
            self.Close()
    
    def OnCut(self, event):
        focused_widget = wx.Window.FindFocus()
        if isinstance(focused_widget, wx.stc.StyledTextCtrl):
            focused_widget.Cut()

    def OnCopy(self, event):
        focused_widget = wx.Window.FindFocus()
        if isinstance(focused_widget, wx.stc.StyledTextCtrl):
            focused_widget.Copy()

    def OnPaste(self, event):
        focused_widget = wx.Window.FindFocus()
        if isinstance(focused_widget, wx.stc.StyledTextCtrl):
            focused_widget.Paste()

    def OnRedo(self, event):
        focused_widget = wx.Window.FindFocus()
        if isinstance(focused_widget, wx.stc.StyledTextCtrl):
            focused_widget.Redo()

    def OnUndo(self, event):
        focused_widget = wx.Window.FindFocus()
        if isinstance(focused_widget, wx.stc.StyledTextCtrl):
            focused_widget.Undo()

    def OnAbout(self, event):
        message = "Structural Toolbox\n" \
                  "Version: 1.0\n" \
                  "Author: Bunji Izumi \n" \
                  "External Libraries: VTK, vedo, wxPython, numpy, scipy, pickle \n" \
                  "Icons: https://icons8.com/"
        dlg = wx.GenericMessageDialog(self, message, "About Application", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnSplitterDClick(self, event):
        event.Veto()

    def OnToggleProjection(self, event):

        self.isParallelProjection = not self.isParallelProjection
        
        if self.plt is not None:

            self.plt.camera.SetParallelProjection(self.isParallelProjection)
            self.plt.render()
    
    def OnCheckElmExtra(self, event):

        isChecked = event.IsChecked()

        if self.mdl == None: 
            return

        if isChecked:
            
            self.plt.remove(self.eplns)

            elms = self.mdl.elms

            eplns = []
            for e in elms:
                mpt = np.array([0.5*(e.n0.x + e.n1.x), 0.5*(e.n0.y + e.n1.y), 0.5*(e.n0.z + e.n1.z)])

                eplns.append(vedo.Arrow(mpt, mpt + 0.2*e.pln.vx.v, c="red",   shaft_radius=0.02, head_radius=0.1))
                eplns.append(vedo.Arrow(mpt, mpt + 0.2*e.pln.vy.v, c="green", shaft_radius=0.02, head_radius=0.1)) 
                eplns.append(vedo.Arrow(mpt, mpt + 0.2*e.pln.vz.v, c="blue",  shaft_radius=0.02, head_radius=0.1)) 

            self.eplns = eplns
            self.plt.add(self.eplns)
            self.plt.interactor.Render() 

        else:
            self.plt.remove(self.eplns)
            self.plt.interactor.Render() 
    
    def OnClickExportPlt(self, event):

        export = Export(self)
        export.DrawPages(210, 297)

        return
    
    def OnClickExportResults(self, event):

        export = Export(self)
        export.ExportResults()

        return
