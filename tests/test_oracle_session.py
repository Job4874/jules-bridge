# pylint: disable=import-outside-toplevel

"""Unit tests for modules/oracle_session.py.

All subprocess and filesystem calls are mocked — no Oracle or Quantower needed.
"""

import os
import tempfile
import unittest
from unittest.mock import patch



class TestOracleStatus(unittest.TestCase):
    def setUp(self):
        from modules import oracle_session
        self.os_mod = oracle_session

    @patch("modules.oracle_session._quantower_process")
    @patch("modules.oracle_session._latest_telemetry")
    @patch("modules.oracle_session._info_xml_settings")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session._dll_info")
    def test_status_returns_expected_keys(
        self, mock_dll, mock_ps, mock_info, mock_telemetry, mock_qtower
    ):
        mock_dll.return_value = {"path": "x.dll", "sha256_prefix": "abc", "last_write_utc": "now"}
        mock_ps.return_value = {"stdout": "", "stderr": "", "code": 0}
        mock_info.return_value = {"exists": True, "symbol_bound": True, "account_bound": True}
        mock_telemetry.return_value = {"exists": False, "root": "/tmp"}
        mock_qtower.return_value = {"running": True, "processes": []}

        result = self.os_mod.oracle_status()

        self.assertIn("oracle_repo", result)
        self.assertIn("blockers", result)
        self.assertIn("gates", result)
        self.assertIn("next_actions", result)
        self.assertIn("verify", result)

    @patch("modules.oracle_session._quantower_process")
    @patch("modules.oracle_session._latest_telemetry")
    @patch("modules.oracle_session._info_xml_settings")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session._dll_info")
    def test_status_adds_blocker_when_not_running(
        self, mock_dll, mock_ps, mock_info, mock_telemetry, mock_qtower
    ):
        mock_dll.return_value = {"path": "", "sha256_prefix": "", "last_write_utc": ""}
        mock_ps.return_value = {"stdout": "", "stderr": "", "code": 1}
        mock_info.return_value = {"exists": True, "symbol_bound": True, "account_bound": True}
        mock_telemetry.return_value = {"exists": False, "root": "/tmp"}
        mock_qtower.return_value = {"running": False, "processes": []}

        result = self.os_mod.oracle_status()
        self.assertTrue(any("Quantower" in b for b in result["blockers"]))

    @patch("modules.oracle_session._quantower_process")
    @patch("modules.oracle_session._latest_telemetry")
    @patch("modules.oracle_session._info_xml_settings")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session._dll_info")
    def test_gates_g2_true_when_verify_passes(
        self, mock_dll, mock_ps, mock_info, mock_telemetry, mock_qtower
    ):
        mock_dll.return_value = {"path": "", "sha256_prefix": "", "last_write_utc": ""}
        mock_ps.return_value = {"stdout": "All replay ready", "stderr": "", "code": 0}
        mock_info.return_value = {"exists": True, "symbol_bound": True, "account_bound": True}
        mock_telemetry.return_value = {"exists": False, "root": "/tmp"}
        mock_qtower.return_value = {"running": True, "processes": []}

        result = self.os_mod.oracle_status()
        self.assertTrue(result["gates"]["g2_dll_deployed"])


class TestParseVerify(unittest.TestCase):
    def setUp(self):
        from modules.oracle_session import _parse_verify
        self.parse = _parse_verify

    def test_parse_all_replay_ready(self):
        stdout = "All replay checks passed\n"
        checks = self.parse(stdout)
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["check"], "summary")
        self.assertTrue(checks[0]["ok"])

    def test_parse_action_line(self):
        stdout = "ACTION: Please bind symbol\n"
        checks = self.parse(stdout)
        self.assertEqual(checks[0]["check"], "action")
        self.assertFalse(checks[0]["ok"])

    def test_parse_tabular_line(self):
        stdout = "DLL Exists   True   Strategy DLL found\n"
        checks = self.parse(stdout)
        # Should parse into 3-column format
        self.assertTrue(any(c.get("ok") for c in checks))

    def test_parse_empty_stdout(self):
        self.assertEqual(self.parse(""), [])


