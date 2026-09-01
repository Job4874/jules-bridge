import pytest
from unittest.mock import patch

from driver import _load_env, main

def test_load_env_exception_handling(caplog):
    with patch("driver.Path.exists", return_value=True), \
         patch("driver.Path.read_text", side_effect=Exception("Read error test")):
        _load_env()

    assert "Could not load .env: Read error test" in caplog.text

def test_main_loop_exception_handling(caplog):
    import logging

    def mock_sleep(seconds):
        if hasattr(mock_sleep, "called"):
            raise KeyboardInterrupt()
        mock_sleep.called = True

    with patch("driver._call_bridge", return_value={"status": "ok", "identity": "test"}), \
         patch("driver.run_cycle", side_effect=Exception("Task execution error")), \
         patch("driver.time.sleep", side_effect=mock_sleep), \
         patch("driver.sys.exit"):

        with caplog.at_level(logging.ERROR):
            try:
                main()
            except KeyboardInterrupt:
                pass

    assert "Driver error: Task execution error" in caplog.text
