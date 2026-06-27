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

    @patch("modules.app_launcher.subprocess.Popen")
    def test_launches_edge_when_authorized(self, mock_popen):
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
