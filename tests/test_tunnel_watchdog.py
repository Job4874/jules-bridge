"""Tests for the tunnel watchdog in start.py."""
import json
from unittest.mock import patch, MagicMock

import pytest

import start


@pytest.fixture
def watchdog_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(start, "configure_ngrok_auth", lambda: True)
    watchdog = start.TunnelWatchdog(inbox_dir=tmp_path)
    watchdog.auth_blocked = False
    return watchdog


@patch("start.urllib.request.urlopen")
def test_ping_success(mock_urlopen, watchdog_fixture, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    watchdog_fixture.check_tunnel()

    assert watchdog_fixture.consecutive_failures == 0
    health_file = tmp_path / "TUNNEL_HEALTH.json"
    assert health_file.exists()
    data = json.loads(health_file.read_text())
    assert data["status"] == "healthy"
    assert data["consecutive_failures"] == 0


@patch("start.urllib.request.urlopen")
@patch("start.ngrok")
def test_ping_failure_reconnect(mock_ngrok, mock_urlopen, watchdog_fixture, tmp_path):
    mock_urlopen.side_effect = OSError("Connection refused")

    # 1st fail
    watchdog_fixture.check_tunnel()
    assert watchdog_fixture.consecutive_failures == 1

    # 2nd fail
    watchdog_fixture.check_tunnel()
    assert watchdog_fixture.consecutive_failures == 2

    # 3rd fail -> triggers reconnect (and resets to 0 since connect succeeds)
    watchdog_fixture.check_tunnel()
    assert watchdog_fixture.consecutive_failures == 0
    mock_ngrok.kill.assert_called_once()
    mock_ngrok.connect.assert_called_once_with(5000, domain=start.NGROK_DOMAIN)

    data = json.loads((tmp_path / "TUNNEL_HEALTH.json").read_text())
    assert data["status"] == "reconnecting"


@patch("start.urllib.request.urlopen")
@patch("start.ngrok")
@patch("start.subprocess.run")
def test_reconnect_failure_escalation(mock_subrun, mock_ngrok, mock_urlopen, watchdog_fixture, tmp_path):
    mock_urlopen.side_effect = OSError("Connection refused")
    mock_ngrok.connect.side_effect = Exception("ngrok error")

    for _ in range(5):
        watchdog_fixture.check_tunnel()

    assert watchdog_fixture.reconnect_failures == 3
    assert watchdog_fixture.escalated is True

    blocker_file = tmp_path / "TUNNEL_BLOCKER.md"
    assert blocker_file.exists()

    response_file = tmp_path / "JULES_RESPONSE.md"
    assert response_file.exists()
    assert "[TUNNEL_DEAD]" in response_file.read_text()

    mock_subrun.assert_not_called()


@patch("start.configure_ngrok_auth", return_value=False)
def test_auth_blocked_skips_reconnect(mock_configure_auth, watchdog_fixture, tmp_path):
    watchdog_fixture.auth_blocked = True
    watchdog_fixture.check_tunnel()

    health = json.loads((tmp_path / "TUNNEL_HEALTH.json").read_text())
    assert health["status"] == "auth_required"
    assert watchdog_fixture.reconnect_failures == 0
