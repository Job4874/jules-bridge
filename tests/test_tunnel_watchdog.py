"""Tests for the tunnel watchdog in start.py."""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

import start


@pytest.fixture
def mock_watchdog(tmp_path):
    watchdog = start.TunnelWatchdog(inbox_dir=tmp_path)
    # mock the sleep in the run loop if we ever call it, but we'll test check_tunnel directly
    return watchdog


@patch("start.urllib.request.urlopen")
def test_ping_success(mock_urlopen, mock_watchdog, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    mock_watchdog.check_tunnel()

    assert mock_watchdog.consecutive_failures == 0
    health_file = tmp_path / "TUNNEL_HEALTH.json"
    assert health_file.exists()
    data = json.loads(health_file.read_text())
    assert data["status"] == "healthy"
    assert data["consecutive_failures"] == 0


@patch("start.urllib.request.urlopen")
@patch("start.ngrok")
def test_ping_failure_reconnect(mock_ngrok, mock_urlopen, mock_watchdog, tmp_path):
    mock_urlopen.side_effect = OSError("Connection refused")
    
    # 1st fail
    mock_watchdog.check_tunnel()
    assert mock_watchdog.consecutive_failures == 1
    
    # 2nd fail
    mock_watchdog.check_tunnel()
    assert mock_watchdog.consecutive_failures == 2
    
    # 3rd fail -> triggers reconnect (and resets to 0 since connect succeeds)
    mock_watchdog.check_tunnel()
    assert mock_watchdog.consecutive_failures == 0
    mock_ngrok.kill.assert_called_once()
    mock_ngrok.connect.assert_called_once_with(5000, domain=start.NGROK_DOMAIN)
    
    data = json.loads((tmp_path / "TUNNEL_HEALTH.json").read_text())
    assert data["status"] == "reconnecting"


@patch("start.urllib.request.urlopen")
@patch("start.ngrok")
@patch("start.subprocess.run")
def test_reconnect_failure_escalation(mock_subrun, mock_ngrok, mock_urlopen, mock_watchdog, tmp_path):
    mock_urlopen.side_effect = OSError("Connection refused")
    mock_ngrok.connect.side_effect = Exception("ngrok error")
    
    # Trigger 3 reconnect failures by checking 5 times.
    # 1st, 2nd, 3rd check -> ping fails -> consecutive=3 -> reconnect fails (reconnect_fails=1)
    # 4th check -> ping fails -> consecutive=4 -> reconnect fails (reconnect_fails=2)
    # 5th check -> ping fails -> consecutive=5 -> reconnect fails (reconnect_fails=3, escalated!)
    for _ in range(5):
        mock_watchdog.check_tunnel()
        
    assert mock_watchdog.reconnect_failures == 3
    
    blocker_file = tmp_path / "TUNNEL_BLOCKER.md"
    assert blocker_file.exists()
    
    response_file = tmp_path / "JULES_RESPONSE.md"
    assert response_file.exists()
    assert "[TUNNEL_DEAD]" in response_file.read_text()
    
    # Verify git commands
    assert mock_subrun.call_count == 3
    calls = mock_subrun.call_args_list
    assert "add" in calls[0][0][0]
    assert "commit" in calls[1][0][0]
    assert "push" in calls[2][0][0]
