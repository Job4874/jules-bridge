"""Tests for Jules task dispatch orchestration.

The dispatcher is intentionally offline by default: it parses Jules cards and
builds worker packets/launch commands without starting remote sessions.
"""

import os
import json
import sys
import tempfile
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def disable_session_cache(monkeypatch):
    monkeypatch.setenv("JULES_SESSION_CACHE_TTL_S", "0")

from modules.jules_orchestrator import (
    _resolve_cli_command,
    _run_cli_command,
    build_cot_ledger,
    build_dispatch,
    jules_preflight,
    launch_packets,
    list_remote_sessions,
    parse_antigravity_queue,
    parse_task_dump,
    pull_remote_session,
    run_jules_cycle,
    run_jules_fleet,
    run_jules_fleet_watch,
    run_jules_watch,
)


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


ANTIGRAVITY_QUEUE = """Needs review | Antigravity offload: CODEX_PHASE0_REPOSITORY_ARCHAEOLOGY_PROMPT.md | repo=C:\\aotp\\projects\\OracleV5
Needs review | Antigravity offload: CODEX_PHASE1_STABILIZATION_PROMPT.md | repo=C:\\aotp\\projects\\OracleV5
"""


def test_parse_antigravity_queue_extracts_prompt_tasks(tmp_path):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "CODEX_PHASE0_REPOSITORY_ARCHAEOLOGY_PROMPT.md").write_text(
        "# Phase 0 prompt\nDo archaeology only.",
        encoding="utf-8",
    )

    tasks = parse_antigravity_queue(
        ANTIGRAVITY_QUEUE,
        source_name="queue.txt",
        prompt_dir=str(prompt_dir),
    )

    assert len(tasks) == 2
    assert tasks[0]["task_type"] == "antigravity"
    assert tasks[0]["status"] == "needs_review"
    assert tasks[0]["repo_path"] == r"C:\aotp\projects\OracleV5"
    assert "Phase 0 prompt" in tasks[0]["raw_excerpt"]


def test_build_dispatch_antigravity_queue_writes_packets_without_clearing_on_empty(tmp_path, monkeypatch):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "CODEX_PHASE0_REPOSITORY_ARCHAEOLOGY_PROMPT.md").write_text(
        "# Phase 0 prompt\nDo archaeology only.",
        encoding="utf-8",
    )
    monkeypatch.setenv("JULES_ANTIGRAVITY_PROMPT_DIR", str(prompt_dir))
    output_dir = tmp_path / "dispatch"
    output_dir.mkdir()
    keep = output_dir / "JT-999-keep-existing-task.md"
    keep.write_text("# keep", encoding="utf-8")
    queue_path = tmp_path / "queue.txt"
    queue_path.write_text(ANTIGRAVITY_QUEUE.splitlines()[0] + "\n", encoding="utf-8")

    result = build_dispatch(
        source_path=str(queue_path),
        max_instances=1,
        write_packets=True,
        output_dir=str(output_dir),
        repo_path=r"C:\fallback\repo",
    )

    assert result["task_count"] == 1
    assert result["selected_count"] == 1
    assert len(result["packet_files"]) == 1
    assert not keep.exists()
    with open(result["packet_files"][0], encoding="utf-8") as handle:
        packet_text = handle.read()
    assert "Execute this Antigravity Codex handover prompt" in packet_text
    assert "Phase 0 prompt" in packet_text

    empty_result = build_dispatch(
        content="not a valid dump",
        write_packets=True,
        output_dir=str(output_dir),
    )
    assert empty_result["selected_count"] == 0
    assert len(list(output_dir.glob("JT-*.md"))) == 1


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
            assert "Do not stop at a plan or ask for plan approval" in content
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

        with patch("modules.jules_orchestrator._run_cli_command") as mock_run:
            result = launch_packets(packet_files=[packet], repo_path=tmp_dir, dry_run=True)

        mock_run.assert_not_called()
        assert result["dry_run"] is True
        assert result["selected_count"] == 1
        assert result["launched_count"] == 0
        assert result["results"][0]["status"] == "dry_run"
        assert result["state_path"] == os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json")
        assert os.path.isfile(result["state_path"])


