# pylint: disable=import-outside-toplevel

"""Unit tests for modules/oracle_session.py.

All subprocess and filesystem calls are mocked — no Oracle or Quantower needed.
"""

import os
import tempfile
import unittest


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


if __name__ == "__main__":
    unittest.main()