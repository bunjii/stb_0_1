import os
import sys
import unittest
from unittest import mock

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_gui.browser import (
    STB_APP_ID,
    _browser_kind,
    _browser_launch_cmd,
    _chromium_profile_dir,
    _linux_chromium_extra_args,
    _parse_windows_open_command,
    _windows_default_browser,
    open_gui_browser,
)


class TestGuiBrowser(unittest.TestCase):

    def test_open_gui_browser_falls_back_to_webbrowser(self):
        with mock.patch("stb_gui.browser._windows_new_window", return_value=False), \
             mock.patch("stb_gui.browser._macos_new_window", return_value=False), \
             mock.patch("stb_gui.browser._linux_new_window", return_value=False), \
             mock.patch("webbrowser.open", return_value=True) as mock_open:
            self.assertTrue(open_gui_browser("http://127.0.0.1:8765/"))
            mock_open.assert_called_once_with("http://127.0.0.1:8765/", new=1, autoraise=True)

    def test_windows_uses_default_browser_app_mode(self):
        profile = "/tmp/stb-chromium-profile"
        with mock.patch("stb_gui.browser.platform.system", return_value="Windows"), \
             mock.patch(
                 "stb_gui.browser._windows_default_browser_via_assoc",
                 return_value=(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chrome"),
             ), \
             mock.patch("stb_gui.browser._chromium_profile_dir", return_value=profile), \
             mock.patch("stb_gui.browser._spawn", return_value=True) as mock_spawn, \
             mock.patch("webbrowser.open") as mock_open:
            open_gui_browser("http://127.0.0.1:8765/")
            mock_spawn.assert_called_once_with([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "--app=http://127.0.0.1:8765/",
                "--app-id=structural-toolbox.stb.gui",
                "--user-data-dir=" + profile,
                "--no-first-run",
                "--no-default-browser-check",
            ])
            mock_open.assert_not_called()

    def test_chromium_launch_uses_app_flag(self):
        profile = "/tmp/stb-chromium-profile"
        with mock.patch("stb_gui.browser.platform.system", return_value="Windows"), \
             mock.patch("stb_gui.browser._chromium_profile_dir", return_value=profile):
            cmd = _browser_launch_cmd(r"C:\Edge\msedge.exe", "edge", "http://127.0.0.1:8765/")
        self.assertEqual(cmd, [
            r"C:\Edge\msedge.exe",
            "--app=http://127.0.0.1:8765/",
            "--app-id=" + STB_APP_ID,
            "--user-data-dir=" + profile,
            "--no-first-run",
            "--no-default-browser-check",
        ])

    def test_linux_chromium_defaults_to_x11_on_wayland(self):
        profile = "/tmp/stb-chromium-profile"
        with mock.patch("stb_gui.browser.platform.system", return_value="Linux"), \
             mock.patch("stb_gui.browser._chromium_profile_dir", return_value=profile), \
             mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
            cmd = _browser_launch_cmd("/usr/bin/chromium", "chrome", "http://127.0.0.1:8765/")
        self.assertIn("--ozone-platform=x11", cmd)
        self.assertNotIn("--enable-features=WaylandWindowDecorations", cmd)
        self.assertIn("--user-data-dir=" + profile, cmd)

    def test_linux_chromium_ozone_wayland_override(self):
        with mock.patch.dict(
            os.environ,
            {"STB_CHROMIUM_OZONE_PLATFORM": "wayland", "WAYLAND_DISPLAY": "wayland-0"},
            clear=False,
        ):
            args = _linux_chromium_extra_args()
        self.assertIn("--ozone-platform=wayland", args)
        self.assertIn("--enable-features=WaylandWindowDecorations", args)

    def test_linux_chromium_ozone_x11_override(self):
        with mock.patch.dict(
            os.environ,
            {"STB_CHROMIUM_OZONE_PLATFORM": "x11", "WAYLAND_DISPLAY": "wayland-0"},
            clear=False,
        ):
            args = _linux_chromium_extra_args()
        self.assertEqual(args.count("--ozone-platform=x11"), 1)

    def test_windows_assoc_query_preferred_over_userchoice(self):
        from stb_gui.browser import _windows_default_browser
        with mock.patch(
            "stb_gui.browser._windows_default_browser_via_assoc",
            return_value=(r"C:\Chrome\chrome.exe", "chrome"),
        ), mock.patch(
            "stb_gui.browser._windows_http_progid",
            return_value="MSEdgeHTM",
        ):
            path, kind = _windows_default_browser()
            self.assertEqual(path, r"C:\Chrome\chrome.exe")
            self.assertEqual(kind, "chrome")

    def test_parse_windows_open_command(self):
        self.assertEqual(
            _parse_windows_open_command(
                r'"C:\Program Files\Google\Chrome\Application\chrome.exe" -- "%1"'
            ),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )

    def test_browser_kind_from_progid(self):
        self.assertEqual(_browser_kind("chrome.exe", "ChromeHTML"), "chrome")
        self.assertEqual(_browser_kind("msedge.exe", "MSEdgeHTM"), "edge")
        self.assertEqual(_browser_kind("firefox.exe", "FirefoxURL"), "firefox")

    def test_windows_default_browser_from_registry(self):
        with mock.patch("stb_gui.browser._windows_default_browser_via_assoc", return_value=None), \
             mock.patch("stb_gui.browser._windows_http_progid", return_value="ChromeHTML"), \
             mock.patch(
                 "stb_gui.browser._windows_progid_open_command",
                 return_value=r'"C:\Chrome\chrome.exe" -- "%1"',
             ), \
             mock.patch("stb_gui.browser.os.path.isfile", return_value=True):
            path, kind = _windows_default_browser()
            self.assertEqual(path, r"C:\Chrome\chrome.exe")
            self.assertEqual(kind, "chrome")


if __name__ == "__main__":
    unittest.main()