def test_launch_packets_packet_dir_honors_dispatch_index_order():
    with tempfile.TemporaryDirectory() as tmp_dir:
        first = os.path.join(tmp_dir, "JT-024-failed.md")
        second = os.path.join(tmp_dir, "JT-001-ready.md")
        with open(first, "w", encoding="utf-8") as handle:
            handle.write("# Failed packet")
        with open(second, "w", encoding="utf-8") as handle:
            handle.write("# Ready packet")
        with open(os.path.join(tmp_dir, "JULES_DISPATCH_INDEX.md"), "w", encoding="utf-8") as handle:
            handle.write(
                "| id | status | type | file | issue | packet |\n"
                "|---|---|---|---|---|---|\n"
                f"| JT-024 | failed | testing | a.cs | failed issue | {first} |\n"
                f"| JT-001 | ready_for_review | testing | b.cs | ready issue | {second} |\n"
            )

        result = launch_packets(packet_dir=tmp_dir, dry_run=True, write_state=False)

        assert result["selected_count"] == 2
        assert result["results"][0]["packet"] == first
        assert result["results"][1]["packet"] == second


@patch("modules.jules_orchestrator.shutil.which", return_value=None)
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_live_posts_packet_to_jules_new(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Created session 123456789",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet\nDo useful work.")

        result = launch_packets(
            packet_files=[packet],
            repo_path=tmp_dir,
            dry_run=False,
            jules_command="jules-test",
        )

    assert result["dry_run"] is False
    assert result["launched_count"] == 1
    assert result["resolved_jules_command"] == "jules-test"
    assert result["results"][0]["exit_code"] == 0
    assert result["results"][0]["session_ids"] == ["123456789"]
    assert mock_run.call_args.args[0] == ["jules-test", "new"]
    assert mock_run.call_args.kwargs["input_text"].startswith("# Packet")
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_skips_launched_and_preserves_state(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Created session 222222",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        first = os.path.join(tmp_dir, "JT-001-first.md")
        second = os.path.join(tmp_dir, "JT-002-second.md")
        with open(first, "w", encoding="utf-8") as handle:
            handle.write("# First")
        with open(second, "w", encoding="utf-8") as handle:
            handle.write("# Second")
        state_path = os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json")
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": first,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = launch_packets(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            limit=1,
            dry_run=False,
            jules_command="jules-test",
            skip_launched=True,
        )

    assert mock_run.call_count == 1
    assert mock_run.call_args.kwargs["input_text"] == "# Second"
    assert result["attempted_count"] == 1
    assert result["skipped_launched_count"] == 1
    assert result["selected_count"] == 2
    assert result["launched_count"] == 2
    assert result["results"][0]["session_ids"] == ["111111"]
    assert result["results"][1]["session_ids"] == ["222222"]
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_can_preserve_existing_session_ids_for_duplicate_instances(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Created session 222222",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-first.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# First")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": packet,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = launch_packets(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            jules_command="jules-test",
            force_packet_files=[packet],
            preserve_existing_session_ids=True,
        )

    assert result["attempted_count"] == 1
    assert result["attempt_results"][0]["session_ids"] == ["222222"]
    assert result["results"][0]["session_ids"] == ["222222", "111111"]
    assert result["preserve_existing_session_ids"] is True
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_drops_stale_previous_state_rows(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Created session 222222",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        stale = os.path.join(tmp_dir, "JT-999-stale.md")
        current = os.path.join(tmp_dir, "JT-001-current.md")
        with open(current, "w", encoding="utf-8") as handle:
            handle.write("# Current")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": stale,
                    "status": "launched",
                    "session_ids": ["999999"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = launch_packets(
            packet_dir=tmp_dir,
            dry_run=False,
            jules_command="jules-test",
        )

    assert result["selected_count"] == 1
    assert result["results"][0]["packet"] == current
    assert result["results"][0]["session_ids"] == ["222222"]
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_treats_exit_zero_cli_error_as_failed(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "",
        "stderr": "Error: No --repo flag provided.\n",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-error.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Error")

        result = launch_packets(
            packet_dir=tmp_dir,
            dry_run=False,
            jules_command="jules-test",
        )

    assert result["attempted_count"] == 1
    assert result["launched_count"] == 0
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["session_ids"] == []
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_retries_malformed_launched_state_without_session_id(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Created session 333333",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        malformed = os.path.join(tmp_dir, "JT-001-malformed.md")
        fresh = os.path.join(tmp_dir, "JT-002-fresh.md")
        with open(malformed, "w", encoding="utf-8") as handle:
            handle.write("# Malformed")
        with open(fresh, "w", encoding="utf-8") as handle:
            handle.write("# Fresh")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": malformed,
                    "status": "launched",
                    "session_ids": [],
                    "timed_out": False,
                    "exit_code": 0,
                    "stderr": "Error: No --repo flag provided.\n",
                }]
            }, handle)

        result = launch_packets(
            packet_dir=tmp_dir,
            dry_run=False,
            jules_command="jules-test",
            skip_launched=True,
            limit=1,
        )

    assert result["attempted_count"] == 1
    assert result["skipped_launched_count"] == 0
    assert result["results"][0]["packet"] == malformed
    assert result["results"][0]["status"] == "launched"
    assert result["results"][0]["session_ids"] == ["333333"]
    assert result["results"][1]["status"] == "not_launched"
    assert mock_run.call_args.kwargs["input_text"] == "# Malformed"
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value=r"C:\tools\jules.cmd")
@patch("modules.jules_orchestrator._run_cli_command")
def test_list_remote_sessions_captures_cli_output(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "123456 running\n",
        "stderr": "",
        "timed_out": False,
    }

    result = list_remote_sessions(jules_command="jules-test", dry_run=False)

    assert result["dry_run"] is False
    assert result["exit_code"] == 0
    assert result["session_ids"] == ["123456"]
    assert result["resolved_jules_command"] == r"C:\tools\jules.cmd"
    assert mock_run.call_args.args[0] == [r"C:\tools\jules.cmd", "remote", "list", "--session"]
    mock_which.assert_any_call("jules-test")


