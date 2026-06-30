# pylint: disable=import-outside-toplevel

"""Unit tests for modules/shell_executor.py.

Tests at the module interface level — subprocess calls are mocked.
"""

import subprocess
import unittest
from unittest.mock import MagicMock, patch


class TestShellExecutorExecute(unittest.TestCase):
    def setUp(self):
        from modules import shell_executor
        self.se = shell_executor

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_powershell_default(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = self.se.execute("echo 1")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "ok")
        self.assertEqual(result["shell"], "powershell")
        args = mock_run.call_args.args[0]
        self.assertEqual(args[:4], ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"])

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_cmd_selector(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="WIN", stderr="")
        result = self.se.execute("echo WIN", shell="cmd")
        self.assertEqual(result["shell"], "cmd")
        args = mock_run.call_args.args[0]
        self.assertEqual(args[:4], ["cmd.exe", "/d", "/s", "/c"])

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_returns_legacy_code_alias(self, mock_run):
        mock_run.return_value = MagicMock(returncode=42, stdout="", stderr="")
        result = self.se.execute("cmd", shell="cmd")
        self.assertEqual(result["code"], 42)
        self.assertEqual(result["exit_code"], 42)

    @patch("modules.shell_executor.shutil.which", return_value=None)
    @patch("modules.shell_executor.os.path.exists", return_value=False)
    def test_execute_bash_not_found_raises(self, _mock_exists, _mock_which):
        with self.assertRaises(self.se.ShellNotAvailableError):
            self.se.execute("ls", shell="bash")

    def test_execute_wsl_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            self.se.execute("ls", shell="wsl")
        self.assertIn("WSL", str(ctx.exception))

    def test_execute_unknown_shell_raises(self):
        with self.assertRaises(self.se.UnsupportedShellError):
            self.se.execute("x", shell="fish")

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_timeout_propagates(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo 1", timeout=1)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.se.execute("echo 1", timeout=1)

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_bytes_stdout_coerced(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=b"bytes out", stderr=b"")
        result = self.se.execute("echo x")
        self.assertIsInstance(result["stdout"], str)
        self.assertEqual(result["stdout"], "bytes out")

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_ps_alias_selector(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = self.se.execute("echo", shell="ps")
        self.assertEqual(result["shell"], "powershell")



    @patch("modules.shell_executor.subprocess.Popen")
    def test_spawn(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        result = self.se.spawn("echo 1")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["spawned"], True)
        self.assertEqual(result["pid"], 12345)
        self.assertEqual(result["shell"], "cmd")
        args = mock_popen.call_args.args[0]
        self.assertEqual(args[:4], ["cmd.exe", "/d", "/s", "/c"])

    def test_coerce_text_none(self):
        self.assertEqual(self.se._coerce_text(None), "")

    @patch("modules.shell_executor.os.path.exists")
    @patch.dict("os.environ", {"JULES_BASH_PATH": "/custom/bash"})
    def test_discover_bash_from_env_exists(self, mock_exists):
        mock_exists.return_value = True
        self.assertEqual(self.se._discover_bash(), "/custom/bash")

    @patch("modules.shell_executor.os.path.exists")
    @patch.dict("os.environ", {"JULES_BASH_PATH": "/custom/missing_bash"})
    def test_discover_bash_from_env_missing(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(self.se.ShellNotAvailableError):
            self.se._discover_bash()

    @patch("modules.shell_executor.os.path.exists")
    @patch("modules.shell_executor.shutil.which")
    @patch.dict("os.environ", {"JULES_BASH_PATH": ""})
    def test_discover_bash_via_which(self, mock_which, mock_exists):
        mock_exists.return_value = False
        mock_which.side_effect = lambda x: "/usr/bin/bash" if x == "bash" else None
        self.assertEqual(self.se._discover_bash(), "/usr/bin/bash")

    @patch("modules.shell_executor.time.time")
    @patch("modules.shell_executor.subprocess.run")
    def test_execute_slow_call_warning(self, mock_run, mock_time):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_time.side_effect = [100.0, 100.0, 106.0, 106.0, 106.0, 106.0]
        with self.assertLogs("jules_bridge", level="WARNING") as cm:
            self.se.execute("sleep 6")
        self.assertTrue(any("Slow shell call (>5s)" in log for log in cm.output))

    @patch("modules.shell_executor.subprocess.run")
    @patch.dict("os.environ", {"SHELL_CACHE_TTL_S": "60"})
    def test_execute_cache(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="cached_out", stderr="")
        res1 = self.se.execute("echo cache_test")
        res2 = self.se.execute("echo cache_test")
        self.assertEqual(res1["stdout"], "cached_out")
        self.assertEqual(res2["stdout"], "cached_out")
        mock_run.assert_called_once()

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_timeout_explicit(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 10", timeout=5.0)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.se.execute("sleep 10", timeout=5.0)


class TestAvailableShells(unittest.TestCase):
    def setUp(self):
        from modules import shell_executor
        self.se = shell_executor

    @patch("modules.shell_executor.os.path.exists", return_value=False)
    @patch("modules.shell_executor.shutil.which", return_value=None)
    def test_available_shells_without_bash(self, _mock_which, _mock_exists):
        shells = self.se.available_shells()
        self.assertIn("powershell", shells)
        self.assertIn("cmd", shells)
        self.assertNotIn("bash", shells)

    @patch("modules.shell_executor.os.path.exists", side_effect=lambda p: "Git" in p)
    def test_available_shells_with_bash(self, _mock_exists):
        shells = self.se.available_shells()
        self.assertIn("bash", shells)


if __name__ == "__main__":
    unittest.main()
