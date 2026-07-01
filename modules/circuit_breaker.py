"""Circuit breaker module to prevent request doom loops."""

import os
import time
from typing import Tuple

# In-memory store: route -> list of timestamps
_call_log: dict[str, list[float]] = {}


def _get_time() -> float:
    """Wrapper for time.time() to allow easy mocking in tests."""
    return time.time()


def check_circuit_breaker(route: str) -> Tuple[bool, int]:
    """
    Check if the given route has exceeded the rate limit threshold.
    Returns (is_open, retry_after_s).
    """
    enabled = os.environ.get("CIRCUIT_BREAKER_ENABLED", "1")
    if enabled == "0":
        return False, 0

    try:
        threshold = int(os.environ.get("CIRCUIT_BREAKER_THRESHOLD", "20"))
    except ValueError:
        threshold = 20

    try:
        window_s = int(os.environ.get("CIRCUIT_BREAKER_WINDOW_S", "60"))
    except ValueError:
        window_s = 60

    # Exempt routes have a higher fixed ceiling
    exempt_routes = {"/ping", "/health", "/dashboard/status"}
    if route in exempt_routes:
        threshold = 200

    now = _get_time()

    if route not in _call_log:
        _call_log[route] = []

    # Prune old timestamps
    cutoff = now - window_s
    _call_log[route] = [ts for ts in _call_log[route] if ts > cutoff]

    # Check threshold
    if len(_call_log[route]) >= threshold:
        # Circuit is open.
        # Calculate when the oldest request in the window expires.
        oldest_in_window = _call_log[route][0]
        retry_after = int((oldest_in_window + window_s) - now)
        if retry_after < 1:
            retry_after = 1
        return True, retry_after

    # Log the successful call
    _call_log[route].append(now)

    return False, 0


def circuit_breaker_hook():
    """Flask before_request hook. Returns a 429 response when the circuit is open."""
    from flask import jsonify, request  # pylint: disable=import-outside-toplevel

    route = request.path
    is_open, retry_after = check_circuit_breaker(route)
    if not is_open:
        return None

    response = jsonify(
        {
            "error": "circuit_open",
            "route": route,
            "retry_after_s": retry_after,
        }
    )
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response
