"""Tests for the circuit breaker middleware."""

import os
from unittest.mock import patch
import pytest

from bridge import app
from modules import circuit_breaker


@pytest.fixture
def client():
    # Force enabled and specific defaults for tests
    os.environ["CIRCUIT_BREAKER_ENABLED"] = "1"
    os.environ["CIRCUIT_BREAKER_THRESHOLD"] = "3"
    os.environ["CIRCUIT_BREAKER_WINDOW_S"] = "60"
    circuit_breaker._call_log.clear()
    
    app.config["TESTING"] = True
    
    class AuthenticatedClient:
        def __init__(self, test_client):
            self.client = test_client
            
        def get(self, path):
            return self.client.get(path, headers={"Authorization": "Bearer testing"})

    with app.test_client() as client:
        yield AuthenticatedClient(client)
        
    os.environ.pop("CIRCUIT_BREAKER_ENABLED", None)
    os.environ.pop("CIRCUIT_BREAKER_THRESHOLD", None)
    os.environ.pop("CIRCUIT_BREAKER_WINDOW_S", None)
    circuit_breaker._call_log.clear()


def test_circuit_breaker_allows_under_threshold(client):
    # Route that does not exist will return 404, but not 429
    for _ in range(3):
        res = client.get("/does_not_exist")
        assert res.status_code == 404


def test_circuit_breaker_blocks_over_threshold(client):
    for _ in range(3):
        client.get("/test_route_1")
        
    # 4th call should be blocked
    res = client.get("/test_route_1")
    assert res.status_code == 429
    data = res.get_json()
    assert data["error"] == "circuit_open"
    assert data["route"] == "/test_route_1"
    assert "retry_after_s" in data


@patch("modules.circuit_breaker._get_time")
def test_circuit_breaker_resets_after_window(mock_time, client):
    mock_time.return_value = 1000.0
    
    for _ in range(3):
        client.get("/test_route_2")
        
    # Blocked
    res = client.get("/test_route_2")
    assert res.status_code == 429
    
    # Fast forward past window (60s default)
    mock_time.return_value = 1061.0
    
    # Should be allowed again
    res = client.get("/test_route_2")
    assert res.status_code == 404  # Not 429


def test_circuit_breaker_exempt_routes_have_higher_threshold(client):
    # Exempt route threshold is 200, so 3 calls should not block it
    for _ in range(4):
        res = client.get("/ping")
        assert res.status_code == 200  # Normal ping response
        
    # Override the environment variable to test the exempt threshold
    os.environ["CIRCUIT_BREAKER_THRESHOLD"] = "5"
    
    # Fill the normal limit
    for _ in range(10):
        client.get("/ping")
        
    # Exempt routes have a fixed higher threshold of 200 regardless of the standard threshold.
    res = client.get("/ping")
    assert res.status_code == 200


def test_circuit_breaker_can_be_disabled(client):
    os.environ["CIRCUIT_BREAKER_ENABLED"] = "0"
    
    for _ in range(5):
        res = client.get("/disabled_route")
        assert res.status_code == 404
