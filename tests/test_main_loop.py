import pytest
from unittest.mock import patch, MagicMock
from main_loop import daemon_loop_iteration

@patch('main_loop.check_and_scale_compute')
@patch('main_loop.read_inbox')
@patch('main_loop.dispatch')
def test_daemon_loop_no_pressure_no_task(mock_dispatch, mock_read_inbox, mock_scale):
    mock_scale.return_value = "Memory at 50.0%, no action needed."
    mock_read_inbox.return_value = None

    daemon_loop_iteration()

    mock_scale.assert_called_once()
    mock_read_inbox.assert_called_once()
    mock_dispatch.assert_not_called()

@patch('main_loop.check_and_scale_compute')
@patch('main_loop.read_inbox')
@patch('main_loop.dispatch')
def test_daemon_loop_with_pressure_and_task(mock_dispatch, mock_read_inbox, mock_scale):
    mock_scale.return_value = "EXECUTED: az vm start --name OracleV5"
    mock_read_inbox.return_value = {"type": "Code/Dev"}

    daemon_loop_iteration()

    mock_scale.assert_called_once()
    mock_read_inbox.assert_called_once()
    mock_dispatch.assert_called_once_with({"type": "Code/Dev"})
