import errno
import logging
import os
import re
import subprocess
from functools import wraps
from flask import jsonify, request
import modules

LOGGER = logging.getLogger("jules_bridge.infra.http")

CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MISSING = object()

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
        except (modules.ShellNotAvailableError, modules.UnsupportedShellError) as exc:
            LOGGER.warning("%s %s -> 400 %s", request.method, request.path, exc)
            return _json_error(400, "Invalid input", details=str(exc))
        except (IsADirectoryError, NotADirectoryError) as exc:
            LOGGER.warning("%s %s -> 400 %s", request.method, request.path, exc)
            return _json_error(400, "Invalid input", details=str(exc))
        except FileNotFoundError as exc:
            path = getattr(exc, "filename", None)
            LOGGER.warning("%s %s -> 404 %s", request.method, request.path, exc)
            return _json_error(404, "Resource not found", path=path)
        except PermissionError as exc:
            LOGGER.warning("%s %s -> 403 %s", request.method, request.path, exc)
            return _json_error(403, "Access denied", reason="Insufficient permissions")
        except re.error as exc:
            return _json_error(400, "Invalid input", details=f"Invalid regex: {exc}")
        except ValueError as exc:
            LOGGER.warning("%s %s -> 400 %s", request.method, request.path, exc)
            return _json_error(400, "Invalid input", details=str(exc))
        except OSError as exc:
            if getattr(exc, "errno", None) in (errno.EACCES, errno.EPERM, 13):
                return _json_error(403, "Access denied", reason="Insufficient permissions")
            if getattr(exc, "errno", None) in (errno.ENOENT, 2, 3):
                return _json_error(404, "Resource not found", path=getattr(exc, "filename", None))
            LOGGER.exception("%s %s -> 500 OSError", request.method, request.path)
            return _json_error(500, "Internal operational failure")
        except Exception:
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

def existing_path(path, kind="file"):
    if not os.path.exists(path):
        raise BridgeHTTPError(404, "Resource not found", path=path)
    if kind == "file" and not os.path.isfile(path):
        raise BridgeHTTPError(400, "Invalid input", details="path must point to a file", path=path)
    if kind == "directory" and not os.path.isdir(path):
        raise BridgeHTTPError(400, "Invalid input", details="path must point to a directory", path=path)
    return path

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

def optional_email(data, key):
    if key not in data or data.get(key) in (None, ""):
        return None
    val = string_field(data, key)
    if not EMAIL_RE.match(val):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a valid email address")
    return val
