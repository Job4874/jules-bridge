import sys
from unittest.mock import patch, MagicMock

import driver

@patch("driver._execute_task")
@patch("driver._call_bridge")
@patch("driver.time.sleep")
def test_run_cycle_handles_execute_task_exception(mock_sleep, mock_call_bridge, mock_execute):
    # Setup mock responses for bridge calls
    # 1. /mission/cycle returns a task
    # 2. /mission/failed returns success
    # 3. /notify/email returns success
    mock_call_bridge.side_effect = [
        {"ok": True, "active_task": {"task_id": "err_123", "title": "Crash Test"}},
        {"ok": True},
        {"ok": True},
    ]

    # Make _execute_task raise an exception
    mock_execute.side_effect = Exception("Simulated crash")

    # Run the cycle
    result = driver.run_cycle()

    # Verify the cycle returns True (meaning it didn't completely abort)
    assert result is True

    # Verify we attempted to execute the task
    mock_execute.assert_called_once()

    # Verify that the mission failure was recorded
    call_args_list = mock_call_bridge.call_args_list
    assert len(call_args_list) == 3

    # Verify the first call was to get the cycle
    assert call_args_list[0][0][0] == "/mission/cycle"

    # Verify the second call was to report the failure
    assert call_args_list[1][0][0] == "/mission/failed"
    assert call_args_list[1][0][1] == {"task_id": "err_123", "reason": "Simulated crash"}

    # Verify the third call was to notify the operator
    assert call_args_list[2][0][0] == "/notify/email"
    notify_payload = call_args_list[2][0][1]
    assert notify_payload["subject"] == "❌ Mission Failed: Crash Test"
    assert "Simulated crash" in notify_payload["body"]
