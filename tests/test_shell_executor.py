# pylint: disable=import-outside-toplevel

"""Unit tests for modules/shell_executor.py.

Tests at the module interface level — subprocess calls are mocked.
"""

import os
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

    @patch("modules.shell_executor.subprocess.run")
    @patch("modules.shell_executor.os.path.exists", side_effect=lambda p: "Git" in str(p))
    def test_execute_auto_routes_unix_syntax_to_bash(self, _mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = self.se.execute("ls -t /tmp/screenshot_v2.png | head -n 1")
        self.assertEqual(result["shell"], "bash")
        self.assertTrue(result.get("shell_auto_selected"))
        args = mock_run.call_args.args[0]
        self.assertTrue(str(args[0]).endswith("bash.exe") or "bash" in str(args[0]).lower())

    @patch("modules.shell_executor.os.path.exists", return_value=False)
    @patch("modules.shell_executor.shutil.which", return_value=None)
    def test_execute_unix_syntax_without_bash_raises(self, _mock_which, _mock_exists):
        with self.assertRaises(self.se.ShellNotAvailableError) as ctx:
            self.se.execute("ls -t /tmp/x | head -n 1")
        self.assertIn("Unix shell syntax", str(ctx.exception))

    @patch("modules.shell_executor.subprocess.run")
    def test_execute_bypass_cache_skips_cached_result(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="one", stderr="")
        with patch.dict(os.environ, {"SHELL_CACHE_TTL_S": "60"}):
            self.se._shell_result_cache.clear()
            self.se.execute("echo cached", shell="cmd")
            self.se.execute("echo cached", shell="cmd", bypass_cache=True)
        self.assertEqual(mock_run.call_count, 2)



class TestShellExecutorSpawn(unittest.TestCase):
    def setUp(self):
        from modules import shell_executor
        self.se = shell_executor

    @patch("modules.shell_executor.subprocess.Popen")
    @patch("modules.shell_executor.os.getcwd", return_value="/mock/dir")
    def test_spawn_default_cmd(self, mock_getcwd, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        result = self.se.spawn(command="echo test")

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["shell"], "cmd")
        self.assertEqual(result["pid"], 1234)
        self.assertTrue(result["spawned"])

        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0][:4], ["cmd.exe", "/d", "/s", "/c"])
        self.assertEqual(kwargs["cwd"], "/mock/dir")
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)

    @patch("modules.shell_executor.subprocess.Popen")
    def test_spawn_powershell_selector(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_popen.return_value = mock_proc

        result = self.se.spawn(command="echo test", shell="powershell")

        self.assertEqual(result["shell"], "powershell")
        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0][:4], ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"])

    @patch("modules.shell_executor.subprocess.Popen")
    def test_spawn_custom_cwd(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        self.se.spawn(command="echo test", cwd="/custom/path")

        _, kwargs = mock_popen.call_args
        self.assertEqual(kwargs["cwd"], "/custom/path")

    def test_spawn_wsl_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            self.se.spawn(command="ls", shell="wsl")
        self.assertIn("WSL", str(ctx.exception))

    def test_spawn_unknown_shell_raises(self):
        with self.assertRaises(self.se.UnsupportedShellError):
            self.se.spawn(command="x", shell="fish")


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
