import pytest
from unittest.mock import patch
from modules.shell_executor import execute

def test_shell_execute_cache(monkeypatch):
    monkeypatch.setenv('SHELL_CACHE_TTL_S', '2')

    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "hello"
        mock_run.return_value.stderr = ""

        # First call
        res1 = execute("echo hello", shell="cmd")
        assert res1['stdout'] == "hello"
        assert mock_run.call_count == 1

        # Second call within TTL
        res2 = execute("echo hello", shell="cmd")
        assert res2['stdout'] == "hello"
        assert mock_run.call_count == 1 # Should hit cache

        # Different command
        res3 = execute("echo world", shell="cmd")
        assert mock_run.call_count == 2

        # Wait for TTL
        import time
        time.sleep(2.1)

        # Call again after TTL
        res4 = execute("echo hello", shell="cmd")
        assert mock_run.call_count == 3

def test_shell_execute_timeout(monkeypatch):
    # This might be harder to test without real subprocess or very specific mocking
    # But we can verify it passes timeout to subprocess.run
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        execute("slow command", timeout=5)
        args, kwargs = mock_run.call_args
        assert kwargs['timeout'] == 5
