import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timezone
import json
import socket
import time
import modules.dashboard_module
from pathlib import Path

from modules.dashboard_module import (
    dashboard_status_event_stream,
    get_dashboard_status,
    _dashboard_status_cache,
    _env_vars,
    _tcp_reachable,
    _tail_log,
    _read_json,
    _fleet_status,
    _vm_info,
    _runtime_context,
    _safe_log_lines,
    _cli_status_summary,
    _codebase_analysis_summary,
    _alliance_status_summary,
    _cloud_sync_status_summary,
)

@pytest.fixture(autouse=True)
def clear_cache():
    _dashboard_status_cache.clear()
    yield
    _dashboard_status_cache.clear()

def test_get_dashboard_status_happy_path():
    # Mocking dependencies
    with patch('modules.dashboard_module._env_vars') as mock_env_vars, \
         patch('modules.dashboard_module.detect_resource_pressure') as mock_pressure, \
         patch('modules.dashboard_module._fleet_status') as mock_fleet, \
         patch('modules.dashboard_module.gemini_status_snapshot') as mock_gemini, \
         patch('modules.dashboard_module.antigravity_status_snapshot') as mock_antigravity, \
         patch('modules.dashboard_module._vm_info') as mock_vm, \
         patch('modules.dashboard_module._codebase_analysis_summary') as mock_codebase, \
         patch('modules.dashboard_module._alliance_status_summary') as mock_alliance, \
         patch('modules.dashboard_module._cloud_sync_status_summary') as mock_cloud_sync, \
         patch('modules.dashboard_module._tail_log') as mock_tail, \
         patch('modules.dashboard_module.build_repo_context_guard') as mock_repo_guard:

        mock_env_vars.return_value = {
            "BROWSER_MODEL_LOOP_URL": "http://127.0.0.1:8765/model-loop",
            "GCE_WORKER_IP": "10.0.0.1",
            "GEMINI_CLI_PATH": r"C:\Users\abdul\.npm-packages\gemini.cmd",
            "ANTIGRAVITY_CLI_PATH": r"C:\Users\abdul\AppData\Local\agy\bin\agy.exe",
        }
        mock_pressure.return_value = {
            "status": "normal",
            "cpu_percent": 10.0,
            "memory_percent": 20.0,
            "maxed_out": False,
            "reasons": []
        }
        mock_fleet.return_value = {
            "launched": 1,
            "completed": 0,
            "pending": 1,
            "failed": 0,
            "in_progress": 1,
            "all_complete": False,
            "sessions_tracked": 0,
        }
        mock_gemini.return_value = {
            "installed": True,
            "ready": True,
            "version": "0.49.0",
            "headless_mode": "-p/--prompt",
            "state_path": r"C:\Users\abdul\jules-bridge\jules_inbox\gemini\GEMINI_PREFLIGHT.json",
            "preferred_gemini_command": r"C:\Users\abdul\.npm-packages\gemini.cmd",
        }
        mock_antigravity.return_value = {
            "installed": True,
            "ready": True,
            "version": "1.0.16",
            "headless_mode": "-p/--print",
            "model_count": 8,
            "state_path": r"C:\Users\abdul\jules-bridge\jules_inbox\gemini\ANTIGRAVITY_PREFLIGHT.json",
            "preferred_antigravity_command": r"C:\Users\abdul\AppData\Local\agy\bin\agy.exe",
        }
        mock_vm.return_value = {
            "vms": [{"provider": "GCP", "name": "jules-offload-worker", "ip": "10.0.0.1"}],
            "total": 1,
            "online": 1
        }
        mock_codebase.return_value = {
            "status": "ready",
            "root_name": "jules-bridge",
            "summary": {
                "file_count": 88,
                "route_count": 42,
                "module_count": 20,
                "test_count": 30,
                "frontend_dependency_count": 8,
                "integration_ready_count": 7,
                "truncated": False,
            },
            "frontend": {"present": True, "package_name": "dashboard-ui", "app_entry_present": True},
            "integrations": [{"id": "codebase_analyzer", "label": "Bounded local codebase analyzer", "ready": True, "tone": "success"}],
            "findings": [{"tone": "success", "title": "Ready", "detail": "Bounded handoff present."}],
        }
        mock_alliance.return_value = {
            "status": "ready",
            "summary": "8/8 switchboard gates passed.",
            "mode": "two_agent_alliance",
            "creator": "jules",
            "implementer": "antigravity_cli",
            "implementer_selection": "preferred",
            "ready_to_execute_alliance": True,
            "simultaneous_two_agent_mode": True,
            "safe_to_launch_live_work": False,
            "required_blocker_count": 0,
            "partial_caveat_count": 0,
            "gate_pass_count": 8,
            "gate_total_count": 8,
            "packet_count": 3,
            "workflow_step_count": 6,
            "state_age_s": 3,
            "lanes": [{"id": "jules", "label": "Jules", "role": "creator", "ready": True}],
        }
        mock_cloud_sync.return_value = {
            "status": "blocked",
            "state": "blocked",
            "branch": "master",
            "upstream": "origin/master",
            "remote_host": "github.com",
            "remote_label": "github.com/jules-bridge",
            "ahead": 0,
            "behind": 0,
            "dirty_count": 2,
            "staged_count": 0,
            "unstaged_count": 1,
            "untracked_count": 1,
            "github_authenticated": True,
            "github_account": "Job4874",
            "publish_ready": False,
            "synced": False,
            "blockers": ["dirty_worktree"],
            "warnings": [],
            "cache_age_s": 0,
        }
        mock_tail.return_value = [
            "Log line 1",
            "Starting ngrok at https://random-ngrok-url.ngrok.io/"
        ]
        mock_repo_guard.return_value = {
            "status": "ready",
            "summary": {"repo_count": 2, "collision_count": 1, "sample_repos": ["private-repo"]},
            "collisions": [{"type": "port_collision", "key": "5000"}],
            "guardrails": ["label by repo"],
            "cache_age_s": 0,
        }

        # Call get_dashboard_status
        start_utc = datetime.now(timezone.utc)
        result = get_dashboard_status(bridge_start_utc=start_utc)

        # Assertions
        assert result["ok"] is True
        assert "timestamp" in result
        assert result["contract"]["name"] == "jules_dashboard_status"
        assert result["contract"]["version"] == 2
        assert result["contract"]["transport"] == "poll"
        assert result["delivery"]["transport"] == "poll"
        assert result["delivery"]["streaming"] is False
        assert result["cache_age_s"] == 0
        assert result["execution_context"] == "[SCHOOL_COMPUTE]"
        assert result["quant_allowed"] is False

        assert result["bridge"]["status"] == "running"
        assert result["bridge"]["ngrok_url"] == "https://random-ngrok-url.ngrok.io"
        assert result["bridge"]["local_url"] == "http://127.0.0.1:5000"

        assert result["resource_pressure"]["status"] == "normal"
        assert result["resource_pressure"]["cpu_percent"] == 10.0
        assert result["resource_pressure"]["memory_percent"] == 20.0
        assert result["resource_pressure"]["maxed_out"] is False

        assert result["cloud"]["total"] == 1
        assert result["jules_fleet"]["launched"] == 1
        assert result["gemini_cli"]["ready"] is True
        assert result["gemini_cli"]["version"] == "0.49.0"
        assert "state_path" not in result["gemini_cli"]
        assert "preferred_gemini_command" not in result["gemini_cli"]
        assert result["antigravity_cli"]["ready"] is True
        assert result["antigravity_cli"]["model_count"] == 8
        assert "state_path" not in result["antigravity_cli"]
        assert "preferred_antigravity_command" not in result["antigravity_cli"]
        assert result["codebase_analysis"]["summary"]["route_count"] == 42
        assert result["codebase_analysis"]["integrations"][0]["id"] == "codebase_analyzer"
        assert result["alliance"]["mode"] == "two_agent_alliance"
        assert result["alliance"]["implementer"] == "antigravity_cli"
        assert result["alliance"]["safe_to_launch_live_work"] is False
        assert result["cloud_sync"]["state"] == "blocked"
        assert result["cloud_sync"]["blockers"] == ["dirty_worktree"]
        assert result["repo_context"]["summary"]["repo_count"] == 2
        assert "sample_repos" not in result["repo_context"]["summary"]
        assert result["repo_context"]["collisions"][0]["type"] == "port_collision"

        assert result["recent_logs"] == ["Log line 1", "Starting ngrok at https://random-ngrok-url.ngrok.io/"]
        assert result["model_loop"]["mode"] == "vm_browser"
        assert result["model_loop"]["requires_provider_api_keys"] is False
        assert "BROWSER_MODEL_LOOP_URL" in result["env_keys_present"]
        assert "GCE_WORKER_IP" in result["env_keys_present"]
        assert "GEMINI_CLI_PATH" in result["env_keys_present"]
        assert "ANTIGRAVITY_CLI_PATH" in result["env_keys_present"]
        assert "GEMINI_API_KEY" not in result["env_keys_present"]

