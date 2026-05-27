import os
import sys

# GPU が原因の不具合が疑われる場合のフォールバック:
#   STB_FORCE_SOFTWARE_GL=1 python main_frame.py
if (
    sys.platform.startswith("linux")
    and os.environ.get("STB_FORCE_SOFTWARE_GL") == "1"
):
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

# wxVTK + VTK の X 系レンダラは Wayland 上の GTK(EGL) と相性が悪く、
# BadWindow / "failed to get the converted tmp" が出る。
# Wayland セッションでは強制的に X11 バックエンド(=XWayland)を使う。
# 既存値が空文字や "wayland" のときも必ず上書きする。
# ユーザーが明示的に X11 を抜けたい場合は STB_ALLOW_WAYLAND=1 を立てる。
if (
    sys.platform.startswith("linux")
    and os.environ.get("WAYLAND_DISPLAY")
    and os.environ.get("STB_ALLOW_WAYLAND") != "1"
):
    os.environ["GDK_BACKEND"] = "x11"

# 小数スケール + VTK で同種エラーが出る場合: STB_GTK_INTEGER_SCALE=1 で整数スケールを試す
if sys.platform.startswith("linux") and os.environ.get("STB_GTK_INTEGER_SCALE") == "1":
    os.environ.setdefault("GDK_SCALE", "1")
    os.environ.setdefault("GDK_DPI_SCALE", "1")

import wx

from ui_classes.event_handlers import EventHandlersMixin
from ui_classes.ui_init import UIInitMixin

class MainFrame(wx.Frame, UIInitMixin, EventHandlersMixin):

    def __init__(self):
        super().__init__(None)

        self.SetTitle("Structural Toolbox")
        self.SetSize((1600, 900))
        self.SetIcon(wx.Icon(r"./ui_classes/icons/icon.png", wx.BITMAP_TYPE_PNG))
        self.Maximize(True)

        # common settings
        self.Reset()
        self.InitUI()

    def Reset(self): 

        self.font          = "Miro"

        self.font_txtfield =  wx.Font(10,
                        wx.FONTFAMILY_TELETYPE, 
                        wx.FONTSTYLE_NORMAL, 
                        wx.FONTWEIGHT_NORMAL)
        
        self.colors = {
            "background": "#E1DEE4", 
            "node": "#666666",
            "element": "#666666",
            "support": "#5eff4d", 
            "load": "red",
            "deform": "#8648d2",
            "txt-id": "#000000", 
            "force-d": "#0047AB"
        }
        # "deform": "#666666",

        self.size = {
            "txt3d": 0.06,
            "txt3d-s": 0.04,
            "txt2d": 0.50,
            "txtflg": 1.0, # 0.67,
            "line-weight": 1.5,
            "line-weight-thin": 1.0,
            "node-radius": 0.015,
            "joint-radius": 0.010,
        }

        # if sys.platform == "darwin":  # macOS
        #     self.size["txt3d"]       = 1.0 * self.size["txt3d"]
        #     self.size["txt2d"]       = 2.0 * self.size["txt2d"]
        #     self.font_txtfield.SetPointSize(12)  
        #     self.size["line-weight"] = 2.0 * self.size["line-weight"]

        self.isParallelProjection = False 

        self.mdl          =  None
        self.txt3d_nids   =  None
        self.txt3d_eids   =  None
        self.txt3d_sids   =  None
        self.txt3d_stags  =  None
        self.txt3d_mids   =  None
        self.txt3d_mtags  =  None
        self.txt3d_cons   =  None
        self.vedo_frame_objs =  None # vedo objects
        self.jnts         =  None # vedo objects
        self.eplns        =  None

        self.filepath     =  None
        self.isdrawn      =  False
        self.buttons      =  None #[0,0,0,0,0,0,0] 

        self.lc           =  None
        self.clc          =  None

        self.isModelSolved=  False
        self.def_factor   =  20.0
        self.frc_factor   =  8.0
        self.def_graphics =  None
        self.lds_graphics =  None
        self.frc_graphics =  None
        self.incl_lst     =  None
        self.excl_lst     =  None

        self.input_txt    =  None
        self.output_txt   =  None

        return
 
if __name__ == '__main__':
    try:
        from vtkmodules.vtkCommonCore import vtkObject

        vtkObject.GlobalWarningDisplayOff()
    except Exception:
        pass
    app = wx.App(redirect=False)
    frame = MainFrame()
    frame.Show(True)
    app.MainLoop()