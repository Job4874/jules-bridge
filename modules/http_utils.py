"""HTTP validation and routing helpers for Jules Bridge.

These helpers are used by bridge.py and route modules to validate
incoming JSON payloads and handle errors consistently.
"""
from __future__ import annotations

import errno
import logging
import os
import re
import subprocess
from functools import wraps
from flask import jsonify, request

LOGGER = logging.getLogger("jules_bridge")

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MISSING = object()

__all__ = [
    "CONTROL_CHAR_RE",
    "EMAIL_RE",
    "MISSING",
    "BridgeHTTPError",
    "route_errors",
    "json_payload",
    "string_field",
    "int_field",
    "bool_field",
    "string_list_field",
    "path_field",
    "content_field",
    "inbox_name_field",
]

class BridgeHTTPError(Exception):
    def __init__(self, status_code, error, **payload):
        super().__init__(error)
        self.status_code = status_code
        self.error = error
        self.payload = payload

def _json_error(status_code, error, **payload):
    body = {"error": error}
    body.update({k: v for k, v in payload.items() if v is not None})
    return jsonify(body), status_code

def route_errors(func):
    """Translate module exceptions into semantic JSON HTTP responses."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BridgeHTTPError as exc:
            LOGGER.warning("%s %s -> %s %s", request.method, request.path, exc.status_code, exc.error)
            return _json_error(exc.status_code, exc.error, **exc.payload)
        except subprocess.TimeoutExpired as exc:
            timeout = getattr(exc, "timeout", None)
            msg = f"Execution timed out after {timeout} seconds" if timeout else "Execution timed out"
            LOGGER.warning("%s %s -> 504 %s", request.method, request.path, msg)
            return _json_error(504, msg)
        # We can't easily import from modules here without circularity if we are in modules
        # but we can check the class name or handle it generically.
        except Exception as exc:
            exc_name = type(exc).__name__
            if exc_name in ("ShellNotAvailableError", "UnsupportedShellError"):
                LOGGER.warning("%s %s -> 400 %s", request.method, request.path, exc)
                return _json_error(400, "Invalid input", details=str(exc))

            if isinstance(exc, (IsADirectoryError, NotADirectoryError)):
                LOGGER.warning("%s %s -> 400 %s", request.method, request.path, exc)
                return _json_error(400, "Invalid input", details=str(exc))
            if isinstance(exc, FileNotFoundError):
                path = getattr(exc, "filename", None)
                LOGGER.warning("%s %s -> 404 %s", request.method, request.path, exc)
                return _json_error(404, "Resource not found", path=path)
            if isinstance(exc, PermissionError):
                LOGGER.warning("%s %s -> 403 %s", request.method, request.path, exc)
                return _json_error(403, "Access denied", reason="Insufficient permissions")
            if isinstance(exc, re.error):
                return _json_error(400, "Invalid input", details=f"Invalid regex: {exc}")
            if isinstance(exc, ValueError):
                LOGGER.warning("%s %s -> 400 %s", request.method, request.path, exc)
                return _json_error(400, "Invalid input", details=str(exc))
            if isinstance(exc, OSError):
                if getattr(exc, "errno", None) in (errno.EACCES, errno.EPERM, 13):
                    return _json_error(403, "Access denied", reason="Insufficient permissions")
                if getattr(exc, "errno", None) in (errno.ENOENT, 2, 3):
                    return _json_error(404, "Resource not found", path=getattr(exc, "filename", None))
                LOGGER.exception("%s %s -> 500 OSError", request.method, request.path)
                return _json_error(500, "Internal operational failure")

            LOGGER.exception("%s %s -> 500", request.method, request.path)
            return _json_error(500, "Internal operational failure")
    return wrapper

def json_payload():
    raw = request.get_data(cache=True)
    if not raw:
        return {}
    if not request.is_json:
        raise BridgeHTTPError(400, "Malformed JSON or missing Content-Type header.")
    data = request.get_json(silent=True)
    if data is None:
        raise BridgeHTTPError(400, "Malformed JSON or missing Content-Type header.")
    if not isinstance(data, dict):
        raise BridgeHTTPError(400, "Invalid input", details="JSON body must be an object.")
    return data

def string_field(data, key, default=MISSING, allow_empty=False, control_safe=False):
    if key not in data:
        if default is MISSING:
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} is required")
        return default
    value = data.get(key)
    if not isinstance(value, str):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a string")
    if not allow_empty and not value.strip():
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} cannot be empty")
    if control_safe and CONTROL_CHAR_RE.search(value):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} contains illegal control characters")
    return value

def int_field(data, key, default=MISSING, min_value=None, max_value=None):
    if key not in data or data.get(key) is None:
        if default is MISSING:
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} is required")
        return default
    value = data.get(key)
    if isinstance(value, bool):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be an integer")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be an integer") from None
    if min_value is not None and value < min_value:
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be <= {max_value}")
    return value

def bool_field(data, key, default=MISSING):
    if key not in data or data.get(key) is None:
        if default is MISSING:
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} is required")
        return default
    value = data.get(key)
    if not isinstance(value, bool):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a boolean")
    return value

def string_list_field(data, key, default=None, control_safe=False):
    if key not in data or data.get(key) is None:
        return list(default or [])
    value = data.get(key)
    if not isinstance(value, list):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a list of strings")
    items = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a list of non-empty strings")
        if control_safe and CONTROL_CHAR_RE.search(item):
            raise BridgeHTTPError(400, "Invalid input", details=f"{key} contains illegal control characters")
        items.append(item)
    return items

def path_field(data, key="path", default=MISSING):
    return string_field(data, key, default=default, control_safe=True)

def content_field(data):
    if "content" in data:
        return string_field(data, "content", allow_empty=True)
    if "data" in data:
        return string_field(data, "data", allow_empty=True)
    raise BridgeHTTPError(400, "Invalid input", details="content or data is required")

def inbox_name_field(data, default):
    if "file" not in data or data.get("file") in (None, ""):
        return default
    name = string_field(data, "file", control_safe=True)
    name = os.path.basename(name)
    if not name:
        raise BridgeHTTPError(400, "Invalid input", details="file cannot be empty")
    return name