def test_get_dashboard_status_cache():
    # Setup initial cache
    now = time.time()
    _dashboard_status_cache['last'] = (now, {"ok": True, "cached_key": "cached_val"})

    with patch('os.environ.get', return_value='5'):
        result = get_dashboard_status()
        assert result["ok"] is True
        assert result["cached_key"] == "cached_val"
        assert "cache_age_s" in result
        assert result["contract"]["transport"] == "poll"

def test_dashboard_status_event_stream_emits_contract_events():
    snapshots = [
        {
            "ok": True,
            "timestamp": "2026-07-05T20:00:00+00:00",
            "bridge": {"status": "running"},
        },
        {
            "ok": True,
            "timestamp": "2026-07-05T20:00:01+00:00",
            "bridge": {"status": "running"},
        },
    ]

    with patch('modules.dashboard_module._build_dashboard_status', side_effect=snapshots):
        events = list(dashboard_status_event_stream(max_events=2, sleep_fn=lambda _seconds: None))

    assert events[0] == "retry: 3000\n\n"
    assert events[1].startswith("id: 1\nevent: dashboard-status\ndata: ")
    assert events[2].startswith("id: 2\nevent: dashboard-status\ndata: ")

    payload = json.loads(events[1].split("data:", 1)[1])
    assert payload["contract"]["name"] == "jules_dashboard_status"
    assert payload["contract"]["version"] == 2
    assert payload["contract"]["transport"] == "sse"
    assert payload["contract"]["sequence"] == 1
    assert payload["delivery"]["streaming"] is True

def test_dashboard_status_event_stream_returns_error_event_on_snapshot_failure():
    with patch('modules.dashboard_module._build_dashboard_status', side_effect=RuntimeError("boom")):
        events = list(dashboard_status_event_stream(max_events=1, sleep_fn=lambda _seconds: None))

    payload = json.loads(events[1].split("data:", 1)[1])
    assert payload["ok"] is False
    assert payload["error"] == "stream_error"
    assert payload["contract"]["transport"] == "sse"

def test_get_dashboard_status_exception():
    with patch('modules.dashboard_module._env_vars') as mock_env_vars:
        mock_env_vars.side_effect = Exception("Failed to read env variables")

        result = get_dashboard_status()

        assert result["ok"] is False
        assert result["error"] == "Failed to read env variables"

def test_fmt_uptime():
    from modules.dashboard_module import _fmt_uptime
    assert _fmt_uptime(5) == "5s"
    assert _fmt_uptime(65) == "1m 5s"
    assert _fmt_uptime(3665) == "1h 1m 5s"
    assert _fmt_uptime(7200) == "2h 0m 0s"

def test_env_vars():
    env_content = "BROWSER_MODEL_LOOP_URL=http://127.0.0.1:8765/model-loop\n#COMMENT\n\nGCE_WORKER_IP = 10.0.0.1"
    with patch('pathlib.Path.read_text', return_value=env_content):
        env = _env_vars()
        assert env.get("BROWSER_MODEL_LOOP_URL") == "http://127.0.0.1:8765/model-loop"
        assert env.get("GCE_WORKER_IP") == "10.0.0.1"

def test_env_vars_exception():
    with patch('pathlib.Path.read_text', side_effect=Exception("Read error")):
        env = _env_vars()
        assert env == {}

def test_runtime_context_local_allows_quantower():
    with patch('modules.dashboard_module.socket.gethostname', return_value='jules-local'):
        status = _runtime_context({"JULES_CONTEXT": "[LOCAL]"})
    assert status["hostname"] == "jules-local"
    assert status["execution_context"] == "[LOCAL]"
    assert status["quant_allowed"] is True

def test_runtime_context_remote_vm_allows_quantower():
    status = _runtime_context({"JULES_CONTEXT": "[REMOTE_VM]"})
    assert status["execution_context"] == "[REMOTE_VM]"
    assert status["quant_allowed"] is True

def test_runtime_context_school_compute_blocks_quantower():
    status = _runtime_context({"JULES_CONTEXT": "[SCHOOL_COMPUTE]"})
    assert status["execution_context"] == "[SCHOOL_COMPUTE]"
    assert status["quant_allowed"] is False

def test_runtime_context_defaults_to_school_compute():
    status = _runtime_context({})
    assert status["execution_context"] == "[SCHOOL_COMPUTE]"
    assert status["quant_allowed"] is False

def test_tcp_reachable():
    with patch('socket.create_connection') as mock_conn:
        assert _tcp_reachable("127.0.0.1", 80) is True
        mock_conn.assert_called_once()

        mock_conn.side_effect = Exception("Connection refused")
        assert _tcp_reachable("127.0.0.1", 80) is False

def test_tcp_reachable_empty_host():
    assert _tcp_reachable("") is False

def test_tail_log():
    log_content = "line1\nline2\nline3\nline4"
    with patch('pathlib.Path.read_text', return_value=log_content):
        assert _tail_log(2) == ["line3", "line4"]
        assert _tail_log(10) == ["line1", "line2", "line3", "line4"]

def test_tail_log_exception():
    with patch('pathlib.Path.read_text', side_effect=Exception("Read error")):
        assert _tail_log() == []

def test_safe_log_lines_masks_local_paths():
    from pathlib import Path
    # Use actual repo root and home so this test works on any machine
    root = str(Path(__file__).resolve().parent.parent)
    home = str(Path.home())
    lines = [
        f"Log path: {root}\\bridge.log",
        f"Tool path: {home}\\AppData\\Local\\agy\\bin\\agy.exe",
    ]

    result = _safe_log_lines(lines)

    assert "[repo-root]" in result[0]
    assert "[user-home]" in result[1]
    assert "Users" not in "\n".join(result)

def test_cli_status_summary_is_frontend_compact():
    payload = {
        "installed": True,
        "ready": True,
        "version": "1.0.16",
        "headless_mode": "-p/--print",
        "model_count": 8,
        "state_path": r"C:\Users\abdul\secret.json",
        "preferred_antigravity_command": r"C:\Users\abdul\AppData\Local\agy\bin\agy.exe",
    }

    result = _cli_status_summary(payload, include_model_count=True)

    assert result["ready"] is True
    assert result["model_count"] == 8
    assert "state_path" not in result
    assert "preferred_antigravity_command" not in result

