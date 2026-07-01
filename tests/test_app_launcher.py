"""Unit tests for modules/app_launcher.py."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class TestLaunchBrowserToUrl(unittest.TestCase):
    def setUp(self):
        from modules import app_launcher

        self.launcher = app_launcher

    def test_blocked_without_runtime_authorization(self):
        result = self.launcher.launch_browser_to_url(
            "https://example.com",
            allow_launch=False,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["started"])
        self.assertIn("allow_launch", result["error"])

    def test_rejects_non_http_protocol(self):
        result = self.launcher.launch_browser_to_url(
            "file:///etc/passwd",
            allow_launch=True,
        )
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["started"])
        self.assertEqual(result["error"], "Invalid target protocol")

    def test_rejects_javascript_protocol(self):
        result = self.launcher.launch_browser_to_url(
            "javascript:alert(1)",
            allow_launch=True,
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Invalid target protocol")

    def test_rejects_empty_url(self):
        result = self.launcher.launch_browser_to_url("", allow_launch=True)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "url is required")

    def test_rejects_url_without_host(self):
        result = self.launcher.launch_browser_to_url("https://", allow_launch=True)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Invalid target URL")


    def test_rejects_url_with_newline(self):
        result = self.launcher.launch_browser_to_url("https://example.com\nmalicious", allow_launch=True)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Invalid target URL")

    def test_launches_edge_with_shutil_which(self):
        with patch("modules.app_launcher.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 4242
            with patch("modules.app_launcher.shutil.which", side_effect=lambda x: "/usr/bin/msedge" if x == "msedge" else None):
                with patch("modules.app_launcher.os.path.isfile", side_effect=lambda x: x == "/usr/bin/msedge"):
                    with patch("modules.app_launcher.os.path.isabs", return_value=True):
                        result = self.launcher.launch_browser_to_url("https://www.google.com", allow_launch=True)
                        self.assertEqual(result["status"], "success")
                        args = mock_popen.call_args.args[0]
                        self.assertEqual(args, ["/usr/bin/msedge", "https://www.google.com"])
    @patch("modules.app_launcher._resolve_edge_executable", return_value="msedge")
    @patch("modules.app_launcher.subprocess.Popen")
    def test_launches_edge_when_authorized(self, mock_popen, _mock_resolve):
        mock_popen.return_value.pid = 4242

        result = self.launcher.launch_browser_to_url(
            "https://www.google.com",
            allow_launch=True,
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["started"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["app_name"], "msedge")
        mock_popen.assert_called_once()
        args = mock_popen.call_args.args[0]
        self.assertEqual(args[:4], ["cmd.exe", "/d", "/s", "/c"])
        self.assertEqual(args[4:], ["start", "", "msedge", "https://www.google.com"])

    @patch("modules.app_launcher.subprocess.Popen")
    def test_launches_absolute_edge_path_when_configured(self, mock_popen):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        with patch.dict(
            "modules.app_launcher.os.environ",
            {"JULES_EDGE_PATH": edge_path},
        ), patch(
            "modules.app_launcher.os.path.isfile",
            side_effect=lambda path: path == edge_path,
        ), patch(
            "modules.app_launcher.os.path.isabs",
            side_effect=lambda path: path.startswith("C:\\") or path.startswith("/"),
        ), patch(
            "modules.app_launcher.shutil.which",
            return_value=None,
        ):
            result = self.launcher.launch_browser_to_url(
                "https://www.google.com",
                allow_launch=True,
            )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["started"])
        args = mock_popen.call_args.args[0]
        self.assertEqual(args, [edge_path, "https://www.google.com"])

    @patch("modules.app_launcher.subprocess.Popen", side_effect=OSError("spawn failed"))
    def test_maps_spawn_failure_to_error(self, _mock_popen):
        result = self.launcher.launch_browser_to_url(
            "http://127.0.0.1:5000/health",
            allow_launch=True,
        )
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["started"])
        self.assertEqual(result["error"], "Internal process launch failure")


if __name__ == "__main__":
    unittest.main()
