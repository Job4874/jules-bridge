"""Unit tests for modules/oracle_session.py.

All subprocess and filesystem calls are mocked — no Oracle or Quantower needed.
"""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch


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
            open(os.path.join(d, "a.md"), "w").close()
            open(os.path.join(d, "b.md"), "w").close()
            with patch.object(self.os_mod, "_CODEX_HANDOVER_ROOT", d):
                result = self.os_mod.codex_handover_index()
        self.assertTrue(result["exists"])
        self.assertEqual(result["file_count"], 2)
        paths = [f["relative_path"] for f in result["files"]]
        self.assertIn("a.md", paths)


class TestHardIndexHostPaths(unittest.TestCase):
    def setUp(self):
        from modules import oracle_session
        self.os_mod = oracle_session

    @patch("modules.oracle_session.os.path.isdir")
    @patch("modules.oracle_session.os.listdir")
    def test_hard_index_reports_both_paths_when_present(self, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["v1.146.13", "Starter.exe"]

        result = self.os_mod.hard_index_host_paths()

        self.assertTrue(result["all_required_exist"])
        self.assertTrue(result["paths"]["oracle_repo"]["exists"])
        self.assertTrue(result["paths"]["quantower_trading_platform"]["exists"])
        self.assertIn("v1.146.13", result["paths"]["quantower_trading_platform"]["sample_entries"])

    @patch("modules.oracle_session.os.path.isdir")
    def test_hard_index_fails_when_quantower_missing(self, mock_isdir):
        def isdir_side_effect(path):
            return "OracleV5" in path

        mock_isdir.side_effect = isdir_side_effect

        result = self.os_mod.hard_index_host_paths()

        self.assertFalse(result["all_required_exist"])
        self.assertFalse(result["paths"]["quantower_trading_platform"]["exists"])


class TestOracleRestartReplay(unittest.TestCase):
    def setUp(self):
        from modules import oracle_session
        self.os_mod = oracle_session

    @patch("modules.oracle_session.oracle_status")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session.hard_index_host_paths")
    @patch("modules.oracle_session._info_xml_settings")
    def test_restart_replay_aborts_when_hard_index_fails(
        self, mock_info, mock_hard_index, mock_run_ps, mock_status
    ):
        mock_hard_index.return_value = {
            "all_required_exist": False,
            "paths": {"quantower_trading_platform": {"exists": False, "path": "C:\\Quantower\\TradingPlatform"}},
        }
        mock_info.return_value = {"exists": True}

        result = self.os_mod.oracle_restart_replay(force_close=False)

        mock_run_ps.assert_not_called()
        self.assertFalse(result["succeeded"])
        self.assertEqual(result["halt"]["reason"], "hard_index_failed")
        mock_status.assert_not_called()

    @patch("modules.oracle_session.oracle_status")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session.hard_index_host_paths")
    @patch("modules.oracle_session._info_xml_settings")
    def test_restart_replay_runs_script_and_halts_on_verify_pass(
        self, mock_info, mock_hard_index, mock_run_ps, mock_status
    ):
        mock_hard_index.return_value = {"all_required_exist": True, "paths": {}}
        mock_info.return_value = {"exists": True, "symbol_bound": True, "account_bound": True}
        mock_run_ps.side_effect = [
            {"stdout": "Quantower restarted", "stderr": "", "code": 0},
            {"stdout": "All replay checks passed", "stderr": "", "code": 0},
        ]
        mock_status.return_value = {
            "blockers": [],
            "gates": {"g2_dll_deployed": True},
            "quantower": {"running": True},
        }

        result = self.os_mod.oracle_restart_replay(force_close=False)

        self.assertTrue(result["succeeded"])
        self.assertEqual(result["halt"]["reason"], "verify_passed")
        restart_call = mock_run_ps.call_args_list[0]
        self.assertIn("Restart-QuantowerLoadOracle.ps1", restart_call[0][0])
        if len(restart_call[0]) > 1:
            self.assertIsNone(restart_call[0][1])
        else:
            self.assertNotIn("extra_args", restart_call[1])

    @patch("modules.oracle_session.oracle_status")
    @patch("modules.oracle_session._run_ps")
    @patch("modules.oracle_session.hard_index_host_paths")
    @patch("modules.oracle_session._info_xml_settings")
    def test_restart_replay_passes_force_close_flag(
        self, mock_info, mock_hard_index, mock_run_ps, mock_status
    ):
        mock_hard_index.return_value = {"all_required_exist": True, "paths": {}}
        mock_info.return_value = {"exists": True}
        mock_run_ps.side_effect = [
            {"stdout": "", "stderr": "", "code": 0},
            {"stdout": "ACTION: bind symbol", "stderr": "", "code": 1},
        ]
        mock_status.return_value = {"blockers": ["Symbol not bound"], "gates": {"g2_dll_deployed": False}}

        result = self.os_mod.oracle_restart_replay(force_close=True)

        restart_call = mock_run_ps.call_args_list[0]
        extra = restart_call[0][1] if len(restart_call[0]) > 1 else restart_call[1].get("extra_args")
        self.assertEqual(extra, ["-ForceClose"])
        self.assertFalse(result["succeeded"])
        self.assertEqual(result["halt"]["reason"], "verify_failed")

    @patch("modules.oracle_session.hard_index_host_paths")
    def test_restart_replay_never_raises_on_bad_input_path(self, mock_hard_index):
        mock_hard_index.side_effect = RuntimeError("unexpected")

        result = self.os_mod.oracle_restart_replay(force_close=False)

        self.assertFalse(result["succeeded"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
