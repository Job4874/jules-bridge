import pytest
from unittest.mock import patch, call
import driver

@patch("driver._call_bridge")
def test_run_cycle_mission_cycle_fails(mock_call_bridge):
    mock_call_bridge.return_value = {"ok": False, "error": "test error"}

    result = driver.run_cycle()

    assert result is False
    mock_call_bridge.assert_called_once_with("/mission/cycle", {})

@patch("driver._call_bridge")
def test_run_cycle_no_active_task(mock_call_bridge):
    mock_call_bridge.return_value = {"ok": True, "queue_summary": {"pending": 0, "done": 1}}

    result = driver.run_cycle()

    assert result is False
    mock_call_bridge.assert_called_once_with("/mission/cycle", {})

@patch("driver._notify")
@patch("driver._execute_task")
@patch("driver._call_bridge")
def test_run_cycle_success(mock_call_bridge, mock_execute_task, mock_notify):
    def call_bridge_side_effect(path, payload=None, method="POST"):
        if path == "/mission/cycle":
            return {
                "ok": True,
                "active_task": {
                    "task_id": "test_123",
                    "title": "Test Task",
                    "task_type": "research",
                    "url": "http://example.com"
                }
            }
        return {"ok": True}

    mock_call_bridge.side_effect = call_bridge_side_effect

    mock_execute_task.return_value = {
        "ok": True,
        "screenshot_path": "/path/to/snap.png",
        "questions_answered": 2,
        "submitted": True
    }

    result = driver.run_cycle()

    assert result is True
    mock_execute_task.assert_called_once_with({
        "task_id": "test_123",
        "title": "Test Task",
        "task_type": "research",
        "url": "http://example.com"
    })

    assert mock_call_bridge.call_count == 3
    args_list = mock_call_bridge.call_args_list
    assert args_list[0] == call("/mission/cycle", {})
    assert args_list[1] == call("/mission/done", {"task_id": "test_123", "result": mock_execute_task.return_value})
    assert args_list[2] == call("/learning/reflect", {"task": {
        "task_id": "test_123",
        "title": "Test Task",
        "task_type": "research",
        "url": "http://example.com"
    }, "result": mock_execute_task.return_value})

    mock_notify.assert_called_once()
    notify_args = mock_notify.call_args[0]
    assert notify_args[0] == "✅ Mission Complete: Test Task"
    assert "Task test_123 completed." in notify_args[1]
    assert "Type: research" in notify_args[1]
    assert "URL: http://example.com" in notify_args[1]
    assert "Answered: 2" in notify_args[1]
    assert "Submitted: True" in notify_args[1]
    assert notify_args[2] == "/path/to/snap.png"

@patch("driver._notify")
@patch("driver._execute_task")
@patch("driver._call_bridge")
def test_run_cycle_failure(mock_call_bridge, mock_execute_task, mock_notify):
    def call_bridge_side_effect(path, payload=None, method="POST"):
        if path == "/mission/cycle":
            return {
                "ok": True,
                "active_task": {
                    "task_id": "test_123",
                    "title": "Test Task",
                    "task_type": "research",
                    "url": "http://example.com"
                }
            }
        return {"ok": True}

    mock_call_bridge.side_effect = call_bridge_side_effect

    mock_execute_task.return_value = {
        "ok": False,
        "error": "Timeout occurred"
    }

    result = driver.run_cycle()

    assert result is True
    mock_execute_task.assert_called_once_with({
        "task_id": "test_123",
        "title": "Test Task",
        "task_type": "research",
        "url": "http://example.com"
    })

    assert mock_call_bridge.call_count == 2
    args_list = mock_call_bridge.call_args_list
    assert args_list[0] == call("/mission/cycle", {})
    assert args_list[1] == call("/mission/failed", {"task_id": "test_123", "reason": "Timeout occurred"})

    mock_notify.assert_called_once()
    notify_args = mock_notify.call_args[0]
    assert notify_args[0] == "❌ Mission Failed: Test Task"
    assert "Task test_123 failed." in notify_args[1]
    assert "Error: Timeout occurred" in notify_args[1]
    assert "URL: http://example.com" in notify_args[1]
