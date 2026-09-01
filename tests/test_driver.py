import pytest
from unittest.mock import patch

from driver import run_cycle

@patch("driver._call_bridge")
@patch("driver.LOGGER")
def test_run_cycle_mission_cycle_fails(mock_logger, mock_call_bridge):
    """Test run_cycle when /mission/cycle returns ok: False."""
    mock_call_bridge.return_value = {"ok": False, "error": "Internal Server Error"}

    result = run_cycle()

    assert result is False
    mock_call_bridge.assert_called_once_with("/mission/cycle", {})
    mock_logger.error.assert_called_once_with("Mission cycle failed: %s", "Internal Server Error")


@patch("driver._call_bridge")
@patch("driver.LOGGER")
def test_run_cycle_no_active_task(mock_logger, mock_call_bridge):
    """Test run_cycle when /mission/cycle returns ok: True but no active_task."""
    mock_call_bridge.return_value = {
        "ok": True,
        "queue_summary": {"pending": 2, "done": 5}
    }

    result = run_cycle()

    assert result is False
    mock_call_bridge.assert_called_once_with("/mission/cycle", {})
    mock_logger.info.assert_called_with("Queue clear — pending=%s done=%s", 2, 5)


@patch("driver._notify")
@patch("driver._execute_task")
@patch("driver._call_bridge")
@patch("driver.LOGGER")
def test_run_cycle_mission_success(mock_logger, mock_call_bridge, mock_execute_task, mock_notify):
    """Test run_cycle when a task is successfully executed."""
    # Setup mocks
    mock_call_bridge.side_effect = [
        # First call: /mission/cycle
        {
            "ok": True,
            "active_task": {
                "task_id": "task-123",
                "title": "Test Task",
                "task_type": "research",
                "url": "https://example.com"
            }
        },
        # Second call: /mission/done
        {"ok": True},
        # Third call: /learning/reflect
        {"ok": True}
    ]

    mock_execute_task.return_value = {
        "ok": True,
        "screenshot_path": "/tmp/screenshot.png",
        "questions_answered": 1,
        "submitted": True
    }

    result = run_cycle()

    assert result is True

    # Assert _execute_task was called with the correct active_task
    mock_execute_task.assert_called_once_with({
        "task_id": "task-123",
        "title": "Test Task",
        "task_type": "research",
        "url": "https://example.com"
    })

    # Assert _call_bridge was called for done and reflect
    assert mock_call_bridge.call_count == 3
    mock_call_bridge.assert_any_call("/mission/done", {
        "task_id": "task-123",
        "result": {
            "ok": True,
            "screenshot_path": "/tmp/screenshot.png",
            "questions_answered": 1,
            "submitted": True
        }
    })
    mock_call_bridge.assert_any_call("/learning/reflect", {
        "task": {
            "task_id": "task-123",
            "title": "Test Task",
            "task_type": "research",
            "url": "https://example.com"
        },
        "result": {
            "ok": True,
            "screenshot_path": "/tmp/screenshot.png",
            "questions_answered": 1,
            "submitted": True
        }
    })

    # Assert _notify was called
    mock_notify.assert_called_once()
    notify_args = mock_notify.call_args[0]
    assert notify_args[0] == "✅ Mission Complete: Test Task"
    assert "Task task-123 completed." in notify_args[1]
    assert notify_args[2] == "/tmp/screenshot.png"


@patch("driver._notify")
@patch("driver._execute_task")
@patch("driver._call_bridge")
@patch("driver.LOGGER")
def test_run_cycle_mission_failure(mock_logger, mock_call_bridge, mock_execute_task, mock_notify):
    """Test run_cycle when a task execution fails."""
    # Setup mocks
    mock_call_bridge.side_effect = [
        # First call: /mission/cycle
        {
            "ok": True,
            "active_task": {
                "task_id": "task-456",
                "title": "Failing Task",
                "task_type": "code",
                "url": "https://github.com"
            }
        },
        # Second call: /mission/failed
        {"ok": True}
    ]

    mock_execute_task.return_value = {
        "ok": False,
        "error": "Failed to run tests"
    }

    result = run_cycle()

    assert result is True

    # Assert _execute_task was called with the correct active_task
    mock_execute_task.assert_called_once_with({
        "task_id": "task-456",
        "title": "Failing Task",
        "task_type": "code",
        "url": "https://github.com"
    })

    # Assert _call_bridge was called for failed
    assert mock_call_bridge.call_count == 2
    mock_call_bridge.assert_any_call("/mission/failed", {
        "task_id": "task-456",
        "reason": "Failed to run tests"
    })

    # Assert _notify was called for failure
    mock_notify.assert_called_once()
    notify_args = mock_notify.call_args[0]
    assert notify_args[0] == "❌ Mission Failed: Failing Task"
    assert "Task task-456 failed." in notify_args[1]
    assert "Error: Failed to run tests" in notify_args[1]