def test_list_remote_sessions_dry_run_does_not_call_cli():
    with patch("modules.jules_orchestrator._run_cli_command") as mock_run:
        result = list_remote_sessions(dry_run=True)

    mock_run.assert_not_called()
    assert result["dry_run"] is True


def test_resolve_cli_prefers_npm_prefix_direct_exe_over_broken_shim(tmp_path, monkeypatch):
    npm_prefix = tmp_path / "npm-prefix"
    npm_bin = npm_prefix / "bin"
    npm_bin.mkdir(parents=True)
    direct_exe = npm_bin / "jules.exe"
    shim = npm_prefix / "jules.cmd"
    direct_exe.write_text("", encoding="utf-8")
    shim.write_text("@echo off\nexit /b 1\n", encoding="utf-8")
    monkeypatch.setenv("npm_config_prefix", str(npm_prefix))

    with patch("modules.jules_orchestrator.shutil.which", return_value=str(shim)):
        resolved = _resolve_cli_command("jules")

    assert resolved == str(direct_exe)


@patch.dict(os.environ, {"JULES_USE_REST_API": "1", "JULES_API_KEY": "secret"}, clear=False)
@patch("modules.jules_orchestrator.jules_api.list_sessions")
@patch("modules.jules_orchestrator._run_cli_command")
def test_list_remote_sessions_uses_rest_api_when_enabled(mock_run, mock_list):
    mock_list.return_value = {
        "status": "ok",
        "session_ids": ["123456"],
        "stdout": " 123456 # Local bridge fix In Progress\n",
    }

    result = list_remote_sessions(dry_run=False, bypass_cache=True)

    mock_run.assert_not_called()
    mock_list.assert_called_once()
    assert result["status"] == "ok"
    assert result["rest_api"] is True
    assert result["session_ids"] == ["123456"]
    assert result["resolved_jules_command"] == "JULES_REST_API"


