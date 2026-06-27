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


BRIDGE_AUTH_HEADER = {"Authorization": "Bearer JULES-SECURE-999"}


def authed_client(test_client):
    """Wrap Flask test client so protected routes receive the bridge token."""

    class _AuthedClient:
        def get(self, path, **kwargs):
            headers = {**BRIDGE_AUTH_HEADER, **(kwargs.pop("headers", None) or {})}
            return test_client.get(path, headers=headers, **kwargs)

        def post(self, path, **kwargs):
            headers = {**BRIDGE_AUTH_HEADER, **(kwargs.pop("headers", None) or {})}
            return test_client.post(path, headers=headers, **kwargs)

    return _AuthedClient()


class TestInboxRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    def test_inbox_read_missing_file(self):
        response = self.client.post("/inbox/read", json={"file": "nonexistent.json"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("inbox file not found", response.get_json()["error"])

    def test_inbox_read_rejects_invalid_file_type(self):
        response = self.client.post("/inbox/read", json={"file": ["OPERATOR_RESPONSE.md"]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestJulesDispatchRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.build_dispatch")
    def test_jules_dispatch_passes_payload_to_module(self, mock_dispatch):
        mock_dispatch.return_value = {
            "task_count": 2,
            "selected_count": 1,
            "selected_tasks": [{"id": "JT-001"}],
            "packet_files": [],
            "launch_commands": ["jules new 'JT-001'"],
        }

        response = self.client.post(
            "/jules/dispatch",
            json={
                "content": "Testing Improvement Task",
                "max_instances": 1,
                "include_statuses": ["failed", "ready_for_review"],
                "repo_path": r"C:\aotp\projects\OracleV5",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["selected_count"], 1)
        self.assertEqual(
            mock_dispatch.call_args.kwargs["repo_path"],
            r"C:\aotp\projects\OracleV5",
        )
        self.assertEqual(mock_dispatch.call_args.kwargs["max_instances"], 1)
        self.assertEqual(
            mock_dispatch.call_args.kwargs["include_statuses"],
            ["failed", "ready_for_review"],
        )

    @patch("modules.build_dispatch")
    def test_jules_dispatch_returns_module_error_as_400(self, mock_dispatch):
        mock_dispatch.return_value = {
            "error": "content or source_path is required",
            "task_count": 0,
            "selected_count": 0,
        }

        response = self.client.post("/jules/dispatch", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "content or source_path is required")

    def test_jules_dispatch_rejects_invalid_include_statuses(self):
        response = self.client.post(
            "/jules/dispatch",
            json={"content": "x", "include_statuses": {"bad": "shape"}},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.launch_packets")
    def test_jules_launch_defaults_to_dry_run(self, mock_launch):
        mock_launch.return_value = {
            "dry_run": True,
            "selected_count": 1,
            "launched_count": 0,
            "results": [],
        }

        response = self.client.post(
            "/jules/launch",
            json={"packet_files": [r"C:\tmp\JT-001.md"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_launch.call_args.kwargs["dry_run"], True)
        self.assertEqual(mock_launch.call_args.kwargs["packet_files"], [r"C:\tmp\JT-001.md"])

    @patch("modules.launch_packets")
    def test_jules_launch_passes_force_packet_files_and_preserve_session_ids(self, mock_launch):
        mock_launch.return_value = {
            "dry_run": False,
            "selected_count": 1,
            "launched_count": 1,
            "results": [],
        }

        response = self.client.post(
            "/jules/launch",
            json={
                "packet_dir": r"C:\tmp",
                "force_packet_files": [r"C:\tmp\JT-001.md"],
                "preserve_existing_session_ids": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_launch.call_args.kwargs["force_packet_files"], [r"C:\tmp\JT-001.md"])
        self.assertIs(mock_launch.call_args.kwargs["preserve_existing_session_ids"], True)

    def test_jules_launch_rejects_invalid_packet_files(self):
        response = self.client.post(
            "/jules/launch",
            json={"packet_files": "not-a-list"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    def test_jules_launch_rejects_invalid_force_packet_files(self):
        response = self.client.post(
            "/jules/launch",
            json={"force_packet_files": "not-a-list"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.list_remote_sessions")
    def test_jules_sessions_defaults_to_dry_run(self, mock_sessions):
        mock_sessions.return_value = {
            "dry_run": True,
            "status": "dry_run",
            "session_ids": [],
        }

        response = self.client.post("/jules/sessions", json={})

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_sessions.call_args.kwargs["dry_run"], True)

    @patch("modules.jules_preflight")
    def test_jules_preflight_defaults_to_remote_check(self, mock_preflight):
        mock_preflight.return_value = {
            "ready": False,
            "likely_blocker": "remote_timeout",
        }

        response = self.client.post("/jules/preflight", json={})

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_preflight.call_args.kwargs["check_remote"], True)
        self.assertEqual(mock_preflight.call_args.kwargs["timeout_s"], 8)

    @patch("modules.pull_remote_session")
    def test_jules_pull_defaults_to_dry_run(self, mock_pull):
        mock_pull.return_value = {
            "dry_run": True,
            "status": "dry_run",
            "session_id": "123456",
        }

        response = self.client.post("/jules/pull", json={"session_id": "123456"})

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_pull.call_args.kwargs["dry_run"], True)
        self.assertEqual(mock_pull.call_args.kwargs["session_id"], "123456")

    def test_jules_pull_requires_session_id(self):
        response = self.client.post("/jules/pull", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.build_cot_ledger")
    def test_jules_cot_writes_ledger_by_default(self, mock_cot):
        mock_cot.return_value = {
            "selected_count": 1,
            "completed_count": 0,
            "all_complete": False,
            "rows": [],
        }

        response = self.client.post("/jules/cot", json={"packet_dir": r"C:\tmp\dispatch"})

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_cot.call_args.kwargs["write_ledger"], True)
        self.assertEqual(mock_cot.call_args.kwargs["packet_dir"], r"C:\tmp\dispatch")

    @patch("modules.run_jules_cycle")
    def test_jules_cycle_defaults_to_safe_dry_run(self, mock_cycle):
        mock_cycle.return_value = {
            "status": "pending",
            "dry_run": True,
            "launch_dry_run": True,
            "cot": {},
        }

        response = self.client.post(
            "/jules/cycle",
            json={"path": r"C:\tmp\queue.txt", "packet_dir": r"C:\tmp\dispatch"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_cycle.call_args.kwargs["dry_run"], True)
        self.assertIs(mock_cycle.call_args.kwargs["launch"], False)
        self.assertIs(mock_cycle.call_args.kwargs["require_remote_ready"], True)
        self.assertEqual(mock_cycle.call_args.kwargs["source_path"], r"C:\tmp\queue.txt")

    def test_jules_cycle_rejects_invalid_session_ids(self):
        response = self.client.post(
            "/jules/cycle",
            json={"session_ids": "123456"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.run_jules_watch")
    def test_jules_watch_defaults_to_safe_dry_run(self, mock_watch):
        mock_watch.return_value = {
            "status": "dry_run",
            "dry_run": True,
            "iterations": [],
        }

        response = self.client.post(
            "/jules/watch",
            json={"packet_dir": r"C:\tmp\dispatch", "max_wait_s": 0},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_watch.call_args.kwargs["dry_run"], True)
        self.assertEqual(mock_watch.call_args.kwargs["max_wait_s"], 0)
        self.assertEqual(mock_watch.call_args.kwargs["poll_interval_s"], 30)
        self.assertEqual(mock_watch.call_args.kwargs["packet_dir"], r"C:\tmp\dispatch")

    @patch("modules.run_jules_fleet")
    def test_jules_fleet_defaults_to_safe_dry_run(self, mock_fleet):
        mock_fleet.return_value = {
            "status": "pending",
            "dry_run": True,
            "launch_dry_run": True,
            "requested_launch_limit": 0,
        }

        response = self.client.post(
            "/jules/fleet",
            json={
                "path": r"C:\tmp\queue.txt",
                "packet_dir": r"C:\tmp\dispatch",
                "max_concurrent": 8,
                "launch_batch_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_fleet.call_args.kwargs["dry_run"], True)
        self.assertIs(mock_fleet.call_args.kwargs["require_remote_ready"], True)
        self.assertEqual(mock_fleet.call_args.kwargs["source_path"], r"C:\tmp\queue.txt")
        self.assertEqual(mock_fleet.call_args.kwargs["packet_dir"], r"C:\tmp\dispatch")
        self.assertEqual(mock_fleet.call_args.kwargs["max_instances"], 12)
        self.assertEqual(mock_fleet.call_args.kwargs["max_concurrent"], 8)
        self.assertEqual(mock_fleet.call_args.kwargs["launch_batch_size"], 2)

    def test_jules_fleet_rejects_invalid_include_statuses(self):
        response = self.client.post(
            "/jules/fleet",
            json={"include_statuses": {"bad": "shape"}},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.run_jules_fleet_watch")
    def test_jules_fleet_watch_defaults_to_safe_dry_run(self, mock_fleet_watch):
        mock_fleet_watch.return_value = {
            "status": "dry_run",
            "dry_run": True,
            "iterations": [],
        }

        response = self.client.post(
            "/jules/fleet-watch",
            json={
                "path": r"C:\tmp\queue.txt",
                "packet_dir": r"C:\tmp\dispatch",
                "max_wait_s": 0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(mock_fleet_watch.call_args.kwargs["dry_run"], True)
        self.assertIs(mock_fleet_watch.call_args.kwargs["require_remote_ready"], True)
        self.assertEqual(mock_fleet_watch.call_args.kwargs["source_path"], r"C:\tmp\queue.txt")
        self.assertEqual(mock_fleet_watch.call_args.kwargs["packet_dir"], r"C:\tmp\dispatch")
        self.assertEqual(mock_fleet_watch.call_args.kwargs["max_instances"], 12)
        self.assertEqual(mock_fleet_watch.call_args.kwargs["max_concurrent"], 6)
        self.assertEqual(mock_fleet_watch.call_args.kwargs["launch_batch_size"], 2)
        self.assertEqual(mock_fleet_watch.call_args.kwargs["max_wait_s"], 0)
        self.assertEqual(mock_fleet_watch.call_args.kwargs["poll_interval_s"], 30)

    def test_jules_fleet_watch_rejects_invalid_include_statuses(self):
        response = self.client.post(
            "/jules/fleet-watch",
            json={"include_statuses": {"bad": "shape"}},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestFsRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

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
        self.client = authed_client(bridge.app.test_client())

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


class TestExecuteRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    def test_execute_requires_at_least_one_action(self):
        response = self.client.post("/execute", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("At least one of click, type, text, or shell", response.get_json()["details"])

    @patch("modules.spawn")
    def test_execute_shell_spawns_by_default(self, mock_spawn):
        mock_spawn.return_value = {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "shell": "cmd",
            "pid": 4242,
            "spawned": True,
        }

        response = self.client.post(
            "/execute",
            json={"shell": "start msedge https://www.google.com"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "executed")
        self.assertEqual(payload["actions"]["shell"]["pid"], 4242)
        mock_spawn.assert_called_once_with(
            "start msedge https://www.google.com",
            shell="cmd",
            cwd=os.getcwd(),
        )

    @patch("modules.click")
    def test_execute_click_delegates_to_ui_module(self, mock_click):
        mock_click.return_value = {"status": "Clicked 500, 500"}

        response = self.client.post(
            "/execute",
            json={"click": {"x": 500, "y": 500}},
        )

        self.assertEqual(response.status_code, 200)
        mock_click.assert_called_once_with(500, 500, button="left")

    @patch("modules.type_text")
    def test_execute_type_accepts_type_key(self, mock_type):
        mock_type.return_value = {"status": "Typed successfully"}

        response = self.client.post("/execute", json={"type": "hello"})

        self.assertEqual(response.status_code, 200)
        mock_type.assert_called_once_with("hello")

    @patch("modules.spawn")
    @patch("modules.click")
    @patch("modules.type_text")
    def test_execute_runs_shell_then_click_then_type(self, mock_type, mock_click, mock_spawn):
        mock_spawn.return_value = {"exit_code": 0, "stdout": "", "stderr": "", "shell": "cmd", "pid": 1}
        mock_click.return_value = {"status": "Clicked 1, 2"}
        mock_type.return_value = {"status": "Typed successfully"}

        response = self.client.post(
            "/execute",
            json={
                "shell": "start notepad",
                "click": {"x": 1, "y": 2},
                "type": "abc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertEqual(mock_click.call_count, 1)
        self.assertEqual(mock_type.call_count, 1)


class TestUIRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

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

    @patch("modules.drive_quantower_login")
    def test_ui_drive_quantower_login_route_is_thin(self, mock_drive):
        mock_drive.return_value = {
            "status": "unknown",
            "state": "unknown",
            "acted": False,
            "message": "State unknown",
            "error": None,
        }

        response = self.client.post(
            "/ui/drive_quantower_login",
            json={
                "ocr_text": "unknown",
                "submit_x": 100,
                "submit_y": 200,
                "allow_secret_use": False,
                "notify": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "unknown")
        mock_drive.assert_called_once()
        kwargs = mock_drive.call_args.kwargs
        self.assertEqual(kwargs["ocr_text"], "unknown")
        self.assertEqual(kwargs["submit_x"], 100)
        self.assertEqual(kwargs["submit_y"], 200)
        self.assertFalse(kwargs["allow_secret_use"])
        self.assertIsNone(kwargs["notify_func"])


class TestAKCRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

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

    @patch("modules.build_context_subagents")
    def test_akc_subagents_builds_context_plan(self, mock_subagents):
        mock_subagents.return_value = {
            "status": "ready",
            "source_count": 1,
            "readable_count": 1,
            "missing_count": 0,
            "context_strategy": "smart_truncation_head_tail_memory_store",
            "subagents": [{"role_id": "implementation_planner"}],
            "packet_files": [],
        }

        response = self.client.post(
            "/akc/subagents",
            json={
                "content": "context engineering",
                "task": "Optimize context handling",
                "roles": ["implementation_planner"],
                "head_chars": 120,
                "tail_chars": 120,
                "max_packet_chars": 4000,
                "context_window_chars": 10000,
                "max_context_utilization_percent": 35,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")
        self.assertEqual(mock_subagents.call_args.kwargs["roles"], ["implementation_planner"])
        self.assertEqual(mock_subagents.call_args.kwargs["head_chars"], 120)
        self.assertEqual(mock_subagents.call_args.kwargs["task"], "Optimize context handling")
        self.assertEqual(mock_subagents.call_args.kwargs["context_window_chars"], 10000)
        self.assertEqual(mock_subagents.call_args.kwargs["max_context_utilization"], 0.35)

    def test_akc_subagents_requires_content_or_sources(self):
        response = self.client.post("/akc/subagents", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")
        self.assertIn("content or source_paths", response.get_json()["details"])

    def test_akc_subagents_rejects_invalid_roles(self):
        response = self.client.post(
            "/akc/subagents",
            json={"content": "x", "roles": "implementation_planner"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestEvidenceGate(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

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
        self.client = authed_client(bridge.app.test_client())

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


class TestBridgeTokenAuth(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def test_ping_and_health_exempt_without_token(self):
        for path in ("/ping", "/health"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_protected_route_rejects_missing_token(self):
        response = self.client.post("/notify/email", json={"subject": "x", "body": "y"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Unauthorized")

    def test_protected_route_accepts_bearer_token(self):
        with patch("bridge.email_service.send_email", return_value={"status": "sent"}):
            response = self.client.post(
                "/notify/email",
                json={"subject": "x", "body": "y"},
                headers=BRIDGE_AUTH_HEADER,
            )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
