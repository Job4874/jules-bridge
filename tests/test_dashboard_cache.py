import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from modules.dashboard_module import get_dashboard_status

def test_dashboard_cache_logic(monkeypatch):
    # Mocking dependencies of get_dashboard_status to avoid real IO
    with patch('modules.dashboard_module._env_vars', return_value={}), \
         patch('modules.dashboard_module.detect_resource_pressure', return_value={}), \
         patch('modules.dashboard_module._fleet_status', return_value={}), \
         patch('modules.dashboard_module._vm_info', return_value={'vms': [], 'total': 0, 'online': 0}), \
         patch('modules.dashboard_module._tail_log', return_value=[]), \
         patch('modules.dashboard_module.test_chat_providers', return_value={'providers': {}}):

        monkeypatch.setenv('DASHBOARD_CACHE_TTL_S', '2')

        start_time = datetime.now(timezone.utc)

        # First call
        res1 = get_dashboard_status(start_time)
        assert res1['ok'] is True
        assert 'cache_age_s' in res1
        assert res1['cache_age_s'] == 0

        # Second call within TTL
        res2 = get_dashboard_status(start_time)
        assert res2['timestamp'] == res1['timestamp']
        assert res2['cache_age_s'] >= 0

        # Operator-triggered refreshes can bypass the cached dashboard snapshot.
        import time
        time.sleep(0.01)
        res_bypass = get_dashboard_status(start_time, bypass_cache=True)
        assert res_bypass['timestamp'] != res1['timestamp']
        assert res_bypass['cache_age_s'] == 0

        # Wait for TTL
        time.sleep(2.1)

        # Third call after TTL
        res3 = get_dashboard_status(start_time)
        assert res3['timestamp'] != res1['timestamp']
        assert res3['cache_age_s'] == 0
