"""Open the GUI in a dedicated, chromeless browser window when possible."""

from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import subprocess
from typing import Iterable, List, Optional, Sequence, Tuple


def open_gui_browser(url: str) -> bool:
    """Launch *url* in a standalone GUI window (no tabs / address bar when supported)."""

    system = platform.system()
    if system == "Windows" and _windows_new_window(url):
        return True
    if system == "Darwin" and _macos_new_window(url):
        return True
    if system not in ("Windows", "Darwin") and _linux_new_window(url):
        return True

    try:
        import webbrowser

        return bool(webbrowser.open(url, new=1, autoraise=True))
    except Exception:
        return False


def _spawn(cmd: Sequence[str]) -> bool:
    try:
        subprocess.Popen(
            list(cmd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=os.name != "nt",
        )
        return True
    except OSError:
        return False


STB_APP_ID = "structural-toolbox.stb.gui"
STB_WM_CLASS = "StructuralToolbox"


def _chromium_profile_dir() -> str:
    override = os.environ.get("STB_CHROMIUM_USER_DATA_DIR", "").strip()
    if override:
        return override
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "StructuralToolbox", "ChromiumProfile")
    return os.path.join(os.path.expanduser("~"), ".config", "structural-toolbox-gui")


def _chromium_common_args() -> List[str]:
    return [
        "--user-data-dir=" + _chromium_profile_dir(),
        "--no-first-run",
        "--no-default-browser-check",
    ]


def _linux_chromium_extra_args() -> List[str]:
    """Extra Chromium flags on Linux (Wayland / GNOME title bar integration).

    Fedora/GNOME Wayland draws PWA titles in the desktop accent colour (often blue)
    when Chromium uses native Wayland or GTK client-side decorations. Default to
    XWayland (``--ozone-platform=x11``) for GNOME server-side decorations and dark
    title text. Use a dedicated profile so flags are not dropped by an already
    running browser instance.

    Override with environment variables:
    - STB_CHROMIUM_OZONE_PLATFORM=wayland|x11
    - STB_CHROMIUM_USER_DATA_DIR=…
    - STB_CHROMIUM_EXTRA_ARGS='…'
    """
    args: List[str] = ["--class=" + STB_WM_CLASS]

    ozone = os.environ.get("STB_CHROMIUM_OZONE_PLATFORM", "").strip().lower()
    if ozone == "wayland":
        args.extend([
            "--ozone-platform=wayland",
            "--ozone-platform-hint=auto",
            "--enable-features=WaylandWindowDecorations",
        ])
    elif ozone == "x11":
        args.append("--ozone-platform=x11")
    elif os.environ.get("WAYLAND_DISPLAY"):
        args.append("--ozone-platform=x11")

    extra = os.environ.get("STB_CHROMIUM_EXTRA_ARGS", "").strip()
    if extra:
        args.extend(shlex.split(extra))
    return args


def _browser_launch_cmd(path: str, kind: str, url: str) -> List[str]:
    """Build a browser command that hides tabs and the URL bar where supported."""

    if kind == "firefox":
        # Firefox has no stable cross-platform app-mode flag; use a separate window.
        return [path, "-new-window", url]
    # Chromium-based browsers (Chrome, Edge, Brave, Opera, …): application mode.
    cmd = [path, "--app=" + url, "--app-id=" + STB_APP_ID]
    cmd.extend(_chromium_common_args())
    if platform.system() == "Linux":
        cmd.extend(_linux_chromium_extra_args())
    return cmd


def _windows_launch_gui(url: str) -> bool:
    default = _windows_default_browser()
    if default:
        path, kind = default
        if _spawn(_browser_launch_cmd(path, kind, url)):
            return True

    try:
        import webbrowser

        return bool(webbrowser.open(url, new=1, autoraise=True))
    except Exception:
        return False


def _windows_new_window(url: str) -> bool:
    return _windows_launch_gui(url)


def _windows_default_browser_via_assoc() -> Optional[Tuple[str, str]]:
    """Resolve the HTTP default browser executable via Windows AssocQueryString."""

    try:
        from ctypes import byref, create_unicode_buffer, windll, wintypes

        assocf_none = 0
        assocstr_executable = 2
        buf = create_unicode_buffer(2048)
        size = wintypes.DWORD(len(buf))
        hr = windll.Shlwapi.AssocQueryStringW(
            assocf_none,
            assocstr_executable,
            "http",
            "open",
            buf,
            byref(size),
        )
        if hr != 0:
            return None
        exe = str(buf.value or "").strip().strip('"')
        if exe and os.path.isfile(exe):
            return exe, _browser_kind(exe, "")
    except Exception:
        return None
    return None