@patch.dict(
    os.environ,
    {
        "JULES_USE_REST_API": "1",
        "JULES_API_KEY": "secret",
        "JULES_SOURCE": "sources/github/Job4874/jules-bridge",
    },
    clear=False,
)
@patch("modules.jules_orchestrator.jules_api.create_session")
@patch("modules.jules_orchestrator._run_cli_command")
def test_launch_packets_uses_rest_api_when_enabled(mock_run, mock_create):
    mock_create.return_value = {
        "status": "ok",
        "session_ids": ["314159"],
        "session": {"id": "314159"},
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-rest.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet\nDo useful work.")

        result = launch_packets(
            packet_files=[packet],
            repo_path=tmp_dir,
            dry_run=False,
        )

    mock_run.assert_not_called()
    assert result["rest_api"] is True
    assert result["launched_count"] == 1
    assert result["results"][0]["status"] == "launched"
    assert result["results"][0]["session_ids"] == ["314159"]
    assert mock_create.call_args.kwargs["prompt"].startswith("# Packet")
    assert mock_create.call_args.kwargs["title"] == "JT-001-rest"


@patch.dict(os.environ, {"JULES_USE_REST_API": "1", "JULES_API_KEY": "secret"}, clear=False)
@patch("modules.jules_orchestrator.jules_api.get_session")
@patch("modules.jules_orchestrator._run_cli_command")
def test_pull_remote_session_uses_rest_api_when_enabled(mock_run, mock_get):
    mock_get.return_value = {
        "status": "ok",
        "session_ids": ["123456"],
        "completed": True,
        "stdout": '{"outputs":[{"pullRequest":{}}]}',
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = pull_remote_session(
            "123456",
            output_dir=tmp_dir,
            dry_run=False,
        )

    mock_run.assert_not_called()
    assert result["rest_api"] is True
    assert result["status"] == "pulled"
    assert result["exit_code"] == 0
    assert "Completion report" in result["note"]


@patch("modules.jules_orchestrator._auth_indicators")
@patch("modules.jules_orchestrator._candidate_jules_commands")
@patch("modules.jules_orchestrator.shutil.which", return_value=r"C:\tools\jules.cmd")
@patch("modules.jules_orchestrator._run_cli_command")
def test_jules_preflight_reports_remote_timeout_as_auth_possible(
    mock_run,
    mock_which,
    mock_candidates,
    mock_auth,
):
    mock_candidates.return_value = [{
        "label": "npm_bin_exe",
        "requested": r"C:\tools\jules.exe",
        "resolved": r"C:\tools\jules.exe",
        "exists": True,
    }]
    mock_auth.return_value = {
        "known_auth_paths": [],
        "any_known_auth_path_exists": False,
    }
    mock_run.side_effect = [
        {"exit_code": 0, "stdout": "Version: v0.1.42", "stderr": "", "timed_out": False},
        {"exit_code": None, "stdout": "", "stderr": "", "timed_out": True},
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = jules_preflight(
            timeout_s=1,
            state_path=os.path.join(tmp_dir, "preflight.json"),
        )
        assert os.path.isfile(result["state_path"])

    assert result["ready"] is False
    assert result["preferred_jules_command"] == r"C:\tools\jules.exe"
    assert result["version"]["exit_code"] == 0
    assert result["remote"]["status"] == "timeout"
    assert result["likely_blocker"] == "remote_timeout_possible_auth_required"
    assert result["login_command"] == [r"C:\tools\jules.exe", "login", "--no-launch-browser"]
    mock_which.assert_any_call("jules")


@patch("modules.jules_orchestrator._auth_indicators", return_value={})
@patch("modules.jules_orchestrator._run_cli_command")
def test_jules_preflight_respects_explicit_command(mock_run, mock_auth):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Version: v0.1.42",
        "stderr": "",
        "timed_out": False,
    }

    result = jules_preflight(
        jules_command=r"C:\custom\jules.exe",
        check_remote=False,
        write_state=False,
    )

    assert result["preferred_jules_command"] == r"C:\custom\jules.exe"
    assert mock_run.call_args.args[0] == [r"C:\custom\jules.exe", "version"]


def test_pull_remote_session_dry_run_writes_result_without_cli():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch("modules.jules_orchestrator._run_cli_command") as mock_run:
            result = pull_remote_session(
                session_id="123456",
                output_dir=tmp_dir,
                dry_run=True,
            )

        mock_run.assert_not_called()
        assert result["status"] == "dry_run"
        assert result["session_ids"] == ["123456"]
        assert os.path.isfile(result["output_path"])


@patch("modules.jules_orchestrator.shutil.which", return_value=r"C:\tools\jules.cmd")
@patch("modules.jules_orchestrator._run_cli_command")
def test_pull_remote_session_live_uses_remote_pull(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": "Completion report\nwhat changed\nverification performed\nsession 123456",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = pull_remote_session(
            session_id="123456",
            repo_path=tmp_dir,
            output_dir=tmp_dir,
            dry_run=False,
            jules_command="jules-test",
        )

    assert result["status"] == "pulled"
    assert result["resolved_jules_command"] == r"C:\tools\jules.cmd"
    assert mock_run.call_args.args[0] == [
        r"C:\tools\jules.cmd",
        "remote",
        "pull",
        "--session",
        "123456",
    ]
    assert mock_run.call_args.kwargs["cwd"] == tmp_dir
    mock_which.assert_called_with("jules-test")


def test_run_cli_command_accepts_unicode_input_on_windows_pipes():
    result = _run_cli_command(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdin.buffer.read(); print('ok')",
        ],
        timeout_s=5,
        input_text="launch packet 🧪",
    )

    assert result["exit_code"] == 0
    assert result["stdout"].strip() == "ok"
    assert result["timed_out"] is False


def test_build_cot_ledger_marks_completion_report():
    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-024-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")
        state = {
            "results": [{
                "packet": packet,
                "status": "launched",
                "session_ids": ["123456"],
                "timed_out": False,
                "exit_code": 0,
            }]
        }
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json_text = '{"results":[{"packet":"%s","status":"launched","session_ids":["123456"],"timed_out":false,"exit_code":0}]}'
            handle.write(json_text % packet.replace("\\", "\\\\"))
        report_dir = os.path.join(tmp_dir, "reports")
        os.makedirs(report_dir)
        with open(os.path.join(report_dir, "123456.md"), "w", encoding="utf-8") as handle:
            handle.write("Completion report\nwhat changed\nverification performed\nsession 123456")

        result = build_cot_ledger(packet_dir=tmp_dir, report_dir=report_dir)

        assert state["results"][0]["packet"] == packet
        assert result["completed_count"] == 1
        assert result["all_complete"] is True
        assert result["rows"][0]["cot_status"] == "completed_reported"
        assert os.path.isfile(result["ledger_path"])


def test_build_cot_ledger_counts_successful_pulled_diff_as_evidence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-024-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": packet,
                    "status": "launched",
                    "session_ids": ["123456"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)
        report_dir = os.path.join(tmp_dir, "pulls")
        os.makedirs(report_dir)
        with open(os.path.join(report_dir, "jules_pull_123456.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "status": "pulled",
                "exit_code": 0,
                "stdout": "diff --git a/file.cs b/file.cs\n--- a/file.cs\n+++ b/file.cs\n+added evidence",
                "stderr": "",
                "session_ids": ["123456"],
            }, handle)

        result = build_cot_ledger(packet_dir=tmp_dir, report_dir=report_dir)

        assert result["completed_count"] == 1
        assert result["pending_count"] == 0
        assert result["all_complete"] is True
        assert result["rows"][0]["cot_status"] == "pulled_output_reported"


def test_build_cot_ledger_marks_dry_run_packets_not_launched():
    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")
        launch_state = {
            "results": [{
                "packet": packet,
                "status": "dry_run",
                "session_ids": [],
                "timed_out": False,
                "exit_code": None,
            }]
        }
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            handle.write(
                '{"results":[{"packet":"%s","status":"dry_run","session_ids":[],"timed_out":false,"exit_code":null}]}'
                % packet.replace("\\", "\\\\")
            )

        result = build_cot_ledger(packet_dir=tmp_dir, write_ledger=False)

        assert result["all_complete"] is False
        assert result["pending_count"] == 1
        assert result["rows"][0]["cot_status"] == "not_launched"


def test_run_jules_cycle_dispatches_and_builds_cot_ledger():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch("modules.jules_orchestrator._run_cli_command") as mock_run:
            result = run_jules_cycle(
                content=SAMPLE_DUMP,
                packet_dir=tmp_dir,
                repo_path=tmp_dir,
                max_instances=2,
                dry_run=True,
            )

        mock_run.assert_not_called()
        assert result["status"] == "pending"
        assert result["dispatch"]["selected_count"] == 2
        assert result["launch_result"]["selected_count"] == 2
        assert result["launch_dry_run"] is True
        assert result["cot"]["selected_count"] == 2
        assert result["cot"]["pending_count"] == 2
        assert os.path.isfile(result["cycle_state_path"])
        assert os.path.isfile(os.path.join(tmp_dir, "JULES_COT_LEDGER.md"))


@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_cycle_blocks_live_launch_when_remote_check_times_out(mock_run):
    mock_run.return_value = {
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "timed_out": True,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")

        result = run_jules_cycle(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            launch=True,
            dry_run=False,
            timeout_s=1,
        )

    assert result["status"] == "blocked"
    assert result["launch_dry_run"] is True
    assert result["launch_result"]["results"][0]["status"] == "dry_run"
    assert "Remote Jules session listing" in result["blockers"][0]
    assert mock_run.call_count == 1


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_cycle_pull_only_preserves_launch_state(mock_run, mock_which):
    mock_run.side_effect = [
        {
            "exit_code": 0,
            "stdout": " 123456 # Packet Job4874/OracleV5 1s ago Completed\n",
            "stderr": "",
            "timed_out": False,
        },
        {
            "exit_code": 0,
            "stdout": "Completion report\nwhat changed\nverification performed\nsession 123456",
            "stderr": "",
            "timed_out": False,
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")
        state_path = os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json")
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": packet,
                    "status": "launched",
                    "session_ids": ["123456"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_cycle(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            launch=False,
            pull=True,
            dry_run=False,
            timeout_s=1,
            jules_command="jules-test",
        )
        with open(state_path, encoding="utf-8") as handle:
            persisted_state = json.load(handle)

    assert result["status"] == "complete"
    assert result["pull_results"][0]["status"] == "pulled"
    assert result["cot"]["completed_count"] == 1
    assert persisted_state["results"][0]["status"] == "launched"
    assert mock_run.call_count == 2
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_cycle_does_not_pull_explicit_incomplete_session(mock_run):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": " 123456 # Packet Job4874/OracleV5 1s ago In Progress\n",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")

        result = run_jules_cycle(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            launch=False,
            pull=True,
            session_ids=["123456"],
            dry_run=False,
            timeout_s=1,
            jules_command="jules-test",
        )

    assert result["status"] == "pending"
    assert result["pull_results"] == []
    assert mock_run.call_count == 1


@patch("modules.jules_orchestrator.run_jules_cycle")
def test_run_jules_watch_stops_when_cot_complete(mock_cycle):
    mock_cycle.return_value = {
        "status": "complete",
        "sessions": {
            "stdout": " 123456 # Packet Job4874/OracleV5 1s ago Completed\n",
            "status": "ok",
        },
        "pull_results": [{"session_id": "123456", "status": "pulled"}],
        "cot": {
            "all_complete": True,
            "completed_count": 1,
            "pending_count": 0,
            "status_counts": {"completed_reported": 1},
        },
        "blockers": [],
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        packet = os.path.join(tmp_dir, "JT-001-abcdef-test.md")
        with open(packet, "w", encoding="utf-8") as handle:
            handle.write("# Packet")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": packet,
                    "status": "launched",
                    "session_ids": ["123456"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_watch(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            max_wait_s=0,
            poll_interval_s=1,
        )
        assert os.path.isfile(result["watch_state_path"])

    assert result["status"] == "complete"
    assert result["stop_reason"] == "cot_complete"
    assert result["iterations"][0]["pull_count"] == 1
    assert result["iterations"][0]["remote_status_counts"] == {"Completed": 1}
    assert result["latest_remote_statuses"][0]["remote_status"] == "Completed"


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_fleet_launches_only_when_capacity_available(mock_run, mock_which):
    mock_run.side_effect = [
        {
            "exit_code": 0,
            "stdout": " 111111 # First Job4874/OracleV5 1s ago In Progress\n",
            "stderr": "",
            "timed_out": False,
        },
        {
            "exit_code": 0,
            "stdout": "Created session 222222",
            "stderr": "",
            "timed_out": False,
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        first = os.path.join(tmp_dir, "JT-001-first.md")
        second = os.path.join(tmp_dir, "JT-002-second.md")
        with open(first, "w", encoding="utf-8") as handle:
            handle.write("# First")
        with open(second, "w", encoding="utf-8") as handle:
            handle.write("# Second")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": first,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_fleet(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            max_concurrent=2,
            launch_batch_size=5,
            timeout_s=1,
            jules_command="jules-test",
        )

    assert result["status"] == "scaled"
    assert result["active_remote_count"] == 1
    assert result["available_launch_capacity"] == 1
    assert result["requested_launch_limit"] == 1
    assert result["launch_dry_run"] is False
    assert result["launch_result"]["attempted_count"] == 1
    assert result["launch_result"]["attempt_results"][0]["packet"] == second
    assert result["launch_result"]["attempt_results"][0]["session_ids"] == ["222222"]
    assert result["launch_result"]["launched_count"] == 2
    assert mock_run.call_count == 2
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_fleet_respects_max_concurrent_capacity(mock_run, mock_which):
    mock_run.return_value = {
        "exit_code": 0,
        "stdout": " 111111 # First Job4874/OracleV5 1s ago In Progress\n",
        "stderr": "",
        "timed_out": False,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        first = os.path.join(tmp_dir, "JT-001-first.md")
        second = os.path.join(tmp_dir, "JT-002-second.md")
        with open(first, "w", encoding="utf-8") as handle:
            handle.write("# First")
        with open(second, "w", encoding="utf-8") as handle:
            handle.write("# Second")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": first,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_fleet(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            max_concurrent=1,
            launch_batch_size=5,
            timeout_s=1,
            jules_command="jules-test",
        )

    assert result["status"] == "pending"
    assert result["active_remote_count"] == 1
    assert result["available_launch_capacity"] == 0
    assert result["requested_launch_limit"] == 0
    assert result["launch_dry_run"] is True
    assert result["launch_result"]["attempted_count"] == 0
    assert result["launch_result"]["attempt_results"] == []
    assert result["launch_result"]["results"][1]["status"] == "not_launched"
    assert mock_run.call_count == 1
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_fleet_relaunches_failed_remote_packet_before_new_work(mock_run, mock_which):
    mock_run.side_effect = [
        {
            "exit_code": 0,
            "stdout": " 111111 # Failed packet Job4874/OracleV5 1s ago Failed\n",
            "stderr": "",
            "timed_out": False,
        },
        {
            "exit_code": 0,
            "stdout": "Created session 333333",
            "stderr": "",
            "timed_out": False,
        },
        {
            "exit_code": 0,
            "stdout": "Created session 222222",
            "stderr": "",
            "timed_out": False,
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        failed = os.path.join(tmp_dir, "JT-001-failed.md")
        fresh = os.path.join(tmp_dir, "JT-002-fresh.md")
        with open(failed, "w", encoding="utf-8") as handle:
            handle.write("# Failed")
        with open(fresh, "w", encoding="utf-8") as handle:
            handle.write("# Fresh")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": failed,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_fleet(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            max_concurrent=2,
            launch_batch_size=2,
            timeout_s=1,
            jules_command="jules-test",
        )

    assert result["status"] == "scaled"
    assert result["active_remote_count"] == 0
    assert result["failed_remote_packet_files"] == [failed]
    assert result["relaunch_failed_limit"] == 1
    assert result["launch_result"]["attempted_count"] == 2
    assert result["launch_result"]["attempt_results"][0]["packet"] == failed
    assert result["launch_result"]["attempt_results"][0]["session_ids"] == ["333333"]
    assert result["launch_result"]["attempt_results"][1]["packet"] == fresh
    assert result["launch_result"]["attempt_results"][1]["session_ids"] == ["222222"]
    assert result["launch_result"]["results"][0]["session_ids"] == ["333333"]
    assert result["launch_result"]["results"][1]["session_ids"] == ["222222"]
    assert mock_run.call_count == 3
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_fleet_relaunches_stale_unknown_remote_packet(mock_run, mock_which):
    mock_run.side_effect = [
        {
            "exit_code": 0,
            "stdout": " 111111 # Blank packet Job4874/OracleV5 21m4s ago                 \n",
            "stderr": "",
            "timed_out": False,
        },
        {
            "exit_code": 0,
            "stdout": "Created session 333333",
            "stderr": "",
            "timed_out": False,
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        stale = os.path.join(tmp_dir, "JT-001-stale.md")
        fresh = os.path.join(tmp_dir, "JT-002-fresh.md")
        with open(stale, "w", encoding="utf-8") as handle:
            handle.write("# Stale")
        with open(fresh, "w", encoding="utf-8") as handle:
            handle.write("# Fresh")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": stale,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_fleet(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            max_concurrent=1,
            launch_batch_size=1,
            timeout_s=1,
            jules_command="jules-test",
        )

    assert result["status"] == "scaled"
    assert result["active_remote_count"] == 0
    assert result["failed_remote_packet_files"] == []
    assert result["stale_unknown_remote_packet_files"] == [stale]
    assert result["retry_remote_packet_files"] == [stale]
    assert result["relaunch_failed_limit"] == 1
    assert result["remote_statuses"][0]["last_active_s"] == 1264
    assert result["remote_statuses"][0]["stale_unknown"] is True
    assert result["launch_result"]["attempted_count"] == 1
    assert result["launch_result"]["attempt_results"][0]["packet"] == stale
    assert result["launch_result"]["attempt_results"][0]["session_ids"] == ["333333"]
    assert result["launch_result"]["results"][0]["session_ids"] == ["333333"]
    assert result["launch_result"]["results"][1]["status"] == "not_launched"
    assert mock_run.call_count == 2
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.shutil.which", return_value="jules-test")
@patch("modules.jules_orchestrator._run_cli_command")
def test_run_jules_fleet_relaunches_awaiting_plan_remote_packet(mock_run, mock_which):
    mock_run.side_effect = [
        {
            "exit_code": 0,
            "stdout": " 111111 # Plan packet Job4874/OracleV5 2m ago Awaiting Plan A\n",
            "stderr": "",
            "timed_out": False,
        },
        {
            "exit_code": 0,
            "stdout": "Created session 333333",
            "stderr": "",
            "timed_out": False,
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        awaiting = os.path.join(tmp_dir, "JT-001-awaiting.md")
        fresh = os.path.join(tmp_dir, "JT-002-fresh.md")
        with open(awaiting, "w", encoding="utf-8") as handle:
            handle.write("# Awaiting")
        with open(fresh, "w", encoding="utf-8") as handle:
            handle.write("# Fresh")
        with open(os.path.join(tmp_dir, "JULES_LAUNCH_STATE.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "results": [{
                    "packet": awaiting,
                    "status": "launched",
                    "session_ids": ["111111"],
                    "timed_out": False,
                    "exit_code": 0,
                }]
            }, handle)

        result = run_jules_fleet(
            packet_dir=tmp_dir,
            repo_path=tmp_dir,
            dry_run=False,
            max_concurrent=1,
            launch_batch_size=1,
            timeout_s=1,
            jules_command="jules-test",
        )

    assert result["status"] == "scaled"
    assert result["active_remote_count"] == 0
    assert result["plan_awaiting_remote_packet_files"] == [awaiting]
    assert result["retry_remote_packet_files"] == [awaiting]
    assert result["relaunch_failed_limit"] == 1
    assert result["launch_result"]["attempted_count"] == 1
    assert result["launch_result"]["attempt_results"][0]["packet"] == awaiting
    assert result["launch_result"]["attempt_results"][0]["session_ids"] == ["333333"]
    assert result["launch_result"]["results"][0]["session_ids"] == ["333333"]
    assert result["launch_result"]["results"][1]["status"] == "not_launched"
    assert mock_run.call_count == 2
    mock_which.assert_any_call("jules-test")


@patch("modules.jules_orchestrator.run_jules_fleet")
def test_run_jules_fleet_watch_loops_until_cot_complete(mock_fleet):
    mock_fleet.side_effect = [
        {
            "status": "scaled",
            "blockers": [],
            "pull_results": [],
            "launch_result": {
                "attempt_results": [{
                    "status": "launched",
                    "session_ids": ["222222"],
                }]
            },
            "active_remote_count": 1,
            "available_launch_capacity": 1,
            "requested_launch_limit": 1,
            "remote_status_counts": {"In Progress": 1},
            "remote_statuses": [{"session_id": "111111", "remote_status": "In Progress"}],
            "cot": {
                "all_complete": False,
                "completed_count": 0,
                "pending_count": 1,
                "status_counts": {"launched_pending_cot": 1},
            },
        },
        {
            "status": "complete",
            "blockers": [],
            "pull_results": [{"session_id": "222222", "status": "pulled"}],
            "launch_result": {"attempt_results": []},
            "active_remote_count": 0,
            "available_launch_capacity": 2,
            "requested_launch_limit": 0,
            "remote_status_counts": {"Completed": 1},
            "remote_statuses": [{"session_id": "222222", "remote_status": "Completed"}],
            "cot": {
                "all_complete": True,
                "completed_count": 1,
                "pending_count": 0,
                "status_counts": {"pulled_output_reported": 1},
            },
        },
    ]

    result = run_jules_fleet_watch(
        source_path=r"C:\tmp\queue.txt",
        packet_dir=r"C:\tmp\dispatch",
        repo_path=r"C:\repo",
        dry_run=False,
        max_wait_s=2,
        poll_interval_s=1,
        write_state=False,
    )

    assert result["status"] == "complete"
    assert result["stop_reason"] == "cot_complete"
    assert len(result["iterations"]) == 2
    assert result["iterations"][0]["launched_sessions"] == ["222222"]
    assert result["iterations"][1]["pulled_sessions"] == ["222222"]
    assert mock_fleet.call_args_list[0].kwargs["source_path"] == r"C:\tmp\queue.txt"
    assert mock_fleet.call_args_list[1].kwargs["source_path"] == ""


@patch("modules.jules_orchestrator.run_jules_fleet")
def test_run_jules_fleet_watch_dry_run_stops_after_one_iteration(mock_fleet):
    mock_fleet.return_value = {
        "status": "pending",
        "blockers": [],
        "pull_results": [],
        "launch_result": {"attempt_results": []},
        "active_remote_count": 0,
        "available_launch_capacity": 2,
        "requested_launch_limit": 2,
        "remote_status_counts": {},
        "remote_statuses": [],
        "cot": {
            "all_complete": False,
            "completed_count": 0,
            "pending_count": 2,
            "status_counts": {"not_launched": 2},
        },
    }

    result = run_jules_fleet_watch(dry_run=True, write_state=False)

    assert result["status"] == "dry_run"
    assert result["stop_reason"] == "dry_run"
    assert len(result["iterations"]) == 1
    mock_fleet.assert_called_once()
