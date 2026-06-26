"""Integration tests for bridge.py HTTP routes.

These test the HTTP surface — validate → call module → JSON response.
Module internals are mocked. For module-level unit tests see test_*_service.py.
"""

import os
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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


class TestAKCRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    @patch("modules.build_akc_context")
    def test_akc_context_post_validates_and_returns_checkpoint(self, mock_build):
        mock_build.return_value = {
            "status": "ready",
            "source_count": 1,
            "readable_count": 1,
            "missing_count": 0,
            "sources": [{"path_ref": "path-ref:abc", "readable": True}],
            "operating_rules": [{"key": "tdd_feedback", "summary": "Use TDD."}],
            "checkpoint_path": "path-ref:checkpoint",
            "checkpoint_markdown": "# AKC Context Checkpoint\n",
        }

        response = self.client.post(
            "/akc/context",
            json={"source_paths": [r"C:\safe\source.txt"], "checkpoint_path": r"C:\safe\akc.md"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["sources"][0]["path_ref"], "path-ref:abc")
        mock_build.assert_called_once()

    def test_akc_context_post_rejects_non_list_sources(self):
        response = self.client.post("/akc/context", json={"source_paths": "not-a-list"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    def test_akc_context_post_requires_at_least_one_source(self):
        response = self.client.post("/akc/context", json={"source_paths": []})
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least one", response.get_json()["details"])

    @patch("modules.load_akc_checkpoint")
    def test_akc_context_get_loads_checkpoint(self, mock_load):
        mock_load.return_value = {
            "exists": True,
            "checkpoint_path": "path-ref:checkpoint",
            "content": "# AKC Context Checkpoint\n",
            "char_count": 25,
        }

        response = self.client.get("/akc/context")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["exists"])
        mock_load.assert_called_once()

    @patch("modules.check_akc_readiness")
    def test_akc_readiness_get_checks_session_start_gate(self, mock_readiness):
        mock_readiness.return_value = {
            "status": "ready",
            "ready": True,
            "checkpoint_exists": True,
            "checkpoint_status": "ready",
            "checkpoint_path": "path-ref:checkpoint",
            "char_count": 120,
            "required_rules": ["context_system", "tdd_feedback"],
            "present_rules": ["context_system", "tdd_feedback"],
            "missing_required_rules": [],
            "gates": [
                {"name": "checkpoint_exists", "passed": True, "detail": "present"},
                {"name": "checkpoint_ready", "passed": True, "detail": "status=ready"},
                {"name": "required_rules_present", "passed": True, "detail": "all present"},
            ],
        }

        response = self.client.get("/akc/readiness")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["status"], "ready")
        mock_readiness.assert_called_once()


class TestEvidenceGate(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def _write_evidence(self, root_dir, timestamp):
        memory_dir = os.path.join(root_dir, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        with open(os.path.join(memory_dir, "test_evidence.json"), "w", encoding="utf-8") as handle:
            json.dump([
                {
                    "output_hash": "abc123",
                    "timestamp_utc": timestamp.isoformat(),
                    "passed": True,
                    "test_count": 1,
                    "raw_output_tail": "1 passed",
                }
            ], handle)

    @patch("modules.oracle_status")
    def test_stale_evidence_soft_mode_warns_only(self, mock_status):
        mock_status.return_value = {"status": "ok"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            stale = datetime.now(timezone.utc) - timedelta(hours=2)
            self._write_evidence(tmp_dir, stale)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "0"}):
                response = self.client.get("/oracle/status")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["X-Evidence-Age-Warning"].startswith("stale:"))
        self.assertEqual(response.get_json()["status"], "ok")

    @patch("modules.oracle_status")
    def test_stale_evidence_hard_mode_returns_423(self, mock_status):
        mock_status.return_value = {"status": "ok"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            stale = datetime.now(timezone.utc) - timedelta(hours=2)
            self._write_evidence(tmp_dir, stale)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.get("/oracle/status")

        self.assertEqual(response.status_code, 423)
        payload = response.get_json()
        self.assertEqual(payload["error"], "evidence_stale")
        self.assertGreater(payload["age_s"], 3600)
        self.assertEqual(payload["threshold_s"], 3600)
        mock_status.assert_not_called()

    @patch("modules.oracle_status")
    def test_fresh_evidence_hard_mode_allows_oracle_route(self, mock_status):
        mock_status.return_value = {"status": "ok"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            fresh = datetime.now(timezone.utc)
            self._write_evidence(tmp_dir, fresh)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.get("/oracle/status")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Evidence-Age-Warning", response.headers)

    def test_health_exempt_from_hard_evidence_gate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            stale = datetime.now(timezone.utc) - timedelta(hours=2)
            self._write_evidence(tmp_dir, stale)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_record_evidence_exempt_from_hard_evidence_gate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            stale = datetime.now(timezone.utc) - timedelta(hours=2)
            self._write_evidence(tmp_dir, stale)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.post(
                    "/retrospective/record_evidence",
                    json={"test_output": "================ 1 passed in 0.01s ================", "memory_path": os.path.join(tmp_dir, "memory")},
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["verified"])


class TestRetrospectiveRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def _report(self):
        report = MagicMock()
        report.session_id = "session"
        report.analyzed_at_utc = "2026-06-26T00:00:00+00:00"
        report.log_lines_analyzed = 0
        report.patterns = []
        report.doom_loops = []
        report.learnings = []
        report.memory_updates = {}
        report.has_doom_loops = False
        report.evidence = None
        report.to_summary.return_value = "summary"
        return report

    @patch("modules.analyze_session")
    def test_analyze_defaults_auto_prune_false(self, mock_analyze):
        mock_analyze.return_value = self._report()

        response = self.client.post("/retrospective/analyze", json={})

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_analyze.call_args.kwargs["auto_prune"], False)

    @patch("modules.analyze_session")
    def test_analyze_passes_auto_prune_true(self, mock_analyze):
        mock_analyze.return_value = self._report()

        response = self.client.post("/retrospective/analyze", json={"auto_prune": True})

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_analyze.call_args.kwargs["auto_prune"], True)


if __name__ == "__main__":
    unittest.main()