def _windows_default_browser() -> Optional[Tuple[str, str]]:
    """Return (executable_path, kind) for the user's HTTP default browser."""

    via_assoc = _windows_default_browser_via_assoc()
    if via_assoc:
        return via_assoc

    progid = _windows_http_progid()
    if not progid:
        return _windows_default_browser_from_webbrowser()

    command = _windows_progid_open_command(progid)
    if not command:
        return _windows_default_browser_from_webbrowser()

    exe = _parse_windows_open_command(command)
    if not exe or not os.path.isfile(exe):
        return _windows_default_browser_from_webbrowser()

    return exe, _browser_kind(exe, progid)


def _windows_http_progid() -> Optional[str]:
    try:
        import winreg
    except ImportError:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
        ) as key:
            progid = winreg.QueryValueEx(key, "ProgId")[0]
            if progid:
                return str(progid)
    except OSError:
        pass

    return None


def _windows_progid_open_command(progid: str) -> Optional[str]:
    try:
        import winreg
    except ImportError:
        return None

    for root, subkey in (
        (winreg.HKEY_CURRENT_USER, progid + r"\shell\open\command"),
        (winreg.HKEY_CLASSES_ROOT, progid + r"\shell\open\command"),
    ):
        try:
            with winreg.OpenKey(root, subkey) as key:
                command = winreg.QueryValueEx(key, None)[0]
                if command:
                    return str(command)
        except OSError:
            continue
    return None


def _parse_windows_open_command(command: str) -> Optional[str]:
    command = str(command or "").strip()
    if not command:
        return None
    if command.startswith('"'):
        end = command.find('"', 1)
        if end > 1:
            return command[1:end]
    match = re.match(r"([^\s]+)", command)
    if match:
        return match.group(1)
    return None


def _browser_kind(exe: str, progid: str) -> str:
    base = os.path.basename(exe).lower()
    progid_lower = progid.lower()
    if "firefox" in base or "firefox" in progid_lower:
        return "firefox"
    if "msedge" in base or "edge" in progid_lower:
        return "edge"
    if any(token in base or token in progid_lower for token in ("chrome", "brave", "vivaldi", "opera")):
        return "chrome"
    return "chrome"


def _windows_default_browser_from_webbrowser() -> Optional[Tuple[str, str]]:
    try:
        import webbrowser
    except ImportError:
        return None

    try:
        controller = webbrowser.get()
    except webbrowser.Error:
        return None

    exe = getattr(controller, "name", None) or getattr(controller, "_name", None)
    if not exe:
        return None

    exe = os.path.expandvars(str(exe).strip().strip('"'))
    if not os.path.isfile(exe):
        resolved = shutil.which(os.path.basename(exe))
        if resolved:
            exe = resolved
        else:
            return None

    return exe, _browser_kind(exe, os.path.basename(exe))


def _macos_new_window(url: str) -> bool:
    for app in ("Google Chrome", "Microsoft Edge", "Brave Browser", "Chromium"):
        if _spawn(["open", "-na", app, "--args", "--app=" + url, "--app-id=" + STB_APP_ID]):
            return True
    if _spawn(["open", "-na", "Firefox", "--args", "-new-window", url]):
        return True
    return False


def _linux_new_window(url: str) -> bool:
    specs = (
        ("google-chrome", "chrome"),
        ("google-chrome-stable", "chrome"),
        ("chromium", "chrome"),
        ("chromium-browser", "chrome"),
        ("microsoft-edge", "edge"),
        ("microsoft-edge-stable", "edge"),
        ("firefox", "firefox"),
    )
    for name, kind in specs:
        path = shutil.which(name)
        if path and _spawn(_browser_launch_cmd(path, kind, url)):
            return True
    desktop = os.environ.get("BROWSER")
    if desktop:
        path = shutil.which(desktop) or (desktop if os.path.isfile(desktop) else None)
        if path and _spawn(_browser_launch_cmd(path, _browser_kind(path, ""), url)):
            return True
    return False
