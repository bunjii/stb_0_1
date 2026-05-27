import sys
#import resource

import numpy as np
import math

import wx
import wx.stc
import vedo
import vedo.vtkclasses as vtki
from vedo.plotter import runtime as _vedo_runtime
from vtkmodules.wx.wxVTKRenderWindowInteractor import wxVTKRenderWindowInteractor

from ui_classes._wxvtk_patch import patch_wxvtk_for_gtk_xid

patch_wxvtk_for_gtk_xid()


def _patch_vedo_default_keypress_none_guard():
    """vedo の既定 KeyPress ハンドラで key=None が来た場合を無視する。"""
    if getattr(_vedo_runtime, "_stb_none_key_guard_patched", False):
        return

    _orig = _vedo_runtime.Plotter._default_keypress

    def _safe_default_keypress(self, iren, event):
        try:
            key = iren.GetKeySym() if iren is not None else None
        except Exception:
            key = None
        if key is None:
            return
        return _orig(self, iren, event)

    _vedo_runtime.Plotter._default_keypress = _safe_default_keypress
    _vedo_runtime._stb_none_key_guard_patched = True


_patch_vedo_default_keypress_none_guard()

from classes.common import Vec, Plane, Pnt, PRES_LEN, PRES_ZERO
from classes.io import ReadLines, RegisterInputData, RegisterResultData
from classes.solve import Solve
from event_handlers import EventHandlersMixin

class FixedMouseStyle(vtki.vtkInteractorStyleUser):
    """Fixed interaction mapping:
    - Shift + Left drag: pan
    - Right drag: rotate
    - Mouse wheel: zoom (dolly)
    """
    def __init__(self):
        super().__init__()
        self.interactor = None
        self.renderer = None
        self._left_down = False
        self._right_down = False
        self.rotate_speed = 0.4
        self.wheel_zoom_factor = 1.15

        self.AddObserver("LeftButtonPressEvent", self._on_left_down)
        self.AddObserver("LeftButtonReleaseEvent", self._on_left_up)
        self.AddObserver("RightButtonPressEvent", self._on_right_down)
        self.AddObserver("RightButtonReleaseEvent", self._on_right_up)
        self.AddObserver("MouseWheelForwardEvent", self._on_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self._on_wheel_backward)
        self.AddObserver("MouseMoveEvent", self._on_mouse_move)

    def SetInteractor(self, interactor):
        super().SetInteractor(interactor)
        self.interactor = interactor
        renderers = self.interactor.GetRenderWindow().GetRenderers()
        self.renderer = renderers.GetFirstRenderer() if renderers else None

    def _on_left_down(self, obj, event):
        self._left_down = True

    def _on_left_up(self, obj, event):
        self._left_down = False

    def _on_right_down(self, obj, event):
        self._right_down = True

    def _on_right_up(self, obj, event):
        self._right_down = False

    def _on_wheel_forward(self, obj, event):
        self._dolly(self.wheel_zoom_factor)

    def _on_wheel_backward(self, obj, event):
        self._dolly(1.0 / self.wheel_zoom_factor)

    def _on_mouse_move(self, obj, event):
        if self.interactor is None or self.renderer is None:
            return
        if not (self._left_down or self._right_down):
            return

        last_pos = np.array(self.interactor.GetLastEventPosition(), dtype=float)
        curr_pos = np.array(self.interactor.GetEventPosition(), dtype=float)
        dx = curr_pos[0] - last_pos[0]
        dy = curr_pos[1] - last_pos[1]
        cam = self.renderer.GetActiveCamera()

        shift_pressed = bool(self.interactor.GetShiftKey())

        if self._left_down and shift_pressed:
            self._pan(last_pos, curr_pos)
        elif self._right_down:
            cam.Azimuth(-dx * self.rotate_speed)
            cam.Elevation(dy * self.rotate_speed)
            cam.OrthogonalizeViewUp()

        self.interactor.Render()

    def _dolly(self, factor):
        if self.interactor is None or self.renderer is None:
            return
        cam = self.renderer.GetActiveCamera()
        cam.Dolly(max(0.05, factor))
        self.renderer.ResetCameraClippingRange()
        self.interactor.Render()

    def _pan(self, last_pos, curr_pos):
        cam = self.renderer.GetActiveCamera()
        fp = cam.GetFocalPoint()
        pos = cam.GetPosition()

        fp_display = np.array([0.0, 0.0, 0.0], dtype=float)
        self.ComputeWorldToDisplay(self.renderer, fp[0], fp[1], fp[2], fp_display)
        focal_depth = fp_display[2]

        last_world = np.array([0.0, 0.0, 0.0, 0.0], dtype=float)
        curr_world = np.array([0.0, 0.0, 0.0, 0.0], dtype=float)
        self.ComputeDisplayToWorld(self.renderer, last_pos[0], last_pos[1], focal_depth, last_world)
        self.ComputeDisplayToWorld(self.renderer, curr_pos[0], curr_pos[1], focal_depth, curr_world)

        motion = last_world[:3] - curr_world[:3]
        cam.SetFocalPoint(np.add(fp, motion))
        cam.SetPosition(np.add(pos, motion))

