"""Integration tests for bridge.py HTTP routes.

These test the HTTP surface — validate → call module → JSON response.
Module internals are mocked. For module-level unit tests see test_*_service.py.
"""

import os
import sys
os.environ["BRIDGE_TOKEN"] = "JULES-SECURE-999"
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

    @patch("modules.jules_api_list_sources")
    def test_jules_api_sources_delegates_to_module(self, mock_sources):
        mock_sources.return_value = {
            "status": "ok",
            "sources": [{"name": "sources/github/Job4874/jules-bridge"}],
            "source_names": ["sources/github/Job4874/jules-bridge"],
        }

        response = self.client.post("/jules/api/sources", json={"page_size": 10})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["source_names"], ["sources/github/Job4874/jules-bridge"])
        self.assertEqual(mock_sources.call_args.kwargs["page_size"], 10)

    @patch("modules.jules_api_list_sessions")
    def test_jules_api_sessions_list_delegates_to_module(self, mock_sessions):
        mock_sessions.return_value = {
            "status": "ok",
            "session_ids": ["123456"],
            "sessions": [{"id": "123456"}],
        }

        response = self.client.post("/jules/api/sessions/list", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["session_ids"], ["123456"])
        self.assertEqual(mock_sessions.call_args.kwargs["page_size"], 5)

    @patch("modules.jules_api_create_session")
    def test_jules_api_sessions_create_delegates_to_module(self, mock_create):
        mock_create.return_value = {
            "status": "ok",
            "session_ids": ["314159"],
            "session": {"id": "314159"},
        }

        response = self.client.post(
            "/jules/api/sessions",
            json={
                "prompt": "Fix provider blockers",
                "title": "Local bridge fix",
                "source": "sources/github/Job4874/jules-bridge",
                "starting_branch": "master",
                "require_plan_approval": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["session_ids"], ["314159"])
        self.assertEqual(mock_create.call_args.kwargs["prompt"], "Fix provider blockers")
        self.assertEqual(mock_create.call_args.kwargs["source"], "sources/github/Job4874/jules-bridge")
        self.assertEqual(mock_create.call_args.kwargs["starting_branch"], "master")
        self.assertIs(mock_create.call_args.kwargs["require_plan_approval"], True)

    def test_jules_api_sessions_create_requires_prompt(self):
        response = self.client.post("/jules/api/sessions", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.jules_api_get_session")
    def test_jules_api_sessions_get_delegates_to_module(self, mock_get):
        mock_get.return_value = {
            "status": "ok",
            "session_ids": ["123456"],
            "session": {"id": "123456"},
        }

        response = self.client.post("/jules/api/sessions/get", json={"session_id": "123456"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_get.call_args.kwargs["session_id"], "123456")

    @patch("modules.jules_api_list_activities")
    def test_jules_api_activities_delegates_to_module(self, mock_activities):
        mock_activities.return_value = {
            "status": "ok",
            "activities": [{"name": "activity/1"}],
        }

        response = self.client.post(
            "/jules/api/sessions/activities",
            json={"session_id": "123456", "page_size": 20},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_activities.call_args.kwargs["session_id"], "123456")
        self.assertEqual(mock_activities.call_args.kwargs["page_size"], 20)

    @patch("modules.jules_api_send_message")
    def test_jules_api_send_message_delegates_to_module(self, mock_send):
        mock_send.return_value = {"status": "ok"}

        response = self.client.post(
            "/jules/api/sessions/send-message",
            json={"session_id": "123456", "prompt": "continue"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_args.kwargs["prompt"], "continue")

    @patch("modules.jules_api_approve_plan")
    def test_jules_api_approve_plan_delegates_to_module(self, mock_approve):
        mock_approve.return_value = {"status": "ok"}

        response = self.client.post(
            "/jules/api/sessions/approve-plan",
            json={"session_id": "123456"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_approve.call_args.kwargs["session_id"], "123456")

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
    def test_shell_invalid_git_bash(self, _mock_which):
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

    @patch("modules.oracle_status")
    def test_clock_skew_hard_mode_returns_423(self, mock_status):
        mock_status.return_value = {"status": "ok"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            future = datetime.now(timezone.utc) + timedelta(hours=2)
            self._write_evidence(tmp_dir, future)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.get("/oracle/status")

        self.assertEqual(response.status_code, 423)
        self.assertEqual(response.get_json()["reason"], "clock_skew")
        mock_status.assert_not_called()

    @patch("modules.oracle_status")
    def test_malformed_evidence_hard_mode_returns_423(self, mock_status):
        mock_status.return_value = {"status": "ok"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_dir = os.path.join(tmp_dir, "memory")
            os.makedirs(memory_dir, exist_ok=True)
            with open(os.path.join(memory_dir, "test_evidence.json"), "w", encoding="utf-8") as handle:
                handle.write("{not valid json")
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.get("/oracle/status")

        self.assertEqual(response.status_code, 423)
        self.assertEqual(response.get_json()["reason"], "malformed")
        mock_status.assert_not_called()

    @patch("modules.oracle_status")
    def test_missing_evidence_hard_mode_allows_oracle_route(self, mock_status):
        mock_status.return_value = {"status": "ok"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.makedirs(os.path.join(tmp_dir, "memory"), exist_ok=True)
            with patch.object(bridge, "ROOT_DIR", tmp_dir), patch.dict(os.environ, {"EVIDENCE_GATE_HARD": "1"}):
                response = self.client.get("/oracle/status")

        self.assertEqual(response.status_code, 200)

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


class TestAppLauncherRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.launch_browser_to_url")
    def test_launch_browser_route_is_thin(self, mock_launch):
        mock_launch.return_value = {
            "status": "success",
            "app_name": "msedge",
            "started": True,
            "error": None,
        }

        response = self.client.post(
            "/apps/launch_browser",
            json={"url": "https://example.com", "allow_launch": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "success")
        mock_launch.assert_called_once_with(
            "https://example.com",
            allow_launch=True,
        )

    def test_launch_browser_requires_url(self):
        response = self.client.post("/apps/launch_browser", json={"allow_launch": True})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestRepoContextGuardRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.build_repo_context_guard")
    def test_repo_context_guard_delegates_to_module(self, mock_guard):
        mock_guard.return_value = {
            "status": "ready",
            "summary": {"repo_count": 1, "collision_count": 0},
            "repos": [{"name": "jules-bridge"}],
            "collisions": [],
            "guardrails": [],
        }

        response = self.client.get(
            "/repo/context-guard?root=C:/repos&max_depth=2&max_repos=25&include_repos=false&use_cache=false"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")
        mock_guard.assert_called_once_with(
            roots=["C:/repos"],
            max_depth=2,
            max_repos=25,
            include_repos=False,
            use_cache=False,
        )

    def test_repo_context_guard_rejects_bad_query(self):
        response = self.client.get("/repo/context-guard?max_depth=deep")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestVMRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.detect_resource_pressure")
    def test_vm_resource_pressure_route_is_thin(self, mock_pressure):
        mock_pressure.return_value = {
            "status": "maxed_out",
            "cpu_percent": 92.0,
            "memory_percent": 71.0,
            "maxed_out": True,
            "reasons": ["cpu_percent 92.0 >= 90.0"],
            "error": None,
        }

        response = self.client.post(
            "/vm/resource_pressure",
            json={
                "cpu_percent": 92,
                "memory_percent": 71,
                "cpu_threshold": 90,
                "memory_threshold": 85,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "maxed_out")
        mock_pressure.assert_called_once_with(
            cpu_percent=92,
            memory_percent=71,
            thresholds={"cpu_percent": 90, "memory_percent": 85},
        )

    @patch("modules.boot_secondary_vm")
    def test_vm_boot_secondary_route_defaults_to_dry_run(self, mock_boot):
        mock_boot.return_value = {
            "status": "dry_run",
            "selected_script": r"C:\vm\Start-SecondaryVM.ps1",
            "started": False,
            "dry_run": True,
            "error": None,
        }

        response = self.client.post(
            "/vm/boot_secondary",
            json={"script_name": "Start-SecondaryVM.ps1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "dry_run")
        mock_boot.assert_called_once_with(
            "Start-SecondaryVM.ps1",
            allow_vm_boot=False,
            dry_run=True,
        )


class TestDiscoveryRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    def test_root_returns_authenticated_route_manifest(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["bridge"], "Jules Bridge")
        self.assertEqual(payload["manifest"], "GET /tentacles")
        self.assertIn("routes", payload)
        self.assertIn(
            {
                "name": "info",
                "route": "GET /info",
                "reach": "Authenticated bridge metadata without the full manifest",
            },
            payload["routes"],
        )

    def test_info_returns_compact_authenticated_metadata(self):
        response = self.client.get("/info")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["route_count"], len(bridge.TENTACLES))
        self.assertNotIn("routes", payload)


class TestBridgeTokenAuth(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def test_ping_and_health_exempt_without_token(self):
        for path in ("/ping", "/health", "/host/identity"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_host_gpg_public_requires_auth(self):
        response = self.client.get("/host/gpg/public")
        self.assertEqual(response.status_code, 401)

    @patch("modules.host_identity.get_gpg_public_payload")
    def test_host_gpg_public_returns_key_when_configured(self, mock_payload):
        mock_payload.return_value = {
            "title": "jules",
            "key_id": "D9BC48A619204DA7",
            "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\nabc\n-----END PGP PUBLIC KEY BLOCK-----",
            "configured": True,
            "github_add_url": "https://github.com/settings/gpg/new",
        }
        response = self.client.get("/host/gpg/public", headers=BRIDGE_AUTH_HEADER)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["title"], "jules")
        self.assertIn("BEGIN PGP PUBLIC KEY BLOCK", body["public_key"])

    def test_protected_route_rejects_missing_token(self):
        response = self.client.post("/notify/email", json={"subject": "x", "body": "y"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Unauthorized")

    def test_root_discovery_rejects_missing_token(self):
        response = self.client.get("/")
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

    def test_notify_email_forwards_existing_attachments(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"screen")
            attachment = handle.name
        try:
            with patch("bridge.email_service.send_email", return_value={"status": "sent"}) as mock_send:
                response = self.client.post(
                    "/notify/email",
                    json={"subject": "x", "body": "y", "attachments": [attachment]},
                    headers=BRIDGE_AUTH_HEADER,
                )

            self.assertEqual(response.status_code, 200)
            mock_send.assert_called_once_with(
                "x",
                "y",
                mail_to=None,
                attachments=[attachment],
            )
        finally:
            os.unlink(attachment)

    def test_notify_email_rejects_missing_attachment_before_send(self):
        missing = os.path.join(tempfile.gettempdir(), "jules-missing-screenshot.png")
        if os.path.exists(missing):
            os.unlink(missing)

        with patch("bridge.email_service.send_email") as mock_send:
            response = self.client.post(
                "/notify/email",
                json={"subject": "x", "body": "y", "attachments": [missing]},
                headers=BRIDGE_AUTH_HEADER,
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Resource not found")
        mock_send.assert_not_called()


class TestChatRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    @patch("modules.test_chat_providers")
    def test_chat_test_delegates_to_module(self, mock_test):
        mock_test.return_value = {"healthy": False, "providers": {"gemini": {"status": "no_key"}}}

        response = self.client.get("/chat/test")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["healthy"])
        mock_test.assert_called_once_with()

    @patch("modules.chat")
    def test_chat_route_is_thin(self, mock_chat):
        mock_chat.return_value = {"response": "ok", "model_used": "stub", "elapsed_ms": 1, "errors": []}

        response = self.client.post(
            "/chat",
            json={
                "message": "hello",
                "model": "smart",
                "system": "system",
                "image_base64": "abc",
                "history": [{"role": "user", "content": "prior"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["response"], "ok")
        mock_chat.assert_called_once_with(
            message="hello",
            model_alias="smart",
            system_prompt="system",
            image_base64="abc",
            history=[{"role": "user", "content": "prior"}],
        )


class TestGhostRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    def test_ghost_status_public_without_token(self):
        response = self.client.get("/ghost/status")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("ghost_locked", body)
        self.assertNotIn("unlock_password_hash", body)

    @patch("modules.ghost_state.lock_ghost")
    def test_ghost_lock_requires_auth_and_password(self, mock_lock):
        mock_lock.return_value = {
            "status": "locked",
            "locked_at_utc": "2026-07-01T00:00:00+00:00",
            "host_id": "school-64gb",
            "location": "school",
        }
        denied = self.client.post("/ghost/lock", json={"password": "secret"})
        self.assertEqual(denied.status_code, 401)

        response = self.client.post(
            "/ghost/lock",
            json={"password": "secret"},
            headers=BRIDGE_AUTH_HEADER,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ghost_locked"])

    @patch("modules.ghost_state.unlock_ghost")
    def test_ghost_unlock_rejects_bad_password(self, mock_unlock):
        mock_unlock.return_value = {"status": "denied", "error": "invalid unlock password"}
        response = self.client.post(
            "/ghost/unlock",
            json={"password": "wrong"},
            headers=BRIDGE_AUTH_HEADER,
        )
        self.assertEqual(response.status_code, 403)

    def test_ping_includes_ghost_fields(self):
        response = self.client.get("/ping")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("ghost_locked", body)
        self.assertIn("host_id", body)




class TestAdditionalFsRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.read")
    def test_fs_read_success(self, mock_read):
        mock_read.return_value = {"content": "hello"}
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"")
            path = f.name
        try:
            response = self.client.post("/fs/read", json={"path": path, "offset": 0, "limit": 10})
            self.assertEqual(response.status_code, 200)
            mock_read.assert_called_with(path, offset=0, limit=10)
        finally:
            os.unlink(path)

    @patch("modules.list_dir")
    def test_fs_list_success(self, mock_list):
        mock_list.return_value = [{"name": "file.txt"}]
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            response = self.client.post("/fs/list", json={"path": temp_dir})
            self.assertEqual(response.status_code, 200)
            mock_list.assert_called_with(temp_dir)

    @patch("modules.tail")
    def test_fs_tail_success(self, mock_tail):
        mock_tail.return_value = {"lines": ["end"]}
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"")
            path = f.name
        try:
            response = self.client.post("/fs/tail", json={"path": path, "lines": 10})
            self.assertEqual(response.status_code, 200)
            mock_tail.assert_called_with(path, lines=10)
        finally:
            os.unlink(path)

    @patch("modules.grep")
    def test_fs_grep_success(self, mock_grep):
        mock_grep.return_value = {"matches": []}
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"")
            path = f.name
        try:
            response = self.client.post("/fs/grep", json={"path": path, "pattern": "error", "max_matches": 10})
            self.assertEqual(response.status_code, 200)
            mock_grep.assert_called_with(path, pattern="error", max_matches=10)
        finally:
            os.unlink(path)


class TestAdditionalOracleRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.oracle_build_deploy")
    def test_oracle_build_deploy(self, mock_build):
        mock_build.return_value = {"status": "deployed"}
        response = self.client.post("/oracle/build-deploy")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "deployed")
        mock_build.assert_called_once()


class TestCodexHandoverRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.codex_handover_index")
    def test_codex_handover(self, mock_codex):
        mock_codex.return_value = {"status": "ok"}
        response = self.client.get("/codex/handover")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        mock_codex.assert_called_once()


class TestAdditionalUIRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.screenshot")
    def test_ui_screenshot(self, mock_screenshot):
        mock_screenshot.return_value = {"status": "ok"}
        response = self.client.get("/ui/screenshot?save=1")
        self.assertEqual(response.status_code, 200)
        mock_screenshot.assert_called_once_with(save=True)

    @patch("modules.type_text")
    def test_ui_type(self, mock_type):
        mock_type.return_value = {"status": "typed"}
        response = self.client.post("/ui/type", json={"text": "hello"})
        self.assertEqual(response.status_code, 200)
        mock_type.assert_called_once_with("hello")


class TestReasoningRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.reason")
    def test_reasoning_solve(self, mock_reason):
        mock_reason.return_value = MagicMock(
            problem="prob", answer="ans", succeeded=True, elapsed_ms=10.0,
            plan=MagicMock(goal_statement="g", steps=[], confidence=1.0, model="m"),
            actions=[],
            halt=MagicMock(reason="done", steps_used=1, steps_budget=8, halted_early=False),
            feedback="fb"
        )
        response = self.client.post("/reasoning/solve", json={"problem": "prob"})
        self.assertEqual(response.status_code, 200)
        mock_reason.assert_called_once()

    @patch("modules.plan_only")
    def test_reasoning_plan(self, mock_plan):
        mock_plan.return_value = MagicMock(
            goal_statement="g", steps=[], step_count=0, confidence=1.0, model="m"
        )
        response = self.client.post("/reasoning/plan", json={"problem": "prob"})
        self.assertEqual(response.status_code, 200)
        mock_plan.assert_called_once()

    @patch("modules.execute_step")
    def test_reasoning_execute_step(self, mock_exec):
        mock_exec.return_value = MagicMock(
            step_index=0, step_description="d", action_type="a", payload={}, confidence=1.0, should_execute=True
        )
        response = self.client.post("/reasoning/execute_step", json={"step": "step1"})
        self.assertEqual(response.status_code, 200)
        mock_exec.assert_called_once()

    @patch("modules.reasoning_module.discover_skills")
    def test_reasoning_skills(self, mock_skills):
        mock_skills.return_value = []
        response = self.client.get("/reasoning/skills")
        self.assertEqual(response.status_code, 200)
        mock_skills.assert_called_once()

    @patch("modules.reasoning_module.inject_gotcha")
    def test_reasoning_inject_gotcha(self, mock_gotcha):
        mock_gotcha.return_value = {"status": "injected"}
        response = self.client.post("/reasoning/inject_gotcha", json={"module": "m", "text": "t"})
        self.assertEqual(response.status_code, 200)
        mock_gotcha.assert_called_once()


class TestAdditionalRetrospectiveRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.load_memory")
    def test_retrospective_memory(self, mock_load):
        mock_load.return_value = "memory content"
        response = self.client.get("/retrospective/memory?domain=general")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["content"], "memory content")
        mock_load.assert_called_once()

    def test_retrospective_memory_invalid_domain(self):
        response = self.client.get("/retrospective/memory?domain=invalid")
        self.assertEqual(response.status_code, 400)

    @patch("modules.prune_memory")
    def test_retrospective_prune_memory(self, mock_prune):
        mock_prune.return_value = {"pruned_count": 1, "domains_affected": ["general"]}
        response = self.client.post("/retrospective/prune_memory", json={"max_age_days": 10})
        self.assertEqual(response.status_code, 200)
        mock_prune.assert_called_once()

    @patch("modules.retrospective_module.assess_memory_quality")
    def test_retrospective_memory_quality(self, mock_assess):
        mock_assess.return_value = {"quality": "good"}
        response = self.client.get("/retrospective/memory_quality?domain=general")
        self.assertEqual(response.status_code, 200)
        mock_assess.assert_called_once()


class TestDashboardRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.dashboard_module.get_dashboard_status")
    def test_dashboard_status(self, mock_dash):
        mock_dash.return_value = {"ok": True, "data": "data"}
        response = self.client.get("/dashboard/status")
        self.assertEqual(response.status_code, 200)
        mock_dash.assert_called_once()


class TestAdditionalVMRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.vm_relay.bootstrap_vm")
    def test_vm_bootstrap(self, mock_boot):
        mock_boot.return_value = {"ok": True}
        response = self.client.post("/vm/bootstrap")
        self.assertEqual(response.status_code, 200)
        mock_boot.assert_called_once()

    @patch("modules.vm_relay.send_task_to_vm")
    def test_vm_task(self, mock_task):
        mock_task.return_value = {"ok": True}
        response = self.client.post("/vm/task", json={"task": "t", "task_type": "build"})
        self.assertEqual(response.status_code, 200)
        mock_task.assert_called_once()

    @patch("modules.vm_relay.get_vm_status")
    def test_vm_status(self, mock_status):
        mock_status.return_value = {"ok": True}
        response = self.client.get("/vm/status")
        self.assertEqual(response.status_code, 200)
        mock_status.assert_called_once()


class TestMissionRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.mission_controller.load_queue")
    def test_mission_queue(self, mock_load):
        q = MagicMock(tasks=[], pending_count=0, active_count=0, done_count=0, parsed_at="now")
        mock_load.return_value = q
        response = self.client.get("/mission/queue")
        self.assertEqual(response.status_code, 200)
        mock_load.assert_called_once()

    @patch("modules.mission_controller.run_mission_cycle")
    def test_mission_cycle(self, mock_cycle):
        mock_cycle.return_value = MagicMock(ok=True, active_task=None, queue_summary={}, timestamp="now", error=None)
        response = self.client.post("/mission/cycle")
        self.assertEqual(response.status_code, 200)
        mock_cycle.assert_called_once()

    @patch("modules.mission_controller.load_queue")
    @patch("modules.mission_controller.mark_task_done")
    def test_mission_done(self, mock_mark, mock_load):
        t = MagicMock(task_id="t1")
        mock_load.return_value = MagicMock(tasks=[t])
        response = self.client.post("/mission/done", json={"task_id": "t1"})
        self.assertEqual(response.status_code, 200)
        mock_mark.assert_called_once()

    @patch("modules.mission_controller.load_queue")
    @patch("modules.mission_controller.mark_task_failed")
    def test_mission_failed(self, mock_mark, mock_load):
        t = MagicMock(task_id="t1")
        mock_load.return_value = MagicMock(tasks=[t])
        response = self.client.post("/mission/failed", json={"task_id": "t1"})
        self.assertEqual(response.status_code, 200)
        mock_mark.assert_called_once()

    @patch("modules.learning_loop.weekly_digest")
    def test_mission_digest(self, mock_digest):
        mock_digest.return_value = MagicMock(ok=True, tasks_done=0, tasks_failed=0, summary="", digest_path="", error="")
        response = self.client.get("/mission/digest")
        self.assertEqual(response.status_code, 200)
        mock_digest.assert_called_once()


class TestBrowserRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.playwright_agent.navigate")
    def test_browser_navigate(self, mock_nav):
        mock_nav.return_value = MagicMock(ok=True, url="url", page_text="", screenshot_path="", timing_ms=1, error="")
        response = self.client.post("/browser/navigate", json={"url": "http://a.b"})
        self.assertEqual(response.status_code, 200)
        mock_nav.assert_called_once()

    @patch("modules.playwright_agent.take_screenshot")
    def test_browser_screenshot(self, mock_sc):
        mock_sc.return_value = MagicMock(ok=True, url="url", screenshot_path="", timing_ms=1, error="")
        response = self.client.post("/browser/screenshot", json={"url": "http://a.b"})
        self.assertEqual(response.status_code, 200)
        mock_sc.assert_called_once()

    @patch("modules.playwright_agent.fill_and_submit_form")
    def test_browser_form(self, mock_form):
        mock_form.return_value = MagicMock(ok=True, url="url", form_submitted=True, screenshot_path="", page_text="", timing_ms=1, error="")
        response = self.client.post("/browser/form", json={"url": "http://a.b"})
        self.assertEqual(response.status_code, 200)
        mock_form.assert_called_once()

    @patch("modules.academic_agent.solve_quiz")
    def test_browser_quiz(self, mock_quiz):
        mock_quiz.return_value = MagicMock(ok=True, url="url", questions_found=0, questions_answered=0, submitted=True, screenshot_path="", ai_answers=[], timestamp="", error="")
        response = self.client.post("/browser/quiz", json={"url": "http://a.b"})
        self.assertEqual(response.status_code, 200)
        mock_quiz.assert_called_once()

    @patch("modules.academic_agent.solve_assignment")
    def test_browser_assignment(self, mock_ass):
        mock_ass.return_value = MagicMock(ok=True, url="url", questions_found=0, ai_answers=[], screenshot_path="", timestamp="", error="")
        response = self.client.post("/browser/assignment", json={"url": "http://a.b"})
        self.assertEqual(response.status_code, 200)
        mock_ass.assert_called_once()


class TestLearningReflectRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.learning_loop.reflect_on_task")
    def test_learning_reflect(self, mock_reflect):
        mock_reflect.return_value = MagicMock(ok=True, task_id="t", lesson="l", memory_updated=True, error="")
        response = self.client.post("/learning/reflect", json={"task": {}})
        self.assertEqual(response.status_code, 200)
        mock_reflect.assert_called_once()


class TestAgentRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.agent_preflight")
    def test_agent_preflight(self, mock_pre):
        mock_pre.return_value = {"ready": True}
        response = self.client.post("/agent/preflight")
        self.assertEqual(response.status_code, 200)
        mock_pre.assert_called_once()

    @patch("modules.agent_chat")
    def test_agent_chat(self, mock_chat):
        mock_chat.return_value = {"status": "ok"}
        response = self.client.post("/agent/chat", json={"prompt": "hi"})
        self.assertEqual(response.status_code, 200)
        mock_chat.assert_called_once()

    @patch("modules.agent_stream")
    def test_agent_stream(self, mock_stream):
        mock_stream.return_value = {"status": "ok"}
        response = self.client.post("/agent/stream", json={"prompt": "hi"})
        self.assertEqual(response.status_code, 200)
        mock_stream.assert_called_once()


class TestGeminiRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.gemini_preflight")
    def test_gemini_preflight(self, mock_pre):
        mock_pre.return_value = {"ready": True}
        response = self.client.post("/gemini/preflight", json={})
        self.assertEqual(response.status_code, 200)
        mock_pre.assert_called_once()

    @patch("modules.run_gemini_prompt")
    def test_gemini_prompt(self, mock_prompt):
        mock_prompt.return_value = {"status": "ok"}
        response = self.client.post("/gemini/prompt", json={"prompt": "hi"})
        self.assertEqual(response.status_code, 200)
        mock_prompt.assert_called_once()


class TestAntigravityRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.antigravity_preflight")
    def test_antigravity_preflight(self, mock_pre):
        mock_pre.return_value = {"ready": True}
        response = self.client.post("/gemini/antigravity/preflight", json={})
        self.assertEqual(response.status_code, 200)
        mock_pre.assert_called_once()

    @patch("modules.run_antigravity_prompt")
    def test_antigravity_prompt(self, mock_prompt):
        mock_prompt.return_value = {"status": "ok"}
        response = self.client.post("/gemini/antigravity/prompt", json={"prompt": "hi"})
        self.assertEqual(response.status_code, 200)
        mock_prompt.assert_called_once()


class TestProofRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.build_collaboration_proof")
    def test_proof_collaboration(self, mock_proof):
        mock_proof.return_value = {"status": "ok"}
        response = self.client.post("/proof/collaboration", json={})
        self.assertEqual(response.status_code, 200)
        mock_proof.assert_called_once()


class TestRemoteRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    @patch("PIL.ImageGrab.grab")
    def test_remote_screen_success(self, mock_grab):
        mock_img = MagicMock()
        mock_img.save.side_effect = lambda fp, format: fp.write(b"png")
        mock_grab.return_value = mock_img

        response = self.client.get("/remote/screen")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"png")

    @patch("PIL.ImageGrab.grab")
    def test_remote_screen_error(self, mock_grab):
        mock_grab.side_effect = Exception("failed")
        response = self.client.get("/remote/screen")
        self.assertEqual(response.status_code, 500)

    @patch.dict("sys.modules", {"pyautogui": MagicMock()})
    def test_remote_input_mouse_click(self):
        response = self.client.post("/remote/input", json={"type": "mouse_click", "x": 10, "y": 20})
        self.assertEqual(response.status_code, 200)
        sys.modules["pyautogui"].click.assert_called_once_with(10, 20)

    @patch.dict("sys.modules", {"pyautogui": MagicMock()})
    def test_remote_input_mouse_move(self):
        response = self.client.post("/remote/input", json={"type": "mouse_move", "x": 10, "y": 20})
        self.assertEqual(response.status_code, 200)
        sys.modules["pyautogui"].moveTo.assert_called_once_with(10, 20, duration=0.1)

    @patch.dict("sys.modules", {"pyautogui": MagicMock()})
    def test_remote_input_keyboard(self):
        response = self.client.post("/remote/input", json={"type": "keyboard", "key": "A", "ctrl": True})
        self.assertEqual(response.status_code, 200)
        sys.modules["pyautogui"].keyDown.assert_called_with("ctrl")
        sys.modules["pyautogui"].press.assert_called_with("a")
        sys.modules["pyautogui"].keyUp.assert_called_with("ctrl")

    @patch.dict("sys.modules", {"pyautogui": MagicMock()})
    def test_remote_input_command(self):
        response = self.client.post("/remote/input", json={"type": "command", "command": "Alt+Tab"})
        self.assertEqual(response.status_code, 200)
        sys.modules["pyautogui"].hotkey.assert_called_with("alt", "tab")

    @patch("psutil.cpu_percent", create=True)
    @patch("psutil.virtual_memory", create=True)
    @patch("psutil.disk_usage", create=True)
    @patch("psutil.boot_time", create=True)
    def test_remote_metrics_success(self, mock_boot, mock_disk, mock_mem, mock_cpu):
        mock_cpu.return_value = 10
        mock_mem.return_value = MagicMock(used=1024**3, total=4*1024**3)
        mock_disk.return_value = MagicMock(free=100*1024**3)
        mock_boot.return_value = 0
        with patch("time.time", return_value=1000):
            response = self.client.get("/remote/metrics")
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["cpu"], 10)
            self.assertEqual(data["ram_used"], 1.0)

    @patch("psutil.cpu_percent", create=True)
    @patch("psutil.virtual_memory", create=True)
    @patch("psutil.disk_usage", create=True)
    @patch("psutil.boot_time", create=True)
    def test_remote_metrics_error(self, mock_boot, mock_disk, mock_mem, mock_cpu):
        mock_cpu.side_effect = Exception("failed")
        response = self.client.get("/remote/metrics")
        self.assertEqual(response.status_code, 500)

if __name__ == "__main__":
    unittest.main()
