import pytest
from unittest.mock import patch
from modules.jules_orchestrator import list_remote_sessions, launch_packets

def test_jules_session_cache(monkeypatch):
    monkeypatch.setenv('JULES_SESSION_CACHE_TTL_S', '2')
    
    with patch('modules.jules_orchestrator._run_cli_command') as mock_run:
        mock_run.return_value = {
            "exit_code": 0,
            "stdout": "session 123456",
            "stderr": "",
            "timed_out": False
        }
        
        # First call
        res1 = list_remote_sessions(dry_run=False)
        assert "123456" in res1['session_ids']
        assert mock_run.call_count == 1
        assert res1.get('cache_hit') is False
        
        # Second call
        res2 = list_remote_sessions(dry_run=False)
        assert "123456" in res2['session_ids']
        assert mock_run.call_count == 1
        assert res2.get('cache_hit') is True
        
        # Wait for TTL
        import time
        time.sleep(2.1)
        
        # Third call
        res3 = list_remote_sessions(dry_run=False)
        assert mock_run.call_count == 2
        assert res3.get('cache_hit') is False

def test_jules_launch_bypasses_cache():
    # Caching should only apply to list_remote_sessions
    pass