class UIInitMixin(EventHandlersMixin):

    def InitUI(self):

        ### menubbar

        ## file
        m_file = wx.Menu()
        m_i_new  = m_file.Append(wx.ID_NEW, "&New\tCtrl+N", "New model")
        m_i_open = m_file.Append(wx.ID_OPEN,"&Open\tCtrl+O", "Open a file")
        m_i_save = m_file.Append(wx.ID_SAVE,"&Save\tCtrl+S", "Save a file")
        m_i_saveas = m_file.Append(wx.ID_SAVEAS,"&Save As\tCtrl+Shift+S", "Save a file")
        m_file.AppendSeparator()
        m_i_exit = m_file.Append(wx.ID_EXIT, "&Exit\tCtrl+Q", "Terminate the program")

        ## edit
        m_edit = wx.Menu()
        m_i_undo = m_edit.Append(wx.ID_UNDO, "&Undo\tCtrl+Z", "Undo last action")
        m_i_redo = m_edit.Append(wx.ID_REDO, "&Redo\tCtrl+Y", "Redo last action")
        m_edit.AppendSeparator()
        m_i_cut = m_edit.Append(wx.ID_CUT, "Cu&t\tCtrl+X", "Cut to clipboard")
        m_i_copy = m_edit.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy to clipboard")
        m_i_paste = m_edit.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste from clipboard")
        m_edit.AppendSeparator()
        m_i_update = m_edit.Append(wx.ID_ANY, "&Update\tCtrl+U", "Update the model")    
        
        ## analysis
        m_analysis = wx.Menu()
        m_i_solve = m_analysis.Append(wx.ID_ANY, "&Solve\tCtrl+R", "Solve the model")

        ## view
        m_view = wx.Menu()
        m_i_xy_plane_item = m_view.Append(wx.ID_ANY, 'XY Plane\tCtrl+1', 'View from XY Plane')
        m_i_yz_plane_item = m_view.Append(wx.ID_ANY, 'YZ Plane\tCtrl+2', 'View from YZ Plane')
        m_i_zx_plane_item = m_view.Append(wx.ID_ANY, 'ZX Plane\tCtrl+3', 'View from ZX Plane')
        m_i_view_entity   = m_view.Append(wx.ID_ANY, 'View Entity\tCtrl+4', 'View Entity')
        m_view.AppendSeparator()
        m_i_toggle_proj = m_view.Append(wx.ID_ANY, 'Toggle Projection\tCtrl+0', 'Switch between parallel and perspective projection')
        m_view.AppendSeparator()
        m_i_toggle_disp = m_view.Append(wx.ID_ANY, "&Toggle Disp\tCtrl+D", "Toggle Displacement")
        m_view.AppendSeparator()
        m_i_toggle_results = m_view.Append(wx.ID_ANY, 'Toggle Results\tCtrl+T', 'Toggle Results Display')

        ## export
        m_export = wx.Menu()
        m_i_export_plot = m_export.Append(wx.ID_ANY, 'Export Plot\tCtrl+E', 'Export Plot')
        m_i_export_results = m_export.Append(wx.ID_ANY, 'Export Results\tCtrl+Shift+E', 'Export Results')

        ## about
        m_about = wx.Menu()
        m_i_about = m_about.Append(wx.ID_ABOUT, "&About", "Info about this program")

        ## bind
        self.Bind(wx.EVT_MENU, self.OnClickQuit, m_i_exit)
        self.Bind(wx.EVT_MENU, self.OnClickNew, m_i_new)
        self.Bind(wx.EVT_MENU, self.OnClickSolve, m_i_solve)      
        self.Bind(wx.EVT_MENU, self.OnUndo, m_i_undo)
        self.Bind(wx.EVT_MENU, self.OnRedo, m_i_redo)
        self.Bind(wx.EVT_MENU, self.OnCut, m_i_cut)
        self.Bind(wx.EVT_MENU, self.OnCopy, m_i_copy)
        self.Bind(wx.EVT_MENU, self.OnPaste, m_i_paste)
        self.Bind(wx.EVT_MENU, self.OnClickUpdate, m_i_update)
        self.Bind(wx.EVT_MENU, self.OnViewXYPlane, m_i_xy_plane_item)
        self.Bind(wx.EVT_MENU, self.OnViewYZPlane, m_i_yz_plane_item)
        self.Bind(wx.EVT_MENU, self.OnViewZXPlane, m_i_zx_plane_item)
        self.Bind(wx.EVT_MENU, self.OnClickOpenFile, m_i_open)
        self.Bind(wx.EVT_MENU, self.OnClickSave, m_i_save)
        self.Bind(wx.EVT_MENU, self.OnToggleDisp, m_i_toggle_disp)
        self.Bind(wx.EVT_MENU, self.OnViewEntity, m_i_view_entity)
        self.Bind(wx.EVT_MENU, self.OnAbout, m_i_about)
        self.Bind(wx.EVT_MENU, self.OnClickSaveAs, m_i_saveas)
        self.Bind(wx.EVT_MENU, lambda event: self.ToggleResultsDisplay(), m_i_toggle_results)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        self.Bind(wx.EVT_MENU, self.OnToggleProjection, m_i_toggle_proj)
        self.Bind(wx.EVT_MENU, self.OnClickExportPlt, m_i_export_plot)
        self.Bind(wx.EVT_MENU, self.OnClickExportResults, m_i_export_results)

        menubar = wx.MenuBar()
        menubar.Append(m_file,  "&File")
        menubar.Append(m_edit,  "&Edit")
        menubar.Append(m_analysis, "&Analysis")
        menubar.Append(m_view, '&View')
        menubar.Append(m_export, "&Export")
        menubar.Append(m_about, "&About")
        self.SetMenuBar(menubar)

        ### toolbar 
        self.toolbar = self.CreateToolBar(wx.TB_DEFAULT_STYLE | wx.NO_BORDER)
        self.toolbar.SetToolBitmapSize((24, 24))

        newIcon = UIInitMixin.ResizeBitmap('./ui_classes/icons/ic_new.png', 24, 24)
        newTool = self.toolbar.AddTool(wx.ID_ANY, 'New', newIcon, shortHelp="new file")
        self.Bind(wx.EVT_TOOL, self.OnClickNew, newTool)

        saveTool = self.toolbar.AddTool(wx.ID_ANY, 'Save', wx.Bitmap('./ui_classes/icons/ic_save.png'), shortHelp="save file")
        self.Bind(wx.EVT_TOOL, self.OnClickSave, saveTool)

        saveasTool = self.toolbar.AddTool(wx.ID_ANY, 'Save As', wx.Bitmap('./ui_classes/icons/ic_saveas.png'), shortHelp="save file as...")
        self.Bind(wx.EVT_TOOL, self.OnClickSaveAs, saveasTool)

        openTool = self.toolbar.AddTool(wx.ID_ANY, 'Open', wx.Bitmap('./ui_classes/icons/ic_open.png'), shortHelp="open a file")
        self.Bind(wx.EVT_TOOL, self.OnClickOpenFile, openTool)

        updateTool = self.toolbar.AddTool(wx.ID_ANY, 'Update', wx.Bitmap('./ui_classes/icons/ic_update.png'), shortHelp="update model")
        self.Bind(wx.EVT_TOOL, self.OnClickUpdate, updateTool)

        solveTool = self.toolbar.AddTool(wx.ID_ANY, 'Solve', wx.Bitmap('./ui_classes/icons/ic_solve.png'), shortHelp="solve model")
        self.Bind(wx.EVT_TOOL, self.OnClickSolve, solveTool)

        self.toolbar.AddSeparator()

        aboutTool = self.toolbar.AddTool(wx.ID_ANY, 'About', wx.Bitmap('./ui_classes/icons/ic_about.png'), shortHelp="about")
        self.Bind(wx.EVT_TOOL, self.OnAbout, aboutTool)

        if sys.platform != "darwin":  # macOS
            self.toolbar.Realize()

        ### window frame
        splitter = wx.SplitterWindow(self)
        nb_left  = wx.Notebook(splitter)
        nb_right = wx.Notebook(splitter)
        splitter.SplitVertically(nb_left, nb_right, 480)
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.OnSplitterDClick)
        ### left frame ###

        ## Tab Left #1

        tab_pre   = wx.Panel(nb_left)
        btnL1_0 = wx.Button(tab_pre, -1, "new"   , pos=( 10,10), size=(100,30))
        btnL1_1 = wx.Button(tab_pre, -1, "save"  , pos=(120,10), size=(100, 30))
        btnL1_2 = wx.Button(tab_pre, -1, "open"  , pos=(230,10), size=(100, 30))
        btnL1_3 = wx.Button(tab_pre, -1, "update", pos=( 10,50), size=(100, 30)) 
        btnL1_4 = wx.Button(tab_pre, -1, "solve" , pos=(120,50), size=(100, 30))
        btnL1_0.Bind(wx.EVT_BUTTON, self.OnClickNew )
        btnL1_1.Bind(wx.EVT_BUTTON, self.OnClickSave)
        btnL1_2.Bind(wx.EVT_BUTTON, self.OnClickOpenFile)
        btnL1_3.Bind(wx.EVT_BUTTON, self.OnClickUpdate)
        btnL1_4.Bind(wx.EVT_BUTTON, self.OnClickSolve)

        ## Tab Left #3
        tab_input = wx.Panel(nb_left)
        vb1 = wx.BoxSizer(wx.VERTICAL)
        vb1.Add((-1, 10))
        hb1 = wx.BoxSizer(wx.HORIZONTAL)
        tab_input_btn = wx.Button(tab_input, -1, "update", pos=(10, 10), size=(100, 30)) 
        tab_input_btn.Bind(wx.EVT_BUTTON, self.OnClickUpdate)

        hb1.Add(tab_input_btn, 0, wx.Left | wx.Top )
        vb1.Add(hb1, 0, wx.LEFT, 10)
        vb1.Add((-1, 10))

        hb2 = wx.BoxSizer(wx.HORIZONTAL)

        self.wx_txt_input = wx.stc.StyledTextCtrl(tab_input)
        self.wx_txt_input.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, self.font_txtfield)
        self.wx_txt_input.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        self.wx_txt_input.SetUseHorizontalScrollBar(False)
        self.wx_txt_input.SetMarginWidth(1, 0)

        hb2.Add(self.wx_txt_input, 1, wx.EXPAND, 20)
        vb1.Add(hb2, 11, wx.EXPAND)
        tab_input.SetSizer(vb1) 
        
        ## Tab Left #3 
        tab_view = wx.Panel(nb_left) 
        self.tab_view_rbs = {}
        bx_view = wx.BoxSizer(wx.VERTICAL) 

        bx_view.AddSpacer(20) 
        #------------------- Material
        txt = wx.StaticText(tab_view, label = "Material", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_mat = wx.Panel(tab_view)
        self.tab_view_rbs[0] = wx.RadioButton(pnl_rb_mat, 0, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[1] = wx.RadioButton(pnl_rb_mat, 1, label = 'Show ID', pos = (90, 10)) 
        self.tab_view_rbs[2] = wx.RadioButton(pnl_rb_mat, 2, label = 'Show Tag', pos = (170, 10)) 
        pnl_rb_mat.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioMID)
        bx_view.Add(pnl_rb_mat, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)
        
        bx_view.AddSpacer(20)

        #------------------- Section
        txt = wx.StaticText(tab_view, label = "Section", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_sec = wx.Panel(tab_view)
        self.tab_view_rbs[10] = wx.RadioButton(pnl_rb_sec, 10, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[11] = wx.RadioButton(pnl_rb_sec, 11, label = 'Show ID', pos = (90, 10)) 
        self.tab_view_rbs[12] = wx.RadioButton(pnl_rb_sec, 12, label = 'Show Tag', pos = (170, 10)) 
        pnl_rb_sec.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioSID)
        bx_view.Add(pnl_rb_sec, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        bx_view.AddSpacer(20)

        #------------------- Node
        txt = wx.StaticText(tab_view, label = "Node", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_nd = wx.Panel(tab_view)
        self.tab_view_rbs[20] = wx.RadioButton(pnl_rb_nd, 20, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[21] = wx.RadioButton(pnl_rb_nd, 21, label = 'Show ID', pos = (90, 10)) 
        self.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioNID)
        bx_view.Add(pnl_rb_nd, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        bx_view.AddSpacer(20)

        #------------------- Element
        txt = wx.StaticText(tab_view, label = "Element", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_elm = wx.Panel(tab_view)
        self.tab_view_rbs[30] = wx.RadioButton(pnl_rb_elm, 30, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[31] = wx.RadioButton(pnl_rb_elm, 31, label = 'Show ID', pos = (90, 10)) 
        pnl_rb_elm.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioEID)
        bx_view.Add(pnl_rb_elm, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        chk_elm_extra = wx.CheckBox(pnl_rb_elm, label='Show LCS', pos=(210, 10))
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckElmExtra, chk_elm_extra)

        bx_view.AddSpacer(20)

        #------------------- Support
        txt = wx.StaticText(tab_view, label = "Support", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_sup = wx.Panel(tab_view)
        self.tab_view_rbs[40] = wx.RadioButton(pnl_rb_sup, 40, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[41] = wx.RadioButton(pnl_rb_sup, 41, label = 'Show ID', pos = (90, 10)) 
        pnl_rb_sup.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioCons)
        bx_view.Add(pnl_rb_sup, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        bx_view.AddSpacer(20)

        #------------------- Load
        txt = wx.StaticText(tab_view, label = "Load", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_ld = wx.Panel(tab_view)
        self.tab_view_rbs[50] = wx.RadioButton(pnl_rb_ld, 50, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[51] = wx.RadioButton(pnl_rb_ld, 51, label = 'Show Graphics', pos = (90, 10)) 
        self.tab_view_rbs[52] = wx.RadioButton(pnl_rb_ld, 52, label = 'Show Value', pos = (210, 10)) 
        pnl_rb_ld.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioLd)
        bx_view.Add(pnl_rb_ld, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        bx_view.AddSpacer(10)

        lcs = [] 

        txt = wx.StaticText(tab_view, label = "Load case", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 30) 
        
        self.choice_lc_view = wx.Choice(tab_view, choices = lcs)
        self.choice_lc_view.SetMinSize((100, 20)) 
        bx_view.Add(self.choice_lc_view, 0, wx.LEFT|wx.RIGHT, 30)  
        self.choice_lc_view.Bind(wx.EVT_CHOICE, self.OnChoice_lc)

        bx_view.AddSpacer(10)

        txt = wx.StaticText(tab_view, label = "Display factor", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt, 0,wx.EXPAND|wx.LEFT|wx.RIGHT, 30) 
        
        self.sld_view_0 = wx.Slider(tab_view, value = 10, minValue = 1, maxValue = 100,
            style = wx.SL_HORIZONTAL|wx.SL_TICKS|wx.SL_LABELS) 
                
        bx_view.Add(self.sld_view_0, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 30) 
        self.sld_view_0.Bind(wx.EVT_SLIDER, self.OnLoadSliderScroll) 

        bx_view.AddSpacer(20)

        #------------------- Joint
        txt = wx.StaticText(tab_view, label = "Joint", style = wx.ALIGN_LEFT) 
        bx_view.Add(txt,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl_rb_jnt = wx.Panel(tab_view)
        self.tab_view_rbs[60] = wx.RadioButton(pnl_rb_jnt, 60, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_view_rbs[61] = wx.RadioButton(pnl_rb_jnt, 61, label = 'Show Graphics', pos = (90, 10)) 
        self.tab_view_rbs[62] = wx.RadioButton(pnl_rb_jnt, 62, label = 'Show Value', pos = (210, 10)) 
        pnl_rb_jnt.Bind(wx.EVT_RADIOBUTTON,  self.OnRadioJnt)
        bx_view.Add(pnl_rb_jnt, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        bx_view.AddSpacer(20)

        tab_view.SetSizer(bx_view)

        ##
        ## Tab Left #4
        ##

        tab_post = wx.Panel(nb_left) 
        box = wx.BoxSizer(wx.VERTICAL) 
        self.tab_post_rbs = {}

        box.AddSpacer(20)

        #---------------- Load case
        lcs = [] 

        txt0 = wx.StaticText(tab_post, label = "Load case", style = wx.ALIGN_LEFT) 
        box.Add(txt0,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        box.AddSpacer(10)

        self.choice_lc = wx.Choice(tab_post, choices = lcs)
        self.choice_lc.SetMinSize((100, 20)) 
        box.Add(self.choice_lc, 0, wx.LEFT|wx.RIGHT, 30)  
        self.choice_lc.Bind(wx.EVT_CHOICE, self.OnChoice_lc)

        box.AddSpacer(20)

        #---------------- Visual Elements

        txt01 = wx.StaticText(tab_post, label = "Element inclusion list", style = wx.ALIGN_LEFT) 
        box.Add(txt01,0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        #box.AddSpacer(10)

        self.txtCtrl00 = wx.TextCtrl(tab_post, style=wx.TE_PROCESS_ENTER)
        self.txtCtrl00.SetMinSize((200, 20)) 
        self.txtCtrl00.Bind(wx.EVT_TEXT_ENTER, self.OnTxtInclPressed) 
        box.Add(self.txtCtrl00, 0, wx.LEFT | wx.RIGHT, 30)

        box.AddSpacer(10)

        txt02 = wx.StaticText(tab_post, label = "Exclusion list", style = wx.ALIGN_LEFT) 
        box.Add(txt02,0,wx.EXPAND|wx.LEFT|wx.Right, 20)
        #box.AddSpacer(10)

        self.txtCtrl01 = wx.TextCtrl(tab_post, style=wx.TE_PROCESS_ENTER)
        self.txtCtrl01.SetMinSize((200, 20)) 
        self.txtCtrl01.Bind(wx.EVT_TEXT_ENTER, self.OnTxtInclPressed) 
        box.Add(self.txtCtrl01, 0, wx.LEFT | wx.RIGHT, 30)

        box.AddSpacer(20)

        #---------------- Deformation
        txt1 = wx.StaticText(tab_post, label = "Deformation", style = wx.ALIGN_LEFT) 
        box.Add(txt1, 0,wx.EXPAND|wx.LEFT|wx.Right, 20) 
        pnl0 = wx.Panel(tab_post)
        self.tab_post_rbs[0] = wx.RadioButton(pnl0, 0, label = 'Hide', pos = (10, 10), style = wx.RB_GROUP) 
        self.tab_post_rbs[1] = wx.RadioButton(pnl0, 1, label = 'Show', pos = (70, 10)) 
        pnl0.Bind(wx.EVT_RADIOBUTTON, self.OnRadioDisp)
        box.Add(pnl0, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        box.AddSpacer(10)

        txt2a = wx.StaticText(tab_post, label = "Element division", style = wx.ALIGN_LEFT) 
        box.Add(txt2a, 0,wx.EXPAND|wx.LEFT|wx.RIGHT, 30) 
        
        self.sld0 = wx.Slider(tab_post, value = 8, minValue = 1, maxValue = 16,
            style = wx.SL_HORIZONTAL|wx.SL_TICKS|wx.SL_LABELS) 
                
        box.Add(self.sld0, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 30) 
        self.sld0.Bind(wx.EVT_SLIDER, self.OnDef0SliderScroll) 

        box.AddSpacer(10)

        txt2b = wx.StaticText(tab_post, label = "Deformation factor", style = wx.ALIGN_LEFT) 
        box.Add(txt2b, 0,wx.EXPAND|wx.LEFT|wx.RIGHT, 30) 
        
        self.sld1 = wx.Slider(tab_post, value = 50, minValue = 1, maxValue = 200,
            style = wx.SL_HORIZONTAL|wx.SL_TICKS|wx.SL_LABELS) 
                
        box.Add(self.sld1, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 30) 
        self.sld1.Bind(wx.EVT_SLIDER, self.OnDef1SliderScroll) 

        self.txtCtrl0 = wx.TextCtrl(tab_post, style=wx.TE_PROCESS_ENTER)
        self.txtCtrl0.SetMinSize((50, 20)) 
        self.txtCtrl0.Bind(wx.EVT_TEXT_ENTER, self.OnTxtDefFacEnterPressed) 
        box.Add(self.txtCtrl0, 0, wx.LEFT | wx.RIGHT, 30)

        #---------------- Forces
        box.AddSpacer(20)

        txt3 = wx.StaticText(tab_post, label = "Forces", style = wx.ALIGN_LEFT) 
        box.Add(txt3, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20) 

        pnl1 = wx.Panel(tab_post)
        self.tab_post_rbs[10] = wx.RadioButton(pnl1, 10, label = 'None', pos = ( 10, 10), style = wx.RB_GROUP) 
        self.tab_post_rbs[11] = wx.RadioButton(pnl1, 11, label = 'Nx',   pos = ( 10, 40)) 
        self.tab_post_rbs[12] = wx.RadioButton(pnl1, 12, label = 'Vy',   pos = ( 70, 40)) 
        self.tab_post_rbs[13] = wx.RadioButton(pnl1, 13, label = 'Vz',   pos = (130, 40)) 
        self.tab_post_rbs[14] = wx.RadioButton(pnl1, 14, label = 'Mx',   pos = (190, 40)) 
        self.tab_post_rbs[15] = wx.RadioButton(pnl1, 15, label = 'My',   pos = (250, 40)) 
        self.tab_post_rbs[16] = wx.RadioButton(pnl1, 16, label = 'Mz',   pos = (310, 40)) 
        pnl1.Bind(wx.EVT_RADIOBUTTON, self.OnRadioFrcGroup)
        box.Add(pnl1, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 20)

        box.AddSpacer(10)

        txt4 = wx.StaticText(tab_post, label = "Element division", style = wx.ALIGN_LEFT)
        box.Add(txt4, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 30)
        self.sld2 = wx.Slider(tab_post, value = 8, minValue = 1, maxValue = 16,
            style = wx.SL_HORIZONTAL|wx.SL_TICKS|wx.SL_LABELS) 
                
        box.Add(self.sld2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 30) 
        self.sld2.Bind(wx.EVT_SLIDER, self.OnFrcDviSliderScroll) 

        txt5 = wx.StaticText(tab_post, label = "Display factor", style = wx.ALIGN_LEFT) 
        box.Add(txt5, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 30) 
        self.sld3 = wx.Slider(tab_post, value = 10, minValue = 1, maxValue = 100,
            style = wx.SL_HORIZONTAL|wx.SL_TICKS|wx.SL_LABELS) 
                
        box.Add(self.sld3, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 30) 
        self.sld3.Bind(wx.EVT_SLIDER, self.OnFrcSliderScroll) 

        self.txtCtrl1 = wx.TextCtrl(tab_post, style=wx.TE_PROCESS_ENTER)
        self.txtCtrl1.SetMinSize((50, 20)) 
        box.Add(self.txtCtrl1, 0, wx.LEFT | wx.RIGHT, 30)
        
        tab_post.SetSizer(box) 

        nb_left.AddPage(tab_pre, "pre")
        nb_left.AddPage(tab_input, "input")
        nb_left.AddPage(tab_view, "view")
        nb_left.AddPage(tab_post, "post")

        ### right frame ###
        
        ## Right frame #1
        self.tabR1   = self.VedoWindow(nb_right) 
        nb_right.AddPage(self.tabR1, "3d model")

        _root = wx.BoxSizer(wx.VERTICAL)
        _root.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(_root)

    def VedoWindow(self, parent):

        panel = wx.Panel(parent, -1)
        self.splitter_r = wx.SplitterWindow(panel)

        self._vtk_placeholder = wx.Panel(self.splitter_r, -1)
        self._vtk_placeholder.SetMinSize((200, 200))
        self.widget = None
        self._wxvtk_mounted = False

        self.plt = None
        self._vedo_startup_ready = False

        # Result window
        self.tabs_results = wx.Notebook(self.splitter_r)

        self.wx_txt_output = wx.stc.StyledTextCtrl(self.tabs_results)
        self.wx_txt_output.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, self.font_txtfield)
        self.wx_txt_output.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        self.wx_txt_output.SetUseHorizontalScrollBar(False)
        self.wx_txt_output.SetMarginWidth(1, 0)
        self.tabs_results.AddPage(self.wx_txt_output, "output")

        self.splitter_r.SplitHorizontally(self._vtk_placeholder, self.tabs_results, -300)
        self.splitter_r.Bind(wx.EVT_SPLITTER_DCLICK, self.OnSplitterDClick)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.splitter_r, 1, wx.EXPAND)
        panel.SetSizer(sizer)

        # wxVTK wires the X11/GL window on first EVT_PAINT; vedo.Render()
        # before that causes vtkXOpenGLRenderWindow BadWindow. Wait until
        # the frame is shown and the GL area has a non-zero client size.
        self._vedo_sched_attempts = 0
        wx.CallAfter(self._schedule_vedo_init_after_realize)

        return panel

    def _schedule_vedo_init_after_realize(self):
        if getattr(self, "_vedo_startup_ready", False):
            return
        self._vedo_sched_attempts = getattr(self, "_vedo_sched_attempts", 0) + 1
        if self._vedo_sched_attempts > 120:
            return
        if not self.IsShown():
            wx.CallLater(20, self._schedule_vedo_init_after_realize)
            return
        self.Layout()
        if not self._wxvtk_mounted:
            ph = getattr(self, "_vtk_placeholder", None)
            if ph is None:
                return
            w, h = ph.GetClientSize()
            if w < 3 or h < 3:
                wx.CallLater(20, self._schedule_vedo_init_after_realize)
                return
            self._mount_wxvtk_render_widget()
            wx.CallLater(80, self._schedule_vedo_init_after_realize)
            return

        if not hasattr(self, "widget") or self.widget is None:
            return
        w, h = self.widget.GetClientSize()
        if w < 3 or h < 3:
            wx.CallLater(20, self._schedule_vedo_init_after_realize)
            return
        self.widget.Refresh(eraseBackground=False)
        wx.CallLater(120, self._init_vedo_plotter_if_needed)

    def _mount_wxvtk_render_widget(self):
        if getattr(self, "_wxvtk_mounted", False):
            return
        ph = getattr(self, "_vtk_placeholder", None)
        if ph is None:
            return
        vk = wxVTKRenderWindowInteractor(self.splitter_r, -1)
        vk.Enable(1)
        vk.AddObserver("ExitEvent", lambda o, e, f=self: f.Close())
        self.splitter_r.ReplaceWindow(ph, vk)
        self._vtk_placeholder = None
        self.widget = vk
        self._wxvtk_mounted = True

    def _configure_embedded_vtk_render_window(self):
        """wx 埋め込み時、MSAA 付き FBConfig で vtkXOpenGLRenderWindow が失敗することがある。"""
        vedo.settings.multi_samples = 0
        try:
            rw = self.widget.GetRenderWindow()
            if rw is not None:
                rw.SetMultiSamples(0)
        except Exception:
            pass

    def _init_vedo_plotter_if_needed(self):
        if getattr(self, "_vedo_startup_ready", False):
            return
        if self.plt is not None:
            self._vedo_startup_ready = True
            return
        if getattr(self, "_vtk_placeholder", None) is not None and not self._wxvtk_mounted:
            self._mount_wxvtk_render_widget()
        if not hasattr(self, "widget") or self.widget is None:
            return
        self.plt = vedo.Plotter(N=1, bg=self.colors["background"], wx_widget=self.widget)
        self._configure_embedded_vtk_render_window()
        self.plt.show(interactive=False)
        self.plt.reset_camera()
        self._apply_fixed_mouse_style()
        self.plt.interactor.Render()
        self._vedo_startup_ready = True

    def _apply_fixed_mouse_style(self):
        if self.plt is None or self.plt.interactor is None:
            return
        self.plt.user_mode(FixedMouseStyle())
    
    def DrawAxes(self):

        axes = []
        axes.append(vedo.Arrow((0,0,0), (0.3,0,0), c="red"  , shaft_radius=0.01, head_radius=0.05, head_length=0.2))
        axes.append(vedo.Arrow((0,0,0), (0,0.3,0), c="green", shaft_radius=0.01, head_radius=0.05, head_length=0.2))
        axes.append(vedo.Arrow((0,0,0), (0,0,0.3), c="blue" , shaft_radius=0.01, head_radius=0.05, head_length=0.2))

        self.plt.add(axes)

        return

    def ResizeBitmap(file_path, width, height):
        img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
        img = img.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(img)
    
    def CreateDataToSave(self):

        data = [
            self.mdl, 
            self.filepath,
            self.buttons 
        ]
 
        return data
    
    def SetData(self, data):

        if self.mdl is not None:
            self.OnClickNew(None)

        self.mdl = data[0]
        self.filepath = data[1]
        self.buttons = data[2]

        self.SetTitle(f"Structural Toolbox :: {self.filepath}")

        if self.input_txt is None:
            self.input_txt = RegisterInputData(self.mdl)
            
        self.wx_txt_input.SetText(self.input_txt)
        
        self.choice_lc.SetItems([str(item) for item in self.mdl.lcs])
        self.choice_lc.SetSelection(0)
        self.choice_lc_view.SetItems([str(item) for item in self.mdl.lcs])
        self.choice_lc_view.SetSelection(0)
        self.lc = self.mdl.lcs[0]
        self.clc = self.mdl.lcs.index(self.lc)

        self.OnClickPlot(None)  # clears plt area, draw frame

        if self.tab_view_rbs[50].GetValue() == False:
            self.PlotLoad()
        
        if self.mdl.date_analysis is not None:
            self.output_txt = RegisterResultData(self.mdl)
            self.wx_txt_output.SetText(self.output_txt)
            
            self.UpdateEDisp()      # this includes PlotDisp()
            self.tab_post_rbs[1].SetValue(True)

        return    

    def SaveButtonStates(self):

        trueids_view = list(dict(filter(lambda i: i[1].GetValue() == True,
                                   self.tab_view_rbs.items())).keys())
        
        trueids_post = list(dict(filter(lambda i: i[1].GetValue() == True,
                                   self.tab_post_rbs.items())).keys())
        
        self.buttons = [trueids_view, trueids_post]
    
    def ApplyButtonStates(self):
    
        if self.buttons is None: return

        trueids_view = self.buttons[0]
        for id in trueids_view:

            self.tab_view_rbs[id].SetValue(True) # apply each button state

            if   id < 10: self.RadioMID(id%10)  # material
            elif id < 20: self.RadioSID(id%10)  # section
            elif id < 30: self.RadioNID(id%10)  # node
            elif id < 40: self.RadioEID(id%10)  # element
            elif id < 50: self.RadioCons(id%10) # support
            elif id < 60: self.RadioLd(id%10)   # load
            elif id < 70: self.RadioJnt(id%10)  # joint

        trueids_post = self.buttons[1]
        for id in trueids_post:
            
            self.tab_post_rbs[id].SetValue(True) # apply each button state

            if   id < 10: self.RadioDisp(id%10)  # deformation
            elif id < 20: self.RadioForce(id%10) # force

    def RadioCons(self, id):

        self.SaveButtonStates()

        if self.mdl == None:
            return
        
        if id == 0:

            self.plt.remove(self.txt3d_cons)
            self.plt.interactor.Render()

        elif id == 1:

            # relevant elements
            relevant_elms = self.GetRelevantElms()

            # relevant nodes
            relevant_nds = self.GetRelevantNds(relevant_elms)

            relevant_cons = list(filter(lambda c: c.nd in relevant_nds, self.mdl.cons))

            cons = list(map(lambda c: 
                            str(int(c.csts[0]))+
                            str(int(c.csts[1]))+
                            str(int(c.csts[2]))+
                            str(int(c.csts[3]))+
                            str(int(c.csts[4]))+
                            str(int(c.csts[5]))
                            , relevant_cons))
            
            consnds = list(map(lambda c:
                               c.nd, relevant_cons))
            
            pts = list(map(lambda n: (
                n.x + 1.1*self.size["node-radius"],
                n.y - 0.2*self.size["node-radius"],
                n.z
            ), consnds))

            self.txt3d_cons = []
            for i in range(len(cons)):
                const = cons[i]
                pos = pts[i]
                txt = vedo.Text3D(const, pos=pos, s=0.7*self.size["txt3d"], c=self.colors["txt-id"], 
                                  justify='top-left', font=self.font)
                self.txt3d_cons.append(txt)
        
            self.plt.add(self.txt3d_cons)
            self.plt.interactor.Render() 

        return

    def GetRadioForceId(self):

        for i in range(7):
            if self.tab_post_rbs[10+i].GetValue() == True:
                return i
            
        return
    
    def RadioForce(self, id): 

        if self.mdl == None: return
        
        if id == 0:

            self.plt.remove(self.frc_graphics)
            self.plt.interactor.Render() 
            return
        
        # relevant elements
        relevant_elms = self.GetRelevantElms()

        if len(relevant_elms) == 0: 
            print("num remaining element is zero")
            return

        bb      = self.mdl.bounds
        elds    = self.mdl.elds
        div_num = self.sld2.GetValue()

        matrices = list(map(lambda e: e.forces, relevant_elms))

        max_mcs = [] # max moment at each element center
        if id in [1, 2, 3]: # kN
            rows = [0, 1, 2, 6, 7, 8]
        else:               # kNm
            rows = [3, 4, 5, 9, 10, 11] 

            mcs = []
            #for e in self.mdl.elms:
            for e in relevant_elms:
                for i in range(len(self.mdl.lcs)): 

                    els = list(filter(lambda el: (el.clc == i) and (el.eid == e.id), elds))
                    lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

                    #print(f"els: {els}")

                    for el in els: 
                        el_lds = np.array(el.lds).reshape(6, 1)

                        if el.isGlobal == True: 
                            el_lds = e.tm[0:6, 0:6] @ el_lds

                        for j in range(6): 
                            lds[j] += el_lds[j, 0]
                            #print(f"el_lds: {el_lds[j, 0]} added")

                    ### i doubt if this is necessary as glds are added in elds
                    if e.glds is not None:
                        num_cols = e.glds.shape[1]
                        if i < num_cols: lds += e.glds[:, i]
                        #print(f"glds: {e.glds[:, i]} added")

                    wzi, wzj = lds[2], lds[5]
                    wyi, wyj = lds[1], lds[4]

                    qzi = e.forces[2][i]
                    myi = e.forces[4][i]
                    qyi = e.forces[1][i]
                    mzi = e.forces[5][i]

                    w_xc= wzi + (wzj - wzi) * 0.5 
                    m_xc= myi + qzi * 0.5 * e.len + 1.0 / 6.0 * (wzi + 2 * w_xc) * (0.5*e.len)**2 
                    mcs.append(abs(m_xc))
                    w_xc= wyi + (wyj - wyi) * 0.5
                    m_xc= mzi - qyi * 0.5 * e.len - 1.0 / 6.0 * (wyi + 2 * w_xc) * (0.5*e.len)**2 
                    mcs.append(abs(m_xc))

            max_mcs = max(mcs)
            
        max_abs_values = [np.max(np.abs(matrix[rows])) for matrix in matrices]
        overall_max_abs_value = max(max_abs_values + max_mcs)
        disp_fac = 0.1 * self.frc_factor * 0.1 * max([abs(bb[1]-bb[0]), abs(bb[3]-bb[2]), abs(bb[5]-bb[4])]) / overall_max_abs_value
        
        if id == 1: #Nx

            if self.clc == None: return
            self.plt.remove(self.frc_graphics)

            frc_graphics = []
            txt2d  = f"ELEMENT FORCE: Nx [kN] \n"
            txt2d += f"LODE CASE: {self.mdl.lcs[self.clc]}" 
            frc_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="bottom-left", c=self.colors["txt-id"], font="Arial"))

            for e in relevant_elms:

                vz = e.pln.vz.v 

                if e.isVxZ and e.pln.vx.v[2] < PRES_ZERO:
                    vz = -1 * vz

                p0 = np.array([e.n0.x, e.n0.y, e.n0.z])
                p1 = np.array([e.n1.x, e.n1.y, e.n1.z])

                ni = e.forces[0][self.clc]
                nj = e.forces[6][self.clc]

                n_xc= 0.5 * ni + 0.5 * nj 
                mp  = 0.5 * p0 + 0.5 * p1 + disp_fac * n_xc * vz

                spline_pts = []
                for i in range(div_num+1):
                    t   = i / div_num
                    x   = t * e.len
                    pt  = (1-t) * p0 + t * p1
                    n_x = ni + (nj - ni) * t 

                    pt_f = pt + disp_fac * n_x * vz

                    frc_graphics.append(vedo.Line(pt, pt_f, lw=self.size["line-weight-thin"], c=self.colors["force-d"]))
                    spline_pts.append(pt_f) 

                frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))

                ### value text
                for i in range(3):
                    if i == 0: 
                        val = ni
                        pt  = spline_pts[0]
                    elif i == 1: 
                        val = n_xc
                        pt  = mp
                    else: 
                        val = nj
                        pt  = spline_pts[-1]

                    if abs(val) < PRES_ZERO: val = "0"
                    else: val = f"{val * 1e-3:.1f}"

                    if self.isParallelProjection:
                        txtsize = self.size["txtflg"]
                    else:
                        txtsize = 0.5 * self.size["txtflg"]

                    frc_graphics.append(UIInitMixin.TxtFlg(val, pt, txtsize, self.font))

            self.frc_graphics = frc_graphics
            self.plt.add(self.frc_graphics)
            self.plt.interactor.Render() 
        
        elif id == 2: #Vy

            if self.clc == None: return
            self.plt.remove(self.frc_graphics)

            frc_graphics = []
            txt2d  = f"ELEMENT FORCE: Vy [kN] \n"
            txt2d += f"LODE CASE: {self.mdl.lcs[self.clc]}" 
            frc_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="bottom-left", c=self.colors["txt-id"], font="Arial"))

            for e in relevant_elms:

                els = list(filter(lambda el: (el.clc == self.clc) and 
                                  (el.eid == e.id), elds))
                
                lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

                for el in els: 
                    el_lds = np.array(el.lds).reshape(6, 1)
                    if el.isGlobal == True: el_lds = e.tm[0:6, 0:6] @ el_lds
                    for i in range(6): lds[i] += el_lds[i, 0]

                vy = e.pln.vy.v # drawing direction
                p0 = np.array([e.n0.x, e.n0.y, e.n0.z])
                p1 = np.array([e.n1.x, e.n1.y, e.n1.z])

                wyi = lds[1]
                wyj = lds[4]

                qyi = e.forces[1][self.clc]
                qyj = e.forces[7][self.clc]

                w_xc= wyi + (wyj - wyi) * 0.5
                q_xc = 1.0 * qyi + 0.5 * (wyi + w_xc) * 0.5 * e.len ###
                mp = 0.5 * p0 + 0.5 * p1 + (disp_fac * q_xc) * vy

                spline_pts = []
                for i in range(div_num+1):
                    t   = i / div_num
                    x   = t * e.len
                    pt  = (1-t) * p0 + t * p1
                    w_x = wyi + (wyj - wyi) * t
                    q_x = 1.0 * qyi + 0.5 * (wyi + w_x) * x

                    pt_f = pt + disp_fac * q_x * vy
                    frc_graphics.append(vedo.Line(pt, pt_f, lw=self.size["line-weight-thin"], c=self.colors["force-d"]))
                    spline_pts.append(pt_f) 

                frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))

                ### value text
                for i in range(3):
                    if i == 0: 
                        val = qyi
                        pt  = spline_pts[0]
                    elif i == 1: 
                        val = q_xc
                        pt  = mp
                    else: 
                        val = qyj
                        pt  = spline_pts[-1]

                    if abs(val) < PRES_ZERO: val = "0"
                    else: val = f"{val * 1e-3:.1f}"

                    if self.isParallelProjection:
                        txtsize = self.size["txtflg"]
                    else:
                        txtsize = 0.5 * self.size["txtflg"]

                    frc_graphics.append(UIInitMixin.TxtFlg(val, pt, txtsize, self.font))

            self.frc_graphics = frc_graphics
            self.plt.add(self.frc_graphics)
            self.plt.interactor.Render() 

        elif id == 3: #Vz

            if self.clc == None: return
            self.plt.remove(self.frc_graphics)

            frc_graphics = []
            txt2d  = f"ELEMENT FORCE: Vz [kN] \n"
            txt2d += f"LODE CASE: {self.mdl.lcs[self.clc]}" 
            frc_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="bottom-left", c=self.colors["txt-id"], font="Arial"))

            for e in relevant_elms:

                els = list(filter(lambda el: (el.clc == self.clc) and 
                                  (el.eid == e.id), elds))
                
                lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

                for el in els: 
                    el_lds = np.array(el.lds).reshape(6, 1)
                    
                    if el.isGlobal == True: el_lds = e.tm[0:6, 0:6] @ el_lds
                    for i in range(6): lds[i] += el_lds[i, 0]

                vz = e.pln.vz.v # drawing direction
                p0 = np.array([e.n0.x, e.n0.y, e.n0.z])
                p1 = np.array([e.n1.x, e.n1.y, e.n1.z])

                wzi = lds[2]
                wzj = lds[5]

                qzi = e.forces[2][self.clc]
                qzj = e.forces[8][self.clc]

                w_xc= wzi + (wzj - wzi) * 0.5
                q_xc = -1.0 * qzi - 0.5 * (wzi + w_xc) * 0.5 * e.len
                mp = 0.5 * p0 + 0.5 * p1 + (disp_fac * q_xc) * vz

                spline_pts = []
                for i in range(div_num+1):
                    t   = i / div_num
                    x   = t * e.len
                    pt  = (1-t) * p0 + t * p1
                    w_x = wzi + (wzj - wzi) * t
                    q_x = -1.0 * qzi - 0.5 * (wzi + w_x) * x

                    pt_f = pt + disp_fac * q_x * vz
                    frc_graphics.append(vedo.Line(pt, pt_f, lw=self.size["line-weight-thin"], c=self.colors["force-d"]))
                    spline_pts.append(pt_f) 

                frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))

                ### value text
                for i in range(3):
                    if i == 0: 
                        val = qzi
                        pt  = spline_pts[0]
                    elif i == 1: 
                        val = q_xc
                        pt  = mp
                    else: 
                        val = qzj
                        pt  = spline_pts[-1]

                    if abs(val) < PRES_ZERO: val = "0"
                    else: val = f"{val * 1e-3:.1f}"

                    if self.isParallelProjection:
                        txtsize = self.size["txtflg"]
                    else:
                        txtsize = 0.5 * self.size["txtflg"]

                    frc_graphics.append(UIInitMixin.TxtFlg(val, pt, txtsize, self.font))

            self.frc_graphics = frc_graphics

            self.plt.add(self.frc_graphics)
            self.plt.interactor.Render() 

        elif id == 4: #Mx 

            print("Mx")

            if self.clc == None: return

            self.plt.remove(self.frc_graphics)

            frc_graphics = []
            txt2d  = f"ELEMENT FORCE: Mx [KNm] \n"
            txt2d += f"LODE CASE: {self.mdl.lcs[self.clc]}" 
            frc_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="bottom-left", c=self.colors["txt-id"], font="Arial"))

            self.frc_graphics = frc_graphics
            self.plt.interactor.Render() 

        elif id == 5: #My

            if self.clc == None: return
            self.plt.remove(self.frc_graphics)

            frc_graphics = []
            txt2d  = f"ELEMENT FORCE: My [kNm] \n"
            txt2d += f"LODE CASE: {self.mdl.lcs[self.clc]}" 
            frc_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="bottom-left", c=self.colors["txt-id"], font="Arial"))

            #for e in self.mdl.elms:     
            for e in relevant_elms:

                els = list(filter(lambda el: (el.clc == self.clc) and (el.eid == e.id), elds))
                
                lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

                for el in els: 

                    el_lds = np.array(el.lds).reshape(6, 1)
                    if el.isGlobal == True: 
                        el_lds = e.tm[0:6, 0:6] @ el_lds
                    for i in range(6): 
                        lds[i] += el_lds[i, 0]
                
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
                for i in range(div_num+1):
                    t   = i / div_num
                    x   = t * e.len
                    pt  = (1-t) * p0 + t * p1
                    w_x = wzi + (wzj - wzj) * t
                    m_x = myi + qzi * x + 1.0 / 6.0 * (wzi + 2.0 * w_x) * x**2

                    pt_f = pt - disp_fac * m_x * vz
                    frc_graphics.append(vedo.Line(pt, pt_f, lw=self.size["line-weight-thin"], c=self.colors["force-d"]))
                    spline_pts.append(pt_f) 

                frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))
                
                ### value text
                for i in range(3):
                    if i == 0: 
                        val = myi
                        pt  = spline_pts[0]
                    elif i == 1: 
                        val = m_xc
                        pt  = mp
                    else: 
                        val = myj
                        pt  = spline_pts[-1]

                    if abs(val) < PRES_ZERO: val = "0"
                    else: val = f"{val * 1e-3:.1f}" 

                    if self.isParallelProjection:
                        txtsize = self.size["txtflg"]
                    else:
                        txtsize = 0.5 * self.size["txtflg"]

                    frc_graphics.append(UIInitMixin.TxtFlg(val, pt, txtsize, self.font))

            self.frc_graphics = frc_graphics
            self.plt.add(self.frc_graphics)
            self.plt.interactor.Render() 

        elif id == 6: #Mz

            if self.clc == None: return
            self.plt.remove(self.frc_graphics)

            frc_graphics = []
            txt2d  = f"ELEMENT FORCE: Mz [kNm] \n"
            txt2d += f"LODE CASE: {self.mdl.lcs[self.clc]}" 
            frc_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="bottom-left", c=self.colors["txt-id"], font="Arial"))

            #for e in self.mdl.elms: 
            for e in relevant_elms:

                els = list(filter(lambda el: (el.clc == self.clc) and 
                                  (el.eid == e.id), elds))
                
                lds = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

                for el in els: 
                    el_lds = np.array(el.lds).reshape(6, 1)
                    
                    if el.isGlobal == True: el_lds = e.tm[0:6, 0:6] @ el_lds
                    for i in range(6): lds[i] += el_lds[i, 0]
                
                if e.glds is not None: lds += e.glds[:, self.clc]

                vy = e.pln.vy.v # drawing direction

                if e.isVxZ: vy = -1 * vy

                p0 = np.array([e.n0.x, e.n0.y, e.n0.z])
                p1 = np.array([e.n1.x, e.n1.y, e.n1.z])

                wyi = lds[1]
                wyj = lds[4]
                
                qyi = e.forces[1][self.clc]
                mzi = e.forces[5][self.clc]
                mzj = e.forces[11][self.clc]

                w_xc= wyi + (wyj - wyi) * 0.5
                m_xc= mzi - qyi * 0.5 * e.len - 1.0 / 6.0 * (wyi + 2.0 * w_xc) * (0.5*e.len)**2 
                mp = 0.5 * p0 + 0.5 * p1 + (disp_fac * m_xc) * vy

                spline_pts = []
                for i in range(div_num+1):
                    t   = i / div_num
                    x   = t * e.len
                    pt  = (1-t) * p0 + t * p1
                    w_x = wyi + (wyj - wyi) * t
                    m_x = mzi - qyi * x - 1.0 / 6.0 * (wyi + 2.0 * w_x) * x**2

                    pt_f = pt + disp_fac * m_x * vy
                    frc_graphics.append(vedo.Line(pt, pt_f, lw = self.size["line-weight-thin"], c=self.colors["force-d"]))
                    spline_pts.append(pt_f)
                
                frc_graphics.append(vedo.KSpline(spline_pts).color(self.colors["force-d"]).lw(self.size["line-weight-thin"]))

                ### value text
                for i in range(3):
                    if i == 0: 
                        val = mzi
                        pt  = spline_pts[0]
                    elif i == 1: 
                        val = m_xc
                        pt  = mp
                    else: 
                        val = mzj
                        pt  = spline_pts[-1]

                    if abs(val) < PRES_ZERO: val = "0" 

                    else: val = f"{val * 1e-3:.1f}"

                    if self.isParallelProjection:
                        txtsize = self.size["txtflg"]
                    else:
                        txtsize = 0.5 * self.size["txtflg"]

                    frc_graphics.append(UIInitMixin.TxtFlg(val, pt, txtsize, self.font))

            self.frc_graphics = frc_graphics
            self.plt.add(self.frc_graphics)
            self.plt.interactor.Render() 

        return
    
    @staticmethod
    def TxtFlg(_txt, _pos, _size, _font):

        flagpost = vedo.Flagpost(_txt, base = _pos, top=[_pos[0], _pos[1], _pos[2] + 0.1], s=_size, font=_font, c="white", bc="black") 

        return flagpost

    def UpdateEDisp(self):

        if self.isModelSolved == False:
            return

        elem_div_num     = self.sld0.GetValue()
        self.def_factor  = self.sld1.GetValue()

        Solve.SetElemDisps(self.mdl, self.def_factor, elem_div_num) 

        if (self.tab_post_rbs[1].GetValue() == True):
            self.PlotDisp()

        return
    
    def PlotDisp(self):

        self.plt.remove(self.def_graphics) 

        if self.isModelSolved == False: return

        lc = self.clc

        def_graphics = [] 

        # relevant elements
        relevant_elms = self.GetRelevantElms()
        # print(f"relevant_elms: {relevant_elms}")

        def_v_max = np.array([0.0,0.0,0.0])
        defmax_pt = None
        defmax_pt_ini = None
        txt_elm = None
        dot_pts = []
        
        for e in relevant_elms:

            edisp = e.edisps[lc]
            
            pts = list(map(lambda p: (p.x, p.y, p.z), edisp))

            sps = pts[: -1]
            eps = pts[1:  ]
            def_graphics.append(vedo.Lines(sps, eps, lw=self.size["line-weight"], c=self.colors["deform"]))
            def_graphics.append(vedo.Cube(pts[ 0], side=0.75*self.size["node-radius"], c=self.colors["deform"]))
            def_graphics.append(vedo.Cube(pts[-1], side=0.75*self.size["node-radius"], c=self.colors["deform"])) 

            # def_max
            len_pts = len(e.edisps[lc])
            spt = (e.n0.x, e.n0.y, e.n0.z)
            ept = (e.n1.x, e.n1.y, e.n1.z)

            for i in range(len_pts):
                n = i / (len_pts-1)
                pt_ini = np.array([(1-n)*spt[0] + n*ept[0], (1-n)*spt[1] + n*ept[1], (1-n)*spt[2] + n*ept[2]])
                pt_def = e.edisps[lc][i].arr #Common.Pnt 
                v = (pt_def - pt_ini) / self.def_factor * 1000
                vlen = np.linalg.norm(v)
                if np.linalg.norm(def_v_max) < vlen:
                    def_v_max = v
                    defmax_pt = pt_def
                    txt_elem = f"ON ELEM ID: {e.id}, SEGMENT #{i}"
                    dot_pts = [pt_ini, pt_def]

        line = vedo.Line(dot_pts[0], dot_pts[1], c=self.colors["deform"], lw=self.size["line-weight"]).pattern('- ', repeats=20)
        
        def_graphics.append(line)
        def_max = np.linalg.norm(def_v_max)
        def_max = f"{def_max:.3f}"
        def_graphics.append(UIInitMixin.TxtFlg(def_max, defmax_pt, self.size["txtflg"], self.font))

        txt2d  = f"DEFORMATION x {self.def_factor}\n"
        txt2d += f"LODE CASE: {self.mdl.lcs[lc]}\n" 
        txt2d += f"MAX DISPL: {def_v_max} [mm] {txt_elem}"
        def_graphics.append(vedo.Text2D(txt2d, s=self.size["txt2d"], pos="top-left", c=self.colors["txt-id"], font="Arial"))

        if (self.jnts is not None):
            combined_objs = self.vedo_frame_objs + self.jnts
        else:
            combined_objs = self.vedo_frame_objs

        for obj in combined_objs:
            obj.alpha(0.2)

        self.def_graphics = def_graphics
        self.plt.add(self.def_graphics)
        self.plt.interactor.Render()

        return

    def RadioDisp(self, id):

        if self.mdl == None: 
            return
        
        if id == 0: 
            if (self.jnts is not None):
                combined_objs = self.vedo_frame_objs + self.jnts
            else:
                combined_objs = self.vedo_frame_objs

            for obj in combined_objs:
                obj.alpha(1.0)

            if self.def_graphics == None: 
                return

            self.plt.remove(self.def_graphics)
            self.plt.interactor.Render() 

            return

        elif id == 1:
            
            if self.clc == None: return
            self.PlotDisp()

        return

    def RadioEID(self, id): 

        self.SaveButtonStates()

        if self.mdl == None:
            return

        if id == 0:

            if self.txt3d_eids == None:
                return
            
            else:
                self.plt.remove(self.txt3d_eids)
                self.plt.interactor.Render()

        elif id == 1: 

            relevant_elms = self.GetRelevantElms()

            pts = list(map(lambda e: (
                0.4*e.n0.x + 0.6*e.n1.x,
                0.4*e.n0.y + 0.6*e.n1.y,
                0.4*e.n0.z + 0.6*e.n1.z
            ), relevant_elms))

            self.txt3d_eids = []
            for i in range(len(relevant_elms)):
                e   = self.mdl.elms[i]
                pos = pts[i]
                txt = vedo.Text3D(
                    e.id, 
                    pos=pos, 
                    s=self.size["txt3d"], 
                    c=self.colors["txt-id"], 
                    justify='bottom-center', 
                    font=self.font)
                
                txt = UIInitMixin.OrientVedoText(txt, pos, e.pln.vx.v)

                self.txt3d_eids.append(txt)

            self.plt.add(self.txt3d_eids)
            self.plt.interactor.Render()

        return
    
    def RadioJnt(self, id):

        self.SaveButtonStates()

        if self.mdl == None:
            return
        
        if id == 0: 

            if self.jnts == None: 
                return

            self.plt.remove(self.jnts)
            self.plt.interactor.Render()

            return
        
        if id == 1:

            self.plt.remove(self.jnts)
            jnt_graphics = [] 

            # relevant elements
            relevant_elms = self.GetRelevantElms()

            for e in relevant_elms:

                vx = e.pln.vx.v #np.array

                if (e.jnt.ryi != None) or (e.jnt.rzi != None):
                    n = np.array([e.n0.x, e.n0.y, e.n0.z])
                    offset = vx/np.linalg.norm(vx)*(self.size["node-radius"]+self.size["joint-radius"])
                    center = n + offset
                    jnt_graphics.append(vedo.Sphere(center, self.size["joint-radius"], c="orange"))

                if (e.jnt.ryj != None) or (e.jnt.rzj != None):
                    n = np.array([e.n1.x, e.n1.y, e.n1.z])
                    offset = vx/np.linalg.norm(vx)*(self.size["node-radius"]+self.size["joint-radius"])
                    center = n - offset
                    jnt_graphics.append(vedo.Sphere(center, self.size["joint-radius"], c="orange"))
            
            self.jnts = jnt_graphics
            self.plt.add(self.jnts)
            self.plt.interactor.Render() 

            return

        return
    
    def PlotLoad(self): 

        self.plt.remove(self.lds_graphics) 

        lc = self.lc
        div_num = 8
        factor_sld = self.sld_view_0.GetValue()

        max_plen = max(list(map(lambda l: l.pv.len, self.mdl.lds))) if self.mdl.lds else 0
        max_mlen = max(list(map(lambda l: l.mv.len, self.mdl.lds))) if self.mdl.lds else 0
        max_len  = max([max_plen, max_mlen])
        max_elen = max(list(map(lambda e: e.len, self.mdl.elds))) if self.mdl.elds else 0
        
        bb = self.mdl.bounds 
        if max_len != 0:
            factor_size   = (0.1 * factor_sld) * (0.1 * max([abs(bb[1]-bb[0]), abs(bb[3]-bb[2]), abs(bb[5]-bb[4])])/max_len) 
        else:
            factor_size   = 0

        if max_elen != 0:
            factor_size_e = (0.1 * factor_sld) * (0.1 * max([abs(bb[1]-bb[0]), abs(bb[3]-bb[2]), abs(bb[5]-bb[4])])/max_elen)
        else:
            factor_size_e = 0

        # relevant elements
        relevant_elms = self.GetRelevantElms()

        # relevant nodes
        relevant_nds = self.GetRelevantNds(relevant_elms)

        # for e in relevant_elms:
        #     if e.n0 not in relevant_nds: relevant_nds.append(e.n0)
        #     if e.n1 not in relevant_nds: relevant_nds.append(e.n1)

        ### point loading
        lds_graphics = []
        for l in self.mdl.lds:

            if l.lc != lc: continue 

            if l.nd not in relevant_nds: continue

            offset_f = Vec.amplify(l.pv, self.size["node-radius"]).v
            offset_m = Vec.amplify(l.mv, self.size["node-radius"]).v

            ept_f = np.array([l.nd.x, l.nd.y, l.nd.z]) - offset_f 
            vec_f = l.pv.v * factor_size
            len_f = l.pv.len * factor_size
            spt_f = ept_f - vec_f

            rad_s = 0.0032 
            rad_h = 0.0160
            len_h = 0.0600
            rad_sp= rad_s / len_f
            rad_hp= rad_h / len_f
            len_hp= len_h / len_f

            # load
            if offset_f is not False:
                lds_graphics.append(vedo.Arrow(spt_f, ept_f, c=self.colors["load"], 
                                               shaft_radius=rad_sp, head_radius=rad_hp, head_length=len_hp))

            # moment
            if offset_m is not False:
                ept_m = np.array([l.nd.x, l.nd.y, l.nd.z]) - offset_m
                vec_m = l.mv.v * factor_size
                len_m = l.mv.len * factor_size
                spt_m = ept_m - vec_m 

                rad_sp = rad_s / len_m
                rad_hp = rad_h / len_m
                len_hp = len_h / len_m

                offset_second_cone = Vec.amplify(l.mv, len_h).v 
                cone_pos = ept_m - 1.5 *offset_second_cone

                lds_graphics.append(vedo.Arrow(spt_m, ept_m, c=self.colors["load"], 
                                               shaft_radius=rad_sp, head_radius=rad_hp, head_length=len_hp))
                lds_graphics.append(vedo.Cone(cone_pos, r = rad_h, height=len_h, 
                                        axis=offset_second_cone, res=12, c=self.colors["load"]))

        ### beam loading
        for el in self.mdl.elds:

            if el.lc != lc: continue 

            if el.elm not in relevant_elms: continue

            e = el.elm
            lds = el.lds

            if el.isGlobal == False:
                vs = [e.pln.vx, e.pln.vy, e.pln.vz]
            else:
                vs = [Vec(1.0, 0.0, 0.0), Vec(0.0, 1.0, 0.0), Vec(0.0, 0.0, 1.0)]
            
            sp = Pnt(e.n0.x, e.n0.y, e.n0.z).arr 
            ep = Pnt(e.n1.x, e.n1.y, e.n1.z).arr 

            lx = Vec((ep - sp)[0], (ep - sp)[1], (ep - sp)[2]) 

            rad_s = 0.0032 
            rad_h = 0.0160
            len_h = 0.0600

            for i in range(3): # x, y, z direction

                if (abs(lds[i]) - PRES_LEN < 0) and (abs(lds[i+3]) - PRES_LEN < 0):
                    continue

                # for each inner division point
                for j in range(div_num + 1): 

                    t   = j / div_num
                    spt = (1.0 - t) * sp + t * ep 
                    v_amp = (1.0 - t) * lds[i] + t * lds[i+3]
                    v = vs[i].v * factor_size_e * v_amp

                    len_v = np.linalg.norm(v)

                    rad_sp= rad_s / len_v
                    rad_hp= rad_h / len_v
                    len_hp= len_h / len_v

                    if vs[i].isParallel(lx): 
                        if j == div_num: continue

                        # no bar, no filler, only arrow
                        ept = spt + v 

                        lds_graphics.append(vedo.Arrow(spt, ept, c=self.colors["load"], 
                                               shaft_radius=rad_sp, head_radius=rad_hp, head_length=len_hp))
                        
                    else:
                        # with bar, filler
                        v = vs[i].v * factor_size_e * v_amp
                        ept = spt - v

                        lds_graphics.append(vedo.Arrow(ept, spt, c=self.colors["load"], 
                                               shaft_radius=rad_sp, head_radius=rad_hp, head_length=len_hp))
                        
                if not vs[i].isParallel(lx):
                    v = vs[i].v * factor_size_e * v_amp
                    spt = sp - vs[i].v * factor_size_e * lds[i]
                    ept = ep - vs[i].v * factor_size_e * lds[i+3] 
                    vec_x = ept - spt 
                    len_x = np.linalg.norm(vec_x)

                    lds_graphics.append(vedo.Cylinder([spt, ept], r=rad_s, height=len_x, 
                                                      axis=vec_x, c=self.colors["load"], res=12))

        self.lds_graphics = lds_graphics
        self.plt.add(self.lds_graphics)
        self.plt.interactor.Render() 
        
        return

    def RadioLd(self, id): 

        self.SaveButtonStates()

        if self.mdl == None:
            return
        
        if id == 0: 

            if self.lds_graphics == None: return

            self.plt.remove(self.lds_graphics)
            self.plt.interactor.Render()

            return

        if id == 1:

            self.PlotLoad()

        if id == 2:

            pass

        return

    def RadioMID(self, id):

        self.SaveButtonStates()

        if self.mdl == None:
            return

        if id == 0:

            self.plt.remove(self.txt3d_mids)
            self.plt.remove(self.txt3d_mtags)

            self.plt.interactor.Render()

            return
        
        relevant_elms = self.GetRelevantElms()
        
        pts = list(map(lambda e: (
                0.33*e.n0.x + 0.67*e.n1.x,
                0.33*e.n0.y + 0.67*e.n1.y,
                0.33*e.n0.z + 0.67*e.n1.z)
            , relevant_elms))

        if id == 1: # id on

            self.plt.remove(self.txt3d_mtags)

            self.txt3d_mids = []

            for i in range(len(relevant_elms)):
                e = relevant_elms[i]
                mid = e.sec.mat.id
                pos = pts[i]
                txt = vedo.Text3D(
                    mid, 
                    pos=pos, 
                    s=self.size["txt3d"], 
                    c=self.colors["txt-id"], 
                    justify='top-center', 
                    font=self.font)
                
                txt = UIInitMixin.OrientVedoText(txt, pos, e.pln.vx.v)

                self.txt3d_mids.append(txt)

            self.plt.add(self.txt3d_mids)
            self.plt.interactor.Render()

        elif id == 2: # tag on

            self.plt.remove(self.txt3d_mids)

            self.txt3d_mtags = []

            for i in range(len(relevant_elms)):
                e = relevant_elms[i]
                mtag = e.sec.mat.name
                pos = pts[i]
                txt = vedo.Text3D(
                    mtag, 
                    pos=pos, 
                    s=self.size["txt3d"], 
                    c=self.colors["txt-id"], 
                    justify='top-center', 
                    font=self.font)
                
                txt = UIInitMixin.OrientVedoText(txt, pos, e.pln.vx.v)
                
                self.txt3d_mtags.append(txt)

            self.plt.add(self.txt3d_mtags)
            self.plt.interactor.Render()

        return

    def RadioNID(self, id):

        self.SaveButtonStates()

        if self.mdl == None: 
            return

        if id == 0:

            self.plt.remove(self.txt3d_nids) #.reset_camera()
            self.plt.interactor.Render()

        elif id == 1:

            relevant_elms = self.GetRelevantElms()
            relevant_nds = self.GetRelevantNds(relevant_elms)
            
            nids = list(map(lambda n: n.id ,  relevant_nds))
            pts  = list(map(lambda n: (n.x + 1.1*self.size["node-radius"], 
                                       n.y + 0.2*self.size["node-radius"], 
                                       n.z) ,  
                                       relevant_nds))

            self.txt3d_nids = []
            for i in range(len(relevant_nds)):
                nid = nids[i]
                pos = pts[i]
                txt = vedo.Text3D(nid, pos=pos, s=self.size["txt3d"], c=self.colors["txt-id"], 
                                  justify='bottom-left', font=self.font)
                self.txt3d_nids.append(txt)
        
            self.plt.add(self.txt3d_nids)
            self.plt.interactor.Render() 

        return

    def RadioSID(self, id):

        self.SaveButtonStates()

        if self.mdl == None:
            return
        

        if id == 0:

            self.plt.remove(self.txt3d_sids)
            self.plt.remove(self.txt3d_stags)

            self.plt.interactor.Render()

            return
        
        relevant_elms = self.GetRelevantElms()
        
        pts = list(map(lambda e: (
                0.75*e.n0.x + 0.25*e.n1.x,
                0.75*e.n0.y + 0.25*e.n1.y,
                0.75*e.n0.z + 0.25*e.n1.z)
            , relevant_elms))

        if id == 1: # id on

            self.plt.remove(self.txt3d_stags)

            self.txt3d_sids = []

            for i in range(len(relevant_elms)):
                e = relevant_elms[i]
                sid = e.sec.id
                pos = pts[i]
                txt = vedo.Text3D(
                    sid, 
                    pos=pos, 
                    s=self.size["txt3d"], 
                    c=self.colors["txt-id"], 
                    justify='bottom-center', 
                    font=self.font)
                
                txt = UIInitMixin.OrientVedoText(txt, pos, e.pln.vx.v)

                self.txt3d_sids.append(txt)

            self.plt.add(self.txt3d_sids)
            self.plt.interactor.Render()

        elif id == 2: # tag on

            self.plt.remove(self.txt3d_sids)

            self.txt3d_stags = []

            for i in range(len(relevant_elms)):
                e = relevant_elms[i]
                stag = e.sec.name
                pos = pts[i]
                txt = vedo.Text3D(
                    stag, 
                    pos=pos, 
                    s=self.size["txt3d"], 
                    c=self.colors["txt-id"], 
                    justify='bottom-center', 
                    font=self.font)
                
                txt = UIInitMixin.OrientVedoText(txt, pos, e.pln.vx.v)

                self.txt3d_stags.append(txt)

            self.plt.add(self.txt3d_stags)
            self.plt.interactor.Render()

        return
    
    def GetRelevantElms(self):

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

        return relevant_elms
    
    def GetRelevantNds(self, elms):

        relevant_nds = []
        for e in elms:
            if e.n0 not in relevant_nds: relevant_nds.append(e.n0)
            if e.n1 not in relevant_nds: relevant_nds.append(e.n1)

        return relevant_nds

    @staticmethod
    def OrientVedoText(_txt, _pos, _vx):

        vx    = _vx / np.linalg.norm(_vx)
        X     =  np.array([1,0,0])
        angle =  np.degrees(np.arccos(np.dot(vx, X)))

        axis  =  np.cross(X, vx)

        if (np.all(axis == 0)):
            return _txt
        else:
            return _txt.rotate(angle, axis=axis, point=_pos)
        
    @staticmethod
    def OrientVedoText2(_txt, _pos, _vh):

        vx    = _vh / np.linalg.norm(_vh)
        X     =  np.array([1,0,0])
        angle =  np.degrees(np.arccos(np.dot(vx, X)))

        axis  =  np.cross(X, vx)

        if (np.all(axis == 0)):
            return _txt
        else:
            return _txt.rotate(angle, axis=axis, point=_pos)
        
    @staticmethod
    def ForceInt(val):
        try:
            i = int(val)
            return i
        
        except ValueError:
            return False   