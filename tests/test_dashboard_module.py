import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timezone
import json
import socket
import time
import modules.dashboard_module
from pathlib import Path

from modules.dashboard_module import (
    get_dashboard_status,
    _dashboard_status_cache,
    _env_vars,
    _tcp_reachable,
    _tail_log,
    _read_json,
    _fleet_status,
    _vm_info,
    _runtime_context,
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
         patch('modules.dashboard_module._vm_info') as mock_vm, \
         patch('modules.dashboard_module._tail_log') as mock_tail, \
         patch('modules.dashboard_module.build_repo_context_guard') as mock_repo_guard:

        mock_env_vars.return_value = {
            "GEMINI_API_KEY": "yes",
            "GCE_WORKER_IP": "10.0.0.1"
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
        mock_vm.return_value = {
            "vms": [{"provider": "GCP", "name": "jules-offload-worker", "ip": "10.0.0.1"}],
            "total": 1,
            "online": 1
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
        assert result["repo_context"]["summary"]["repo_count"] == 2
        assert "sample_repos" not in result["repo_context"]["summary"]
        assert result["repo_context"]["collisions"][0]["type"] == "port_collision"

        assert result["recent_logs"] == ["Log line 1", "Starting ngrok at https://random-ngrok-url.ngrok.io/"]
        assert "GEMINI_API_KEY" in result["env_keys_present"]
        assert "GCE_WORKER_IP" in result["env_keys_present"]
        assert "OPENROUTER_API_KEY" not in result["env_keys_present"]

def test_get_dashboard_status_cache():
    # Setup initial cache
    now = time.time()
    _dashboard_status_cache['last'] = (now, {"ok": True, "cached_key": "cached_val"})

    with patch('os.environ.get', return_value='5'):
        result = get_dashboard_status()
        assert result["ok"] is True
        assert result["cached_key"] == "cached_val"
        assert "cache_age_s" in result

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
    env_content = "GEMINI_API_KEY=12345\n#COMMENT\n\nGCE_WORKER_IP = 10.0.0.1"
    with patch('pathlib.Path.read_text', return_value=env_content):
        env = _env_vars()
        assert env.get("GEMINI_API_KEY") == "12345"
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
