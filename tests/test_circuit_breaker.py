import pytest
import time
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from modules.circuit_breaker import circuit_breaker_hook

@pytest.fixture
def app():
    from modules.circuit_breaker import _route_calls
    _route_calls.clear()
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    @app.before_request
    def before_request():
        return circuit_breaker_hook()

    @app.route('/test')
    def test_route():
        return jsonify({"ok": True})

    @app.route('/health')
    def health_route():
        return jsonify({"ok": True})

    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_circuit_breaker_threshold(client, monkeypatch):
    monkeypatch.setenv('CIRCUIT_BREAKER_THRESHOLD', '3')
    monkeypatch.setenv('CIRCUIT_BREAKER_WINDOW_S', '60')
    monkeypatch.setenv('CIRCUIT_BREAKER_ENABLED', '1')
    
    # First 3 calls should succeed
    for _ in range(3):
        res = client.get('/test')
        assert res.status_code == 200
    
    # 4th call should fail with 429
    res = client.get('/test')
    assert res.status_code == 429
    assert res.json['error'] == 'circuit_open'

def test_circuit_breaker_exempt_route(client, monkeypatch):
    monkeypatch.setenv('CIRCUIT_BREAKER_THRESHOLD', '3')
    monkeypatch.setenv('CIRCUIT_BREAKER_ENABLED', '1')
    
    # /health is exempt and has higher threshold (default 200, but let's just test it exceeds 3)
    for _ in range(5):
        res = client.get('/health')
        assert res.status_code == 200

def test_circuit_breaker_disabled(client, monkeypatch):
    monkeypatch.setenv('CIRCUIT_BREAKER_THRESHOLD', '3')
    monkeypatch.setenv('CIRCUIT_BREAKER_ENABLED', '0')
    
    for _ in range(5):
        res = client.get('/test')
        assert res.status_code == 200

def test_circuit_breaker_window_reset(client, monkeypatch):
    monkeypatch.setenv('CIRCUIT_BREAKER_THRESHOLD', '1')
    monkeypatch.setenv('CIRCUIT_BREAKER_WINDOW_S', '1')
    monkeypatch.setenv('CIRCUIT_BREAKER_ENABLED', '1')
    
    assert client.get('/test').status_code == 200
    assert client.get('/test').status_code == 429
    
    time.sleep(1.1)
    
    assert client.get('/test').status_code == 200
