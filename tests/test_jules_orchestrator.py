"""Tests for Jules task dispatch orchestration.

The dispatcher is intentionally offline by default: it parses Jules cards and
builds worker packets/launch commands without starting remote sessions.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from modules.jules_orchestrator import build_dispatch, launch_packets, list_remote_sessions, parse_task_dump


SAMPLE_DUMP = """Needs review
Testing Improvement Task
You are a testing-focused agent.

Task Details
File: OracleV5.Strategy/Health/HeartbeatMonitor.cs:78 Issue: Add test for HeartbeatMonitor.IsAlive

Language: csharp

Rationale: Easy to assert state changes.

Jules is waiting for you to review...
Ready for review

Performance Optimization Task
Task Details
File: OracleV5.Strategy/Observability/CsvTelemetryService.cs:444 Issue: Serial execution of asynchronous file I/O
Language: csharp
Rationale: Refactor await loop to Task.WhenAll.

Failed

Testing Improvement Task
Task Details
File: OracleV5.Strategy/Regime/VIXMonitor.cs:68 Issue: Add test for VIXMonitor.Reset
Language: csharp
Rationale: Straightforward state reset test.

Complete
"""


def test_parse_task_dump_extracts_cards_and_statuses():
    tasks = parse_task_dump(SAMPLE_DUMP)

    assert len(tasks) == 3
    assert tasks[0]["task_type"] == "testing"
    assert tasks[0]["status"] == "ready_for_review"
    assert tasks[0]["file"] == "OracleV5.Strategy/Health/HeartbeatMonitor.cs:78"
    assert tasks[0]["issue"] == "Add test for HeartbeatMonitor.IsAlive"
    assert tasks[1]["task_type"] == "performance"
    assert tasks[1]["status"] == "failed"
    assert tasks[2]["status"] == "complete"


def test_build_dispatch_selects_open_tasks_and_writes_packets():
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = build_dispatch(
            content=SAMPLE_DUMP,
            max_instances=2,
            write_packets=True,
            output_dir=tmp_dir,
            repo_path=r"C:\aotp\projects\OracleV5",
        )

        assert result["task_count"] == 3
        assert result["selected_count"] == 2
        assert result["status_counts"]["failed"] == 1
        assert result["status_counts"]["complete"] == 1
        assert len(result["packet_files"]) == 2
        assert len(result["launch_commands"]) == 2

        for packet in result["packet_files"]:
            assert os.path.isfile(packet)
            with open(packet, encoding="utf-8") as handle:
                content = handle.read()
            assert "Do not reveal private chain-of-thought" in content
            assert "Completion report" in content

        assert os.path.isfile(os.path.join(tmp_dir, "JULES_DISPATCH_INDEX.md"))
        assert os.path.isfile(os.path.join(tmp_dir, "jules_launch_commands.ps1"))


def test_build_dispatch_dry_run_does_not_write_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = build_dispatch(
            content=SAMPLE_DUMP,
            max_instances=5,
            write_packets=False,
            output_dir=tmp_dir,
        )

        assert result["selected_count"] == 2
        assert result["packet_files"] == []
        assert os.listdir(tmp_dir) == []


def test_build_dispatch_reads_source_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        source = os.path.join(tmp_dir, "dump.txt")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(SAMPLE_DUMP)

        result = build_dispatch(source_path=source, max_instances=1)

        assert result["source"] == source
        assert result["selected_count"] == 1
        assert result["selected_tasks"][0]["status"] == "failed"


def test_build_dispatch_reports_missing_input_without_raising():
    result = build_dispatch()

    assert result["error"] == "content or source_path is required"
    assert result["task_count"] == 0


def test_build_dispatch_dedupes_same_task_and_prefers_failed_status():
    duplicate_dump = SAMPLE_DUMP + """
Testing Improvement Task
Task Details
File: OracleV5.Strategy/Health/HeartbeatMonitor.cs:78 Issue: Add test for HeartbeatMonitor.IsAlive
Language: csharp
Rationale: Easy to assert state changes.

Failed
"""

    result = build_dispatch(content=duplicate_dump, max_instances=5)
    selected_ids = [task["fingerprint"] for task in result["selected_tasks"]]
    alive_tasks = [
        task for task in result["selected_tasks"]
        if task["issue"] == "Add test for HeartbeatMonitor.IsAlive"
    ]

    assert len(selected_ids) == len(set(selected_ids))
    assert len(alive_tasks) == 1
    assert alive_tasks[0]["status"] == "failed"


def test_launch_packets_dry_run_uses_packet_files_without_subprocess():
    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet\nDo useful work.")

        with patch("modules.jules_orchestrator.subprocess.run") as mock_run:
            result = launch_packets(packet_files=[packet], repo_path=tmp_dir, dry_run=True)

        mock_run.assert_not_called()
        assert result["dry_run"] is True
        assert result["selected_count"] == 1
        assert result["launched_count"] == 0
        assert result["results"][0]["status"] == "dry_run"


@patch("modules.jules_orchestrator.subprocess.run")
def test_launch_packets_live_posts_packet_to_jules_new(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Created session 123456789",
        stderr="",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet\nDo useful work.")

        result = launch_packets(packet_files=[packet], repo_path=tmp_dir, dry_run=False)

    assert result["dry_run"] is False
    assert result["launched_count"] == 1
    assert result["results"][0]["exit_code"] == 0
    assert result["results"][0]["session_ids"] == ["123456789"]
    assert mock_run.call_args.args[0] == ["jules", "new"]
    assert mock_run.call_args.kwargs["input"].startswith("# Packet")


@patch("modules.jules_orchestrator.subprocess.run")
def test_list_remote_sessions_captures_cli_output(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="123456 running\n", stderr="")

    result = list_remote_sessions(dry_run=False)

    assert result["dry_run"] is False
    assert result["exit_code"] == 0
    assert result["session_ids"] == ["123456"]
    assert mock_run.call_args.args[0] == ["jules", "remote", "list", "--session"]


def test_list_remote_sessions_dry_run_does_not_call_cli():
    with patch("modules.jules_orchestrator.subprocess.run") as mock_run:
        result = list_remote_sessions(dry_run=True)

    mock_run.assert_not_called()
    assert result["dry_run"] is True
