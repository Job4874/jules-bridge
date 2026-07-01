"""Tests for the tunnel watchdog in start.py."""
import json
from unittest.mock import patch, MagicMock

import pytest

import start


@pytest.fixture
def watchdog_fixture(tmp_path):
    watchdog = start.TunnelWatchdog(inbox_dir=tmp_path)
    return watchdog


@patch("start.ping_public")
def test_ping_success(mock_ping_public, watchdog_fixture, tmp_path):
    mock_ping_public.return_value = (True, "")

    watchdog_fixture.check_tunnel()

    assert watchdog_fixture.consecutive_failures == 0
    health_file = tmp_path / "TUNNEL_HEALTH.json"
    assert health_file.exists()
    data = json.loads(health_file.read_text())
    assert data["status"] == "healthy"
    assert data["consecutive_failures"] == 0


@patch("start.connect_ngrok")
@patch("start.ping_public")
def test_ping_failure_reconnect(mock_ping_public, mock_connect_ngrok, watchdog_fixture, tmp_path):
    mock_ping_public.return_value = (False, "404")
    mock_connect_ngrok.return_value = start.NGROK_PUBLIC_URL

    watchdog_fixture.check_tunnel()
    assert watchdog_fixture.consecutive_failures == 1

    watchdog_fixture.check_tunnel()
    assert watchdog_fixture.consecutive_failures == 2

    watchdog_fixture.check_tunnel()
    assert watchdog_fixture.consecutive_failures == 0
    mock_connect_ngrok.assert_called_once()

    data = json.loads((tmp_path / "TUNNEL_HEALTH.json").read_text())
    assert data["status"] == "reconnecting"


@patch("start.connect_ngrok")
@patch("start.ping_public")
@patch("start.subprocess.run")
def test_reconnect_failure_escalation(mock_subrun, mock_ping_public, mock_connect_ngrok, watchdog_fixture, tmp_path):
    mock_ping_public.return_value = (False, "404")
    mock_connect_ngrok.side_effect = Exception("ngrok error")

    for _ in range(6):
        watchdog_fixture.check_tunnel()

    assert watchdog_fixture.reconnect_failures == 4

    blocker_file = tmp_path / "TUNNEL_BLOCKER.md"
    assert blocker_file.exists()
    assert "Last error:" in blocker_file.read_text()

    response_file = tmp_path / "JULES_RESPONSE.md"
    assert response_file.exists()
    assert "[TUNNEL_DEAD]" in response_file.read_text()

    assert mock_subrun.call_count == 3
