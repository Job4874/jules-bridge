import os
import time
from unittest.mock import patch, MagicMock

import pytest

import main_loop
from main_loop import (
    daemon_loop_iteration,
    read_inbox,
    write_heartbeat,
    _HEARTBEAT_PATH,
)


class TestReadInbox:
    @patch.dict(os.environ, {"JULES_BRIDGE_URL": "http://localhost:9999"})
    @patch("main_loop._try_import_requests")
    def test_read_inbox_returns_task_when_content_present(self, mock_requests_import):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "Scale the VM now"}
        mock_response.raise_for_status.return_value = None
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        mock_requests_import.return_value = mock_requests

        task = read_inbox()
        assert task is not None
        assert task["type"] == "Compute/Scale"
        assert "Scale the VM now" in task["content"]

    @patch("main_loop._try_import_requests")
    def test_read_inbox_returns_none_when_empty(self, mock_requests_import):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": ""}
        mock_response.raise_for_status.return_value = None
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        mock_requests_import.return_value = mock_requests

        assert read_inbox() is None

    @patch("main_loop._try_import_requests")
    def test_read_inbox_returns_none_on_request_error(self, mock_requests_import):
        mock_requests = MagicMock()
        mock_requests.post.side_effect = Exception("connection refused")
        mock_requests_import.return_value = mock_requests

        assert read_inbox() is None

    @patch("main_loop._try_import_requests")
    def test_read_inbox_returns_none_when_requests_missing(self, mock_requests_import):
        mock_requests_import.return_value = None
        assert read_inbox() is None


class TestWriteHeartbeat:
    def teardown_method(self):
        if os.path.isfile(_HEARTBEAT_PATH):
            os.remove(_HEARTBEAT_PATH)

    def test_writes_first_heartbeat(self):
        status = write_heartbeat(force=True)
        assert status == "written"
        with open(_HEARTBEAT_PATH, encoding="utf-8") as fh:
            content = fh.read()
        assert "daemon alive" in content

    def test_skips_when_recent(self):
        write_heartbeat(force=True)
        status = write_heartbeat()
        assert status == "skipped"

    def test_writes_after_interval_elapsed(self):
        write_heartbeat(force=True)
        # Backdate the heartbeat file mtime to force a re-write.
        old_time = time.time() - 120
        os.utime(_HEARTBEAT_PATH, (old_time, old_time))
        status = write_heartbeat()
        assert status == "written"


class TestDaemonLoopIteration:
    @patch("main_loop.write_heartbeat")
    @patch("main_loop.boot_secondary_vm")
    @patch("main_loop.read_inbox")
    @patch("main_loop.dispatch")
    def test_no_pressure_no_task(
        self, mock_dispatch, mock_read_inbox, mock_boot, mock_heartbeat
    ):
        mock_boot.return_value = {
            "status": "no_action",
            "memory_percent": 50.0,
            "message": "Memory at 50.0%, no action needed.",
        }
        mock_read_inbox.return_value = None
        mock_heartbeat.return_value = "written"

        result = daemon_loop_iteration()
        assert result["vm_action"] == "no_action"
        assert result["inbox_status"] == "error_or_empty"
        assert result["routed"] is None
        mock_dispatch.assert_not_called()

    @patch("main_loop.write_heartbeat")
    @patch("main_loop.boot_secondary_vm")
    @patch("main_loop.read_inbox")
    @patch("main_loop.dispatch")
    def test_high_pressure_and_task(
        self, mock_dispatch, mock_read_inbox, mock_boot, mock_heartbeat
    ):
        mock_boot.return_value = {
            "status": "dry_run",
            "memory_percent": 90.0,
            "command": ["az", "vm", "start", "--name", "OracleV5"],
        }
        mock_read_inbox.return_value = {"type": "Code/Dev"}
        mock_dispatch.return_value = {"target": "Cursor/Jules", "task_type": "Code/Dev"}
        mock_heartbeat.return_value = "written"

        result = daemon_loop_iteration()
        assert result["vm_action"] == "dry_run"
        assert result["inbox_status"] == "task_found"
        assert result["routed"]["target"] == "Cursor/Jules"
        mock_dispatch.assert_called_once_with({"type": "Code/Dev"})

    @patch("main_loop.write_heartbeat")
    @patch("main_loop.boot_secondary_vm")
    def test_blocks_vm_boot_when_not_allowed(self, mock_boot, mock_heartbeat):
        mock_boot.side_effect = main_loop.VMBootError("allow_vm_boot=False")
        mock_heartbeat.return_value = "written"

        result = daemon_loop_iteration()
        assert result["vm_action"] == "blocked"