class TestCodexHandoverIndex(unittest.TestCase):
    def setUp(self):
        from modules import oracle_session
        self.os_mod = oracle_session

    def test_missing_folder_returns_exists_false(self):
        with patch.object(self.os_mod, "_CODEX_HANDOVER_ROOT", r"C:\does\not\exist"):
            result = self.os_mod.codex_handover_index()
        self.assertFalse(result["exists"])
        self.assertIn("message", result)

    def test_existing_folder_returns_file_list(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.md"), "w", encoding="utf-8").close()
            open(os.path.join(d, "b.md"), "w", encoding="utf-8").close()
            with patch.object(self.os_mod, "_CODEX_HANDOVER_ROOT", d):
                result = self.os_mod.codex_handover_index()
        self.assertTrue(result["exists"])
        self.assertEqual(result["file_count"], 2)
        paths = [f["relative_path"] for f in result["files"]]
        self.assertIn("a.md", paths)

    def test_nested_directories_and_size(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sub1", "sub2"))

            # File 1: in root
            p1 = os.path.join(d, "file1.txt")
            with open(p1, "w", encoding="utf-8") as f:
                f.write("hello")  # 5 bytes

            # File 2: in sub1/sub2
            p2 = os.path.join(d, "sub1", "sub2", "file2.txt")
            with open(p2, "w", encoding="utf-8") as f:
                f.write("world!")  # 6 bytes

            with patch.object(self.os_mod, "_CODEX_HANDOVER_ROOT", d):
                result = self.os_mod.codex_handover_index()

        self.assertTrue(result["exists"])
        self.assertEqual(result["file_count"], 2)

        # files should be sorted by relative_path
        files = result["files"]
        self.assertEqual(files[0]["relative_path"], "file1.txt")
        self.assertEqual(files[0]["size"], 5)
        self.assertEqual(files[1]["relative_path"], "sub1/sub2/file2.txt")
        self.assertEqual(files[1]["size"], 6)

    def test_max_200_files_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(205):
                p = os.path.join(d, f"file{i:03d}.txt")
                with open(p, "w", encoding="utf-8") as f:
                    f.write("x")

            with patch.object(self.os_mod, "_CODEX_HANDOVER_ROOT", d):
                result = self.os_mod.codex_handover_index()

        self.assertTrue(result["exists"])
        self.assertEqual(result["file_count"], 205)
        self.assertEqual(len(result["files"]), 200)


if __name__ == "__main__":
    unittest.main()
class TestOracleBuildDeploy(unittest.TestCase):
    def setUp(self):
        from modules import oracle_session
        self.os_mod = oracle_session

    @patch("modules.oracle_session.subprocess.run")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session.oracle_status")
    @patch("modules.oracle_session._parse_verify")
    def test_oracle_build_deploy_success(self, mock_parse_verify, mock_oracle_status, mock_run_ps, mock_subprocess_run):
        # Setup mocks
        class MockProcess:
            returncode = 0
            stdout = "Build succeeded\n1 Warning(s)\n0 Error(s)"
            stderr = ""
        mock_subprocess_run.return_value = MockProcess()

        # _run_ps is called twice: once for deploy, once for verify
        mock_run_ps.side_effect = [
            {"code": 0, "stdout": "Deployed", "stderr": ""}, # Deploy
            {"code": 0, "stdout": "Verified", "stderr": ""}  # Verify
        ]

        mock_parse_verify.return_value = [{"check": "summary", "ok": True}]
        mock_oracle_status.return_value = {"blockers": [], "gates": {}, "next_actions": []}

        # Execute
        result = self.os_mod.oracle_build_deploy()

        # Assert build
        self.assertEqual(result["build"]["code"], 0)
        self.assertIn("Build succeeded", result["build"]["stdout_tail"][0])
        self.assertEqual(result["build"]["stderr_tail"], [])

        # Assert deploy
        self.assertEqual(result["deploy"]["code"], 0)
        self.assertEqual(result["deploy"]["stdout"], "Deployed")

        # Assert verify
        self.assertEqual(result["verify"]["code"], 0)
        self.assertEqual(result["verify"]["checks"][0]["check"], "summary")
        self.assertTrue(result["verify"]["checks"][0]["ok"])

        # Assert status
        self.assertEqual(result["status"]["blockers"], [])

        # Verify calls
        mock_subprocess_run.assert_called_once()
        self.assertEqual(mock_run_ps.call_count, 2)
        mock_parse_verify.assert_called_once_with("Verified")
        mock_oracle_status.assert_called_once()


    @patch("modules.oracle_session.subprocess.run")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session.oracle_status")
    @patch("modules.oracle_session._parse_verify")
    def test_oracle_build_deploy_build_failure(self, mock_parse_verify, mock_oracle_status, mock_run_ps, mock_subprocess_run):
         # Setup mocks for a build failure
        class MockProcess:
            returncode = 1
            stdout = "Build FAILED."
            stderr = "Error: Some build error"
        mock_subprocess_run.return_value = MockProcess()

        mock_run_ps.side_effect = [
            {"code": 0, "stdout": "Deployed", "stderr": ""},
            {"code": 0, "stdout": "Verified", "stderr": ""}
        ]

        mock_parse_verify.return_value = [{"check": "summary", "ok": True}]
        mock_oracle_status.return_value = {"blockers": [], "gates": {}, "next_actions": []}

        # Execute
        result = self.os_mod.oracle_build_deploy()

        # Assert build failure is propagated
        self.assertEqual(result["build"]["code"], 1)
        self.assertEqual(result["build"]["stderr_tail"][0], "Error: Some build error")
