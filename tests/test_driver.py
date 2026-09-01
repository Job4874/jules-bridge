"""Tests for F1 Autonomous Driver."""
from unittest.mock import patch

import driver


@patch("driver.run_cycle")
def test_driver_main_exception_handling(mock_run_cycle, caplog):
    """Verify that exceptions in run_cycle are caught, logged, and trigger a sleep."""
    # Setup mock to break the loop on time.sleep after logging exception
    with patch("driver.time.sleep", side_effect=KeyboardInterrupt) as mock_sleep:
        # Mock bridge health check to pass immediately
        with patch("driver._call_bridge", side_effect=[{"status": "ok"}]):
            # Setup run_cycle to raise an exception
            mock_run_cycle.side_effect = RuntimeError("Simulated exception in task")

            try:
                driver.main()
            except KeyboardInterrupt:
                pass

            mock_sleep.assert_called_with(driver.POLL_SECONDS)
            mock_run_cycle.assert_called_once()
            assert "Driver error: Simulated exception in task" in caplog.text
