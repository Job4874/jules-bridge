"""Integration tests for bridge.py HTTP routes.

These test the HTTP surface — validate → call module → JSON response.
Module internals are mocked. For module-level unit tests see test_*_service.py.
"""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import bridge


class TestInboxRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def test_inbox_read_missing_file(self):
        response = self.client.post("/inbox/read", json={"file": "nonexistent.json"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("inbox file not found", response.get_json()["error"])

    def test_inbox_read_rejects_invalid_file_type(self):
        response = self.client.post("/inbox/read", json={"file": ["OPERATOR_RESPONSE.md"]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestFsRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def test_fs_read_invalid_input(self):
        response = self.client.post("/fs/read", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    def test_fs_read_missing_path(self):
        response = self.client.post("/fs/read", json={"path": r"C:\definitely\missing.txt"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Resource not found")

    def test_fs_read_rejects_malformed_payload(self):
        response = self.client.post("/fs/read", data='{"path": "x"}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Malformed JSON or missing Content-Type header.")

    def test_fs_write_requires_content_or_data(self):
        response = self.client.post("/fs/write", json={"path": r"C:\tmp\bridge-test.txt"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("content or data", response.get_json()["details"])

    def test_fs_write_accepts_data_alias(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "out.txt")
            response = self.client.post("/fs/write", json={"path": path, "data": "ok"})
            self.assertEqual(response.status_code, 200)
            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "ok")


class TestShellRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    @patch("modules.shell_executor.subprocess.run")
    def test_shell_powershell_default(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        response = self.client.post("/shell", json={"command": "echo 1"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["shell"], "powershell")
        self.assertEqual(payload["stdout"], "Success")
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(
            mock_run.call_args.args[0][:4],
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"],
        )

    @patch("modules.shell_executor.subprocess.run")
    def test_shell_cmd_selector(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        response = self.client.post("/shell", json={"command": "echo OK", "shell": "cmd"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["shell"], "cmd")
        self.assertEqual(mock_run.call_args.args[0][:4], ["cmd.exe", "/d", "/s", "/c"])

    @patch("modules.shell_executor.shutil.which", return_value=None)
    def test_shell_invalid_git_bash(self, mock_which):
        # Patch os.path.exists with a side_effect so real directories
        # (cwd check in bridge) pass, but bash candidate paths fail.
        real_exists = os.path.exists

        def fake_exists(p):
            if "Git" in str(p) or "bash" in str(p).lower():
                return False
            return real_exists(p)

        with patch("modules.shell_executor.os.path.exists", side_effect=fake_exists):
            response = self.client.post(
                "/shell",
                json={"command": "ls", "shell": "bash"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bash shell", response.get_json()["details"])

    def test_shell_rejects_wsl_selector(self):
        response = self.client.post("/shell", json={"command": "ls", "shell": "wsl"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("WSL", response.get_json()["details"])

    @patch("modules.shell_executor.subprocess.run")
    def test_shell_timeout_maps_to_504(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo 1", timeout=1)
        response = self.client.post("/shell", json={"command": "echo 1", "timeout": 1})
        self.assertEqual(response.status_code, 504)
        self.assertIn("timed out", response.get_json()["error"])


class TestUIRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def test_ui_click_negative_coordinate(self):
        response = self.client.post("/ui/click", json={"x": -10, "y": 500})
        self.assertEqual(response.status_code, 400)

    @patch("modules.ui_automation._pyautogui")
    def test_ui_click_validates_display_bounds(self, mock_pag_factory):
        pag = MagicMock()
        pag.size.return_value = (1920, 1080)
        mock_pag_factory.return_value = pag

        response = self.client.post("/ui/click", json={"x": 5000, "y": 500})
        self.assertEqual(response.status_code, 400)
        pag.moveTo.assert_not_called()
        pag.click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
