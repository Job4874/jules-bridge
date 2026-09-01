import pytest
from unittest.mock import patch
import driver

def test_driver_exception_handling(caplog):
    class BreakLoop(Exception): pass

    def fake_bridge(path, payload=None, method="POST", **kwargs):
        if path == "/health":
            return {"status": "ok"}
        if path == "/mission/cycle":
            return {"ok": True, "active_task": {"task_id": "mock_task", "title": "Mock Task"}}
        if path == "/mission/failed":
            return {"ok": True}
        return {}

    with patch("driver._call_bridge", side_effect=fake_bridge), \
         patch("driver._execute_task", side_effect=Exception("Test Task Exception")), \
         patch("driver.time.sleep", side_effect=BreakLoop):

        with pytest.raises(BreakLoop):
            driver.main()

    # We want to test that an exception in task execution is handled correctly
    # looking at driver.py `run_cycle`, _execute_task exception is actually NOT caught in run_cycle
    # it is caught in the `main` while loop

    assert "Driver error: Test Task Exception" in caplog.text