def test_read_json():
    json_content = '{"key": "value"}'
    # Don't mock pathlib.Path.read_text globally here because mock_path needs to mock it
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.return_value = json_content
    assert _read_json(mock_path) == {"key": "value"}

def test_read_json_exception():
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = Exception("Parse error")
    assert _read_json(mock_path) is None

def test_codebase_analysis_summary_is_compact():
    with patch('modules.dashboard_module.analyze_codebase') as mock_analyze:
        mock_analyze.return_value = {
            "status": "ready",
            "root": {"name": "jules-bridge", "path_ref": "path:jules-bridge:abc"},
            "summary": {
                "file_count": 100,
                "route_count": 50,
                "module_count": 25,
                "test_count": 40,
                "frontend_dependency_count": 8,
                "integration_ready_count": 7,
                "truncated": False,
                "line_count": 99999,
            },
            "frontend": {"present": True, "package_name": "dashboard-ui", "app_entry_present": True},
            "integrations": [
                {"id": "codebase_analyzer", "label": "Bounded local codebase analyzer", "ready": True, "tone": "success"}
            ],
            "findings": [{"tone": "success", "title": "Ready", "detail": "No raw files returned."}],
            "files": [{"path": "secret.py", "bytes": 10}],
        }

        result = _codebase_analysis_summary()

    assert result["status"] == "ready"
    assert result["root_name"] == "jules-bridge"
    assert result["summary"]["route_count"] == 50
    assert result["integrations"][0]["id"] == "codebase_analyzer"
    assert "files" not in result
    mock_analyze.assert_called_once_with(max_files=1800, include_files=False)

def test_alliance_status_summary_is_privacy_safe():
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "generated_at_utc": now,
        "status": "ready",
        "summary": "8/8 switchboard gates passed.",
        "roles": {
            "mode": "two_agent_alliance",
            "creator": {"agent": "jules"},
        },
        "active_implementer": {"name": "antigravity_cli", "selection": "preferred"},
        "readiness": {
            "jules": {"ready": True, "installed": True},
            "antigravity_cli": {"ready": True, "installed": True},
            "legacy_gemini_cli": {"ready": False, "installed": True, "likely_blocker": "auth_required"},
            "akc": {"ready": True},
            "collaboration_proof_state": {"available": True, "status": "pass"},
        },
        "completion_assessment": {
            "ready_to_execute_alliance": True,
            "simultaneous_two_agent_mode": True,
            "required_blockers": [],
            "partial_caveats": [],
            "safe_to_launch_live_work": False,
        },
        "gates": [
            {"name": "creator_jules_reachable", "status": "pass", "required": True},
            {"name": "preferred_implementer_reachable", "status": "pass", "required": True},
        ],
        "workflow": [{"step": "classify"}, {"step": "verify"}],
        "packets": {
            "packet_paths": {
                "creator_jules": r"C:\Users\abdul\secret\ALLIANCE_CREATOR_JULES.md",
                "implementer_google": r"C:\Users\abdul\secret\ALLIANCE_IMPLEMENTER_GOOGLE_TERMINAL.md",
            }
        },
    }

    with patch('modules.dashboard_module._read_json', return_value=state):
        result = _alliance_status_summary()

    assert result["status"] == "ready"
    assert result["mode"] == "two_agent_alliance"
    assert result["creator"] == "jules"
    assert result["implementer"] == "antigravity_cli"
    assert result["gate_pass_count"] == 2
    assert result["packet_count"] == 2
    assert result["lanes"][2]["id"] == "legacy_gemini_cli"
    assert result["lanes"][2]["status"] == "installed"
    assert r"C:\Users" not in json.dumps(result)

def test_alliance_status_summary_handles_missing_state():
    with patch('modules.dashboard_module._read_json', return_value=None):
        result = _alliance_status_summary()

    assert result["status"] == "missing"
    assert result["mode"] == "unconfigured"
    assert result["ready_to_execute_alliance"] is False
    assert result["required_blocker_count"] == 1

