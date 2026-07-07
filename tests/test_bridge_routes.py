import os
os.environ["BRIDGE_TOKEN"] = "JULES-SECURE-999"
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

    @patch("modules.inbox_append")
    def test_inbox_append_delegates_to_module(self, mock_append):
        mock_append.return_value = {"status": "success", "file": "vm_results.jsonl", "mode": "append"}

        response = self.client.post(
            "/inbox/append",
            json={"file": "vm_results.jsonl", "content": "{\"status\":\"done\"}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "append")
        mock_append.assert_called_once_with(content="{\"status\":\"done\"}", file="vm_results.jsonl")


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

    @patch("modules.analyze_codebase")
    def test_codebase_analyze_route_is_thin(self, mock_analyze):
        mock_analyze.return_value = {
            "ok": True,
            "status": "ready",
            "summary": {"file_count": 10},
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            response = self.client.post(
                "/codebase/analyze",
                json={"path": tmp_dir, "max_files": 120, "include_files": True},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["summary"]["file_count"], 10)
        mock_analyze.assert_called_once_with(
            root_path=tmp_dir,
            max_files=120,
            include_files=True,
        )

    def test_codebase_analyze_rejects_missing_root(self):
        response = self.client.post("/codebase/analyze", json={"path": r"C:\definitely\missing-repo"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Resource not found")


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


class TestSyncStatusRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.get_cloud_sync_status")
    def test_sync_status_delegates_to_module(self, mock_sync):
        mock_sync.return_value = {
            "status": "blocked",
            "state": "blocked",
            "blockers": ["dirty_worktree"],
        }

        response = self.client.get("/sync/status?root=C:/repos/jules-bridge&timeout_s=6&use_cache=false")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["state"], "blocked")
        mock_sync.assert_called_once_with(
            root="C:/repos/jules-bridge",
            timeout_s=6,
            use_cache=False,
        )

    def test_sync_status_rejects_bad_query(self):
        response = self.client.get("/sync/status?timeout_s=slow")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.build_cloud_publish_packet")
    def test_sync_publish_preview_is_authenticated_read_only(self, mock_packet):
        mock_packet.return_value = {
            "status": "blocked",
            "state": "blocked",
            "blockers": ["dirty_worktree"],
            "artifacts": {"packet_written": False, "packet_path": ""},
            "packet": "# Cloud Publish Packet\n",
        }

        response = self.client.get(
            "/sync/publish-preview?objective=Preview%20dashboard%20work"
            "&timeout_s=9&use_cache=false&write_packet=true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["state"], "blocked")
        self.assertFalse(response.get_json()["artifacts"]["packet_written"])
        mock_packet.assert_called_once_with(
            root="",
            objective="Preview dashboard work",
            timeout_s=9,
            use_cache=False,
            write_packet=False,
            output_dir="",
        )

    @patch("modules.build_cloud_publish_packet")
    def test_sync_publish_preview_requires_auth(self, mock_packet):
        raw_client = bridge.app.test_client()

        response = raw_client.get("/sync/publish-preview")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Unauthorized")
        mock_packet.assert_not_called()

    @patch("modules.build_cloud_publish_packet")
    def test_sync_publish_preview_rejects_root(self, mock_packet):
        response = self.client.get("/sync/publish-preview?root=C:/repos/private")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")
        self.assertIn("authenticated publish-packet", response.get_json()["details"])
        mock_packet.assert_not_called()

    @patch("modules.build_cloud_publish_packet")
    def test_sync_publish_packet_delegates_to_module(self, mock_packet):
        mock_packet.return_value = {
            "status": "blocked",
            "state": "blocked",
            "blockers": ["dirty_worktree"],
            "packet": "# Cloud Publish Packet\n",
        }

        response = self.client.post(
            "/sync/publish-packet",
            json={
                "root": "C:/repos/jules-bridge",
                "objective": "Publish dashboard work",
                "timeout_s": 9,
                "use_cache": False,
                "write_packet": True,
                "output_dir": "jules_inbox/cloud_sync",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["state"], "blocked")
        mock_packet.assert_called_once_with(
            root="C:/repos/jules-bridge",
            objective="Publish dashboard work",
            timeout_s=9,
            use_cache=False,
            write_packet=True,
            output_dir="jules_inbox/cloud_sync",
        )

    def test_sync_publish_packet_rejects_bad_timeout(self):
        response = self.client.post("/sync/publish-packet", json={"timeout_s": "slow"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestTIUWorkbenchRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.build_tiu_workbench_plan")
    def test_tiu_workbench_delegates_to_module(self, mock_tiu):
        mock_tiu.return_value = {
            "status": "blocked",
            "plan_state": "publish_blocked",
            "blockers": ["cloud_sync:dirty_worktree"],
        }

        response = self.client.post(
            "/tiu/workbench",
            json={
                "objective": "Improve the dashboard TIU",
                "scope": "dashboard",
                "model_lane": "alliance",
                "mode": "design_review",
                "target_files": ["dashboard-ui/src/App.jsx"],
                "require_cloud_sync": True,
                "include_live_checks": False,
                "write_packet": True,
                "timeout_s": 7,
                "output_dir": "jules_inbox/tiu_workbench",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["plan_state"], "publish_blocked")
        mock_tiu.assert_called_once_with(
            objective="Improve the dashboard TIU",
            scope="dashboard",
            model_lane="alliance",
            mode="design_review",
            target_files=["dashboard-ui/src/App.jsx"],
            require_cloud_sync=True,
            include_live_checks=False,
            write_packet=True,
            timeout_s=7,
            output_dir="jules_inbox/tiu_workbench",
        )

    def test_tiu_workbench_requires_objective(self):
        response = self.client.post("/tiu/workbench", json={"scope": "dashboard"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    def test_tiu_workbench_allows_cors_preflight_without_token(self):
        raw_client = bridge.app.test_client()

        response = raw_client.open(
            "/tiu/workbench",
            method="OPTIONS",
            headers={
                "Origin": "http://127.0.0.1:6001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:6001")
        self.assertIn("POST", response.headers.get("Allow", ""))


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


class TestGeminiRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.gemini_preflight")
    def test_gemini_preflight_delegates_to_module(self, mock_preflight):
        mock_preflight.return_value = {"ready": True, "installed": True, "version": {"stdout": "0.49.0\n"}}

        response = self.client.post(
            "/gemini/preflight",
            json={
                "gemini_command": "gemini",
                "timeout_s": 4,
                "run_smoke": True,
                "smoke_prompt": "ready?",
                "model": "gemini-3-pro",
                "cwd": r"C:\repo",
                "write_state": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ready"])
        mock_preflight.assert_called_once_with(
            gemini_command="gemini",
            timeout_s=4,
            run_smoke=True,
            smoke_prompt="ready?",
            model="gemini-3-pro",
            cwd=r"C:\repo",
            write_state=False,
            state_path="",
        )

    @patch("modules.run_gemini_prompt")
    def test_gemini_prompt_defaults_to_dry_run_plan_mode(self, mock_prompt):
        mock_prompt.return_value = {"status": "dry_run", "dry_run": True}

        response = self.client.post(
            "/gemini/prompt",
            json={"prompt": "Inspect the repo"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "dry_run")
        mock_prompt.assert_called_once_with(
            prompt="Inspect the repo",
            cwd="",
            model="",
            approval_mode="plan",
            output_format="text",
            timeout_s=120,
            gemini_command="gemini",
            dry_run=True,
            trust_workspace=True,
            write_state=True,
            state_path="",
        )

    def test_gemini_prompt_rejects_missing_prompt(self):
        response = self.client.post("/gemini/prompt", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.antigravity_preflight")
    def test_antigravity_preflight_delegates_to_module(self, mock_preflight):
        mock_preflight.return_value = {"ready": True, "installed": True, "version": {"stdout": "1.0.16\n"}}

        response = self.client.post(
            "/gemini/antigravity/preflight",
            json={
                "agy_command": "agy",
                "timeout_s": 4,
                "run_smoke": True,
                "smoke_prompt": "ready?",
                "model": "Gemini 3.5 Flash (High)",
                "cwd": r"C:\repo",
                "write_state": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ready"])
        mock_preflight.assert_called_once_with(
            agy_command="agy",
            timeout_s=4,
            run_smoke=True,
            smoke_prompt="ready?",
            model="Gemini 3.5 Flash (High)",
            cwd=r"C:\repo",
            write_state=False,
            state_path="",
        )

    @patch("modules.run_antigravity_prompt")
    def test_antigravity_prompt_defaults_to_dry_run(self, mock_prompt):
        mock_prompt.return_value = {"status": "dry_run", "dry_run": True}

        response = self.client.post(
            "/gemini/antigravity/prompt",
            json={"prompt": "Inspect the repo"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "dry_run")
        mock_prompt.assert_called_once_with(
            prompt="Inspect the repo",
            cwd="",
            model="",
            timeout_s=120,
            agy_command="agy",
            dry_run=True,
            write_state=True,
            state_path="",
        )

    def test_antigravity_prompt_rejects_missing_prompt(self):
        response = self.client.post("/gemini/antigravity/prompt", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestCollaborationProofRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.build_collaboration_proof")
    def test_collaboration_proof_delegates_to_module(self, mock_proof):
        mock_proof.return_value = {"status": "partial", "gates": []}

        response = self.client.post(
            "/proof/collaboration",
            json={
                "include_live_checks": True,
                "run_gemini_smoke": True,
                "timeout_s": 15,
                "write_state": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "partial")
        mock_proof.assert_called_once_with(
            include_live_checks=True,
            run_gemini_smoke=True,
            timeout_s=15,
            write_state=False,
            state_path="",
        )

    def test_collaboration_proof_validates_boolean_fields(self):
        response = self.client.post(
            "/proof/collaboration",
            json={"run_gemini_smoke": "yes"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestAllianceSwitchboardRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    @patch("modules.build_alliance_switchboard")
    def test_alliance_switchboard_delegates_to_module(self, mock_switchboard):
        mock_switchboard.return_value = {"status": "ready", "roles": {}}

        response = self.client.post(
            "/alliance/switchboard",
            json={
                "objective": "Create the real thing with Jules and Google CLI",
                "target_files": ["bridge.py", "modules/alliance_switchboard.py"],
                "complexity": "complex",
                "preferred_creator": "jules",
                "preferred_implementer": "antigravity_cli",
                "include_live_checks": True,
                "run_implementer_smoke": True,
                "write_packets": True,
                "state_path": r"C:\tmp\alliance",
                "timeout_s": 20,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")
        mock_switchboard.assert_called_once_with(
            objective="Create the real thing with Jules and Google CLI",
            target_files=["bridge.py", "modules/alliance_switchboard.py"],
            complexity="complex",
            preferred_creator="jules",
            preferred_implementer="antigravity_cli",
            include_live_checks=True,
            run_implementer_smoke=True,
            write_packets=True,
            state_path=r"C:\tmp\alliance",
            timeout_s=20,
        )

    def test_alliance_switchboard_requires_objective(self):
        response = self.client.post("/alliance/switchboard", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    def test_alliance_switchboard_validates_target_files(self):
        response = self.client.post(
            "/alliance/switchboard",
            json={"objective": "x", "target_files": "bridge.py"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")


class TestDashboardRoutes(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = bridge.app.test_client()

    @patch("modules.dashboard_module.get_dashboard_status")
    def test_dashboard_status_json_delegates_to_module(self, mock_status):
        mock_status.return_value = {
            "ok": True,
            "contract": {"name": "jules_dashboard_status", "version": 2, "transport": "poll"},
        }

        response = self.client.get("/dashboard/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["contract"]["transport"], "poll")
        mock_status.assert_called_once_with(bridge_start_utc=bridge._BRIDGE_START_UTC)

    @patch("modules.dashboard_module.dashboard_status_event_stream")
    def test_dashboard_status_stream_delegates_to_module(self, mock_stream):
        mock_stream.return_value = iter([
            "retry: 3000\n\n",
            'id: 1\nevent: dashboard-status\ndata: {"ok":true}\n\n',
        ])

        response = self.client.get("/dashboard/status?stream=1&events=1&interval_s=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/event-stream")
        body = response.get_data(as_text=True)
        self.assertIn("event: dashboard-status", body)
        mock_stream.assert_called_once_with(
            bridge_start_utc=bridge._BRIDGE_START_UTC,
            interval_s=1,
            max_events=1,
        )

    def test_dashboard_status_stream_rejects_bad_interval(self):
        response = self.client.get("/dashboard/status?stream=1&interval_s=fast")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid input")

    @patch("modules.dashboard_commands.admit_command")
    def test_dashboard_commands_post_delegates_to_module(self, mock_admit):
        mock_admit.return_value = {
            "ok": True,
            "command": {"commandId": "cmd-1", "status": "admitted", "type": "button_sweep"},
            "workflow": {"workflowId": "wf-1", "status": "running"},
        }

        response = self.client.post(
            "/dashboard/commands",
            json={"type": "button_sweep", "summary": "sweep"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["command"]["commandId"], "cmd-1")
        mock_admit.assert_called_once()

    @patch("modules.dashboard_commands.get_dashboard_projection")
    def test_dashboard_projection_delegates_to_module(self, mock_projection):
        mock_projection.return_value = {
            "ok": True,
            "contract": {"name": "jules_dashboard_projection", "version": 1},
            "commands": [],
            "workflows": [],
        }

        response = self.client.get("/dashboard/projection?limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["contract"]["name"], "jules_dashboard_projection")
        mock_projection.assert_called_once()

    @patch("modules.dashboard_commands.get_command")
    def test_dashboard_command_get_delegates_to_module(self, mock_get):
        mock_get.return_value = {
            "ok": True,
            "command": {"commandId": "cmd-abc", "status": "succeeded", "type": "break_test"},
        }

        response = self.client.get("/dashboard/commands/cmd-abc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["command"]["commandId"], "cmd-abc")
        mock_get.assert_called_once_with("cmd-abc")

    @patch("modules.dashboard_commands.get_command")
    def test_dashboard_command_get_not_found(self, mock_get):
        mock_get.return_value = {"ok": False, "error": "command_not_found", "commandId": "cmd-missing"}

        response = self.client.get("/dashboard/commands/cmd-missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "command_not_found")

    @patch("modules.dashboard_command_worker.tick_command_worker")
    def test_dashboard_worker_tick_delegates_to_module(self, mock_tick):
        mock_tick.return_value = {
            "ok": True,
            "processed": 1,
            "skipped": 0,
            "succeeded": 1,
            "failed": 0,
            "blocked": 0,
            "not_implemented": 0,
            "lastTickAt": "2026-07-07T00:00:00+00:00",
            "lastCommandId": "cmd-1",
        }

        response = self.client.post("/dashboard/worker/tick?limit=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["processed"], 1)
        mock_tick.assert_called_once()

    @patch("modules.dashboard_command_worker.worker_status")
    def test_dashboard_worker_status_delegates_to_module(self, mock_status):
        mock_status.return_value = {
            "ok": True,
            "workerId": "dashboard-worker-abc",
            "enabled": False,
            "mode": "manual_tick",
            "pendingCount": 2,
            "runningCount": 0,
            "terminalCount": 1,
            "lastTickAt": None,
            "lastCommandId": None,
            "running": False,
            "poll_interval_s": 1.0,
        }

        response = self.client.get("/dashboard/worker/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "manual_tick")
        mock_status.assert_called_once_with()


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


class TestReasoningSolveRoute(unittest.TestCase):
    def setUp(self):
        bridge.app.testing = True
        self.client = authed_client(bridge.app.test_client())

    def test_reasoning_solve_mcq_returns_parsed_answer(self):
        problem = (
            "You are answering a multiple-choice quiz question.\n"
            "Return ONLY valid JSON matching: "
            '{"index": int, "selected_text": string, "confidence": float, "reason": string}\n\n'
            "Question:\nPick one\n\nOptions:\n0. Alpha\n1. Beta"
        )
        response = self.client.post(
            "/reasoning/solve",
            json={"problem": problem, "halt_budget": 8, "model": "stub"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("parsed_answer", payload)
        self.assertEqual(payload["parsed_answer"]["selected_text"], "Alpha")
        self.assertNotIn("Executed action for step", str(payload.get("answer") or ""))

    @patch("modules.reasoning_module._model_loop_chat")
    def test_reasoning_solve_mcq_retry_returns_parsed_answer(self, mock_model_loop):
        problem = (
            "You are answering a multiple-choice quiz question.\n"
            "Return ONLY valid JSON matching: "
            '{"index": int, "selected_text": string, "confidence": float, "reason": string}\n\n'
            "Question:\nPick one\n\nOptions:\n0. Alpha\n1. Beta"
        )
        mock_model_loop.side_effect = [
            "Executed action for step 1",
            json.dumps(
                {
                    "index": 1,
                    "selected_text": "Beta",
                    "confidence": 0.93,
                    "reason": "Best option.",
                }
            ),
        ]
        response = self.client.post(
            "/reasoning/solve",
            json={"problem": problem, "halt_budget": 8, "model": "smart"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["parsed_answer"]["selected_text"], "Beta")
        self.assertEqual(mock_model_loop.call_count, 2)


if __name__ == "__main__":
    unittest.main()
