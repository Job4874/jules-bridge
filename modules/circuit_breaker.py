import os
import time
import logging
from flask import request, jsonify

LOGGER = logging.getLogger("jules_bridge")

# Tracks rolling call counts per route: { route_path: [timestamp1, timestamp2, ...] }
_route_calls = {}

def circuit_breaker_hook():
    """
    Circuit breaker pre-request hook for Flask.
    Tracks call frequency per route and returns 429 if threshold is exceeded.
    """
    enabled = os.environ.get('CIRCUIT_BREAKER_ENABLED', '1') == '1'
    if not enabled:
        return None

    route = request.path
    now = time.time()

    # Configuration
    threshold = int(os.environ.get('CIRCUIT_BREAKER_THRESHOLD', '20'))
    window_s = int(os.environ.get('CIRCUIT_BREAKER_WINDOW_S', '60'))

    # Exempt routes and routes with higher thresholds
    # GET /ping, GET /health, GET /dashboard/status allowed higher thresholds (200)
    if route in ('/ping', '/health', '/dashboard/status'):
        threshold = 200

    # Clean up old timestamps outside the window
    if route not in _route_calls:
        _route_calls[route] = []

    _route_calls[route] = [ts for ts in _route_calls[route] if now - ts < window_s]

    # Check threshold
    if len(_route_calls[route]) >= threshold:
        LOGGER.warning("Circuit breaker OPEN for route %s (count: %d)", route, len(_route_calls[route]))
        return jsonify({
            "error": "circuit_open",
            "route": route,
            "retry_after_s": window_s - (now - _route_calls[route][0]) if _route_calls[route] else window_s
        }), 429

    # Record this call
    _route_calls[route].append(now)
    return None
