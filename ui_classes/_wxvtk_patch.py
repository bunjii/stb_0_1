"""wxVTKRenderWindowInteractor を VTK 9.4+ / wxGTK で動かすためのパッチ。

背景:
    この環境(wxPython 4.2.5 / wxGTK 3.2.9 / Python 3.13)では
    wx.Window.GetHandle() がバグっており、すべてのウィジェットで
    トップレベル GtkWindow に相当するポインタを返す。さらにその
    値は生 deref すると seg fault することすらある。

    一方 wx.Window.GetGtkWidget() は正しく **各ウィジェット個別の**
    GtkWidget*(GtkWindow / wxPizza など)を返す。

修正:
    Linux では wxVTKRenderWindowInteractor.GetHandle() を差し替え、
    GetGtkWidget() の値から
        1) gtk_widget_realize() (必要なら)
        2) gtk_widget_get_window() で GdkWindow を得る
        3) GdkX11Window なら gdk_x11_window_get_xid() で X11 XID を返す
    という流れで 32bit の XID を VTK に渡す。

    XID は 32bit に収まるので VTK 9.4+ の `from_chars(..., int)` が成功し、
    "vtkXOpenGLRenderWindow ERR| The result is out of range" や続く
    BadWindow を回避できる。

前提:
    Wayland セッションでも GDK_BACKEND=x11 が立っていること
    (main_frame.py で setdefault 済み)。
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import util


_libs: dict[str, ctypes.CDLL | None] = {"gtk": None, "gdk": None, "gobj": None}


def _load_libs():
    if _libs["gtk"] is None:
        for name in ("gtk-3", "gtk-x11-2.0"):
            path = util.find_library(name)
            if not path:
                continue
            try:
                lib = ctypes.CDLL(path)
                lib.gtk_widget_get_realized.restype = ctypes.c_int
                lib.gtk_widget_get_realized.argtypes = [ctypes.c_void_p]
                lib.gtk_widget_realize.restype = None
                lib.gtk_widget_realize.argtypes = [ctypes.c_void_p]
                lib.gtk_widget_get_window.restype = ctypes.c_void_p
                lib.gtk_widget_get_window.argtypes = [ctypes.c_void_p]
                lib.gtk_widget_get_parent.restype = ctypes.c_void_p
                lib.gtk_widget_get_parent.argtypes = [ctypes.c_void_p]
                _libs["gtk"] = lib
                break
            except (OSError, AttributeError):
                continue

    if _libs["gdk"] is None:
        for name in ("gdk-3", "gdk-x11-2.0"):
            path = util.find_library(name)
            if not path:
                continue
            try:
                lib = ctypes.CDLL(path)
                lib.gdk_x11_window_get_xid.restype = ctypes.c_ulong
                lib.gdk_x11_window_get_xid.argtypes = [ctypes.c_void_p]
                _libs["gdk"] = lib
                break
            except (OSError, AttributeError):
                continue

    if _libs["gobj"] is None:
        path = util.find_library("gobject-2.0")
        if path:
            try:
                lib = ctypes.CDLL(path)
                # NOTE: g_type_from_instance は libgobject 内のマクロなので CDLL からは引けない。
                # g_type_check_instance / g_type_name_from_instance は実シンボル。
                lib.g_type_check_instance.restype = ctypes.c_int
                lib.g_type_check_instance.argtypes = [ctypes.c_void_p]
                lib.g_type_name_from_instance.restype = ctypes.c_char_p
                lib.g_type_name_from_instance.argtypes = [ctypes.c_void_p]
                _libs["gobj"] = lib
            except (OSError, AttributeError):
                pass

    return _libs["gtk"], _libs["gdk"], _libs["gobj"]


def _gtype_name(addr: int) -> str | None:
    """安全に GTypeInstance の型名を取得する。GTypeInstance でなければ None。"""
    if not addr:
        return None
    _, _, gobj = _load_libs()
    if gobj is None:
        return None
    try:
        if not gobj.g_type_check_instance(ctypes.c_void_p(addr)):
            return None
        n = gobj.g_type_name_from_instance(ctypes.c_void_p(addr))
        return n.decode() if n else None
    except Exception:
        return None


def _xid_from_widget_ptr(widget_addr: int, debug: bool = False) -> int:
    """与えられた GtkWidget* から X11 XID を取り出す。失敗したら 0。"""
    if not widget_addr:
        return 0
    gtk, gdk, _ = _load_libs()
    if gtk is None or gdk is None:
        return 0

    name = _gtype_name(widget_addr)
    if not name:
        if debug:
            sys.stderr.write(
                f"[stb wxvtk] {widget_addr:#x} is not a GTypeInstance — skip\n"
            )
        return 0

    h = ctypes.c_void_p(widget_addr)

    try:
        if not gtk.gtk_widget_get_realized(h):
            gtk.gtk_widget_realize(h)
    except Exception:
        pass

    def _xid_of(gdkwin_addr: int) -> int:
        if not gdkwin_addr:
            return 0
        gdk_name = _gtype_name(gdkwin_addr)
        if not gdk_name or "X11" not in gdk_name:
            if debug:
                sys.stderr.write(
                    f"[stb wxvtk] gdk_window {gdkwin_addr:#x} is {gdk_name!r}, "
                    f"not X11 — GDK_BACKEND=x11 required\n"
                )
            return 0
        try:
            return int(gdk.gdk_x11_window_get_xid(ctypes.c_void_p(gdkwin_addr)))
        except Exception:
            return 0

    try:
        gdkwin = gtk.gtk_widget_get_window(h)
        xid = _xid_of(int(gdkwin) if gdkwin else 0)
        if xid:
            if debug:
                sys.stderr.write(
                    f"[stb wxvtk] widget {widget_addr:#x}({name}) -> XID {xid:#x}\n"
                )
            return xid
    except Exception:
        pass

    # 親ウィジェットの window を fallback に試す
    try:
        parent = gtk.gtk_widget_get_parent(h)
        if parent:
            pgw = gtk.gtk_widget_get_window(ctypes.c_void_p(parent))
            xid = _xid_of(int(pgw) if pgw else 0)
            if xid:
                if debug:
                    sys.stderr.write(
                        f"[stb wxvtk] widget {widget_addr:#x}({name}) -> "
                        f"parent XID {xid:#x}\n"
                    )
                return xid
    except Exception:
        pass

    return 0


def patch_wxvtk_for_gtk_xid() -> None:
    if not sys.platform.startswith("linux"):
        return

    try:
        from vtkmodules.wx import wxVTKRenderWindowInteractor as _mod
    except ImportError:
        return

    cls = _mod.wxVTKRenderWindowInteractor
    if getattr(cls, "_stb_gtk_xid_patched", False):
        return

    import wx

    if wx.Platform != "__WXGTK__":
        return

    debug = os.environ.get("STB_WXVTK_DEBUG") == "1"

    # Wayland セッションで GDK_BACKEND が立っていない場合の警告(初回のみ)
    if (
        os.environ.get("WAYLAND_DISPLAY")
        and os.environ.get("GDK_BACKEND") != "x11"
    ):
        sys.stderr.write(
            "[stb wxvtk] WARNING: WAYLAND_DISPLAY is set but GDK_BACKEND!=x11. "
            "VTK requires X11; please set GDK_BACKEND=x11 before importing wx.\n"
        )

    def _patched_get_handle(self):
        try:
            gw_obj = self.GetGtkWidget()
            gw = int(gw_obj) if gw_obj else 0
        except Exception:
            gw = 0

        if gw:
            xid = _xid_from_widget_ptr(gw, debug=debug)
            if xid:
                return xid

        if debug:
            sys.stderr.write(
                f"[stb wxvtk] FAILED to derive X11 XID; "
                f"falling back to broken GetHandle (will likely error).\n"
            )

        # 最後の手段。VTK で from_chars が落ちるが、何も返さないよりはマシ。
        try:
            import wx as _wx

            return _wx.glcanvas.GLCanvas.GetHandle(self)
        except Exception:
            return 0

    cls.GetHandle = _patched_get_handle
    cls._stb_gtk_xid_patched = True