def test_alliance_status_summary_uses_live_cli_readiness():
    state = {
        "status": "ready",
        "roles": {"mode": "two_agent_alliance", "creator": {"agent": "jules"}},
        "active_implementer": {"name": "antigravity_cli", "selection": "preferred"},
        "readiness": {
            "jules": {"ready": True, "installed": True},
            "antigravity_cli": {"ready": False, "installed": False},
            "legacy_gemini_cli": {"ready": True, "installed": True},
        },
        "completion_assessment": {"ready_to_execute_alliance": True, "simultaneous_two_agent_mode": True},
        "gates": [],
        "workflow": [],
        "packets": {"packet_paths": {}},
    }

    with patch('modules.dashboard_module._read_json', return_value=state):
        result = _alliance_status_summary(
            gemini_cli={"ready": False, "installed": True, "last_blocker": "auth_required"},
            antigravity_cli={"ready": True, "installed": True, "last_blocker": ""},
        )

    lanes = {row["id"]: row for row in result["lanes"]}
    assert lanes["legacy_gemini_cli"]["status"] == "installed"
    assert lanes["legacy_gemini_cli"]["blocker"] == "auth_required"
    assert lanes["antigravity_cli"]["status"] == "ready"

def test_cloud_sync_status_summary_is_compact():
    payload = {
        "status": "blocked",
        "state": "blocked",
        "repo": {
            "branch": "master",
            "upstream": "origin/master",
            "remote_host": "github.com",
            "remote_label": "github.com/jules-bridge",
        },
        "git": {
            "ahead": 0,
            "behind": 0,
            "dirty_count": 3,
            "staged_count": 1,
            "unstaged_count": 1,
            "untracked_count": 1,
        },
        "github": {"authenticated": True, "account": "Job4874"},
        "publish_ready": False,
        "synced": False,
        "blockers": ["dirty_worktree"],
        "warnings": ["remote_tracking_stale"],
        "cache_age_s": 4,
        "privacy": {"remote_url_returned": False},
    }

    with patch('modules.dashboard_module.get_cloud_sync_status', return_value=payload):
        result = _cloud_sync_status_summary()

    assert result["state"] == "blocked"
    assert result["remote_host"] == "github.com"
    assert result["dirty_count"] == 3
    assert result["github_authenticated"] is True
    assert result["blockers"] == ["dirty_worktree"]
    assert "privacy" not in result

def test_fleet_status():
    cot_data = {"selected_count": 5, "completed_count": 2, "pending_count": 3, "all_complete": False}
    launch_data = {"launched": [{"remote_status": "failed"}, {"remote_status": "in progress"}]}
    watch_data = {"sessions_checked": 10}

    def side_effect(path):
        if "COT" in str(path):
            return cot_data
        elif "LAUNCH" in str(path):
            return launch_data
        elif "WATCH" in str(path):
            return watch_data
        return None

    with patch('modules.dashboard_module._read_json', side_effect=side_effect):
        status = _fleet_status()
        assert status["launched"] == 5
        assert status["completed"] == 2
        assert status["pending"] == 3
        assert status["failed"] == 1
        assert status["in_progress"] == 1
        assert status["all_complete"] is False
        assert status["sessions_tracked"] == 10

def test_vm_info():
    env = {
        "GCE_WORKER_IP": "10.0.0.1",
        "AZURE_WORKER_VM1": "10.0.0.2",
    }
    with patch('modules.dashboard_module._tcp_reachable', return_value=True):
        info = _vm_info(env)
        assert info["total"] == 2
        assert info["online"] == 2
        assert len(info["vms"]) == 2

        vms = sorted(info["vms"], key=lambda x: x["provider"])
        assert vms[0]["provider"] == "Azure"
        assert vms[0]["ip"] == "10.0.0.2"
        assert vms[1]["provider"] == "GCP"
        assert vms[1]["ip"] == "10.0.0.1"
