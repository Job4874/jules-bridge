"""Jules God-Mode Bridge — thin HTTP routing layer.

This file contains ONLY:
  - Flask app setup and middleware
  - HTTP request validation (parsing JSON, field extraction)
  - Route handlers (validate → call module → return JSON)

All business logic lives in modules/:
  fs_service, shell_executor, ui_automation, inbox_service, oracle_session
"""

import errno
import logging
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler

from flask import Flask, g, jsonify, request
from flask_cors import CORS

import notify_email as email_service
import modules

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(ROOT_DIR, "jules_inbox")
LOG_PATH = os.path.join(ROOT_DIR, "bridge.log")
REQUEST_LOG: deque = deque(maxlen=200)


def configure_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if any(getattr(h, "_jules_bridge_handler", False) for h in root_logger.handlers):
        return
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    os.makedirs(ROOT_DIR, exist_ok=True)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=10_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(formatter)
    fh._jules_bridge_handler = True
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh._jules_bridge_handler = True
    root_logger.addHandler(fh)
    root_logger.addHandler(sh)


configure_logging()
LOGGER = logging.getLogger("jules_bridge")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Error handling infrastructure
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Request field helpers (validation only — no business logic)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.before_request
def _start_timer():
    g.request_start = datetime.now(timezone.utc)


@app.after_request
def _finalize_request(response):
    started = getattr(g, "request_start", None)
    elapsed_ms = 0.0
    if started is not None:
        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    entry = {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.path,
        "status": response.status_code,
        "remote": request.headers.get("X-Forwarded-For", request.remote_addr),
        "ms": elapsed_ms,
    }
    REQUEST_LOG.appendleft(entry)
    LOGGER.info("%s %s -> %s %.2fms remote=%s",
                entry["method"], entry["path"], entry["status"], entry["ms"], entry["remote"])
    return response

# ---------------------------------------------------------------------------
# Tentacle manifest
# ---------------------------------------------------------------------------

TENTACLES = [
    {"name": "pulse",        "route": "GET /ping",              "reach": "Confirm the bridge is alive"},
    {"name": "manifest",     "route": "GET /tentacles",          "reach": "List every tentacle (this endpoint)"},
    {"name": "session_log",  "route": "GET /session/log",        "reach": "Audit which tools Jules used recently"},
    {"name": "shell",        "route": "POST /shell",             "reach": "Run PowerShell, cmd.exe, or Git Bash on the host"},
    {"name": "read",         "route": "POST /fs/read",           "reach": "Read any file on the host (supports offset/limit)"},
    {"name": "write",        "route": "POST /fs/write",          "reach": "Write any file on the host"},
    {"name": "list",         "route": "POST /fs/list",           "reach": "List a directory like Codex file tree"},
    {"name": "tail",         "route": "POST /fs/tail",           "reach": "Tail log/CSV files"},
    {"name": "grep",         "route": "POST /fs/grep",           "reach": "Search file contents for gate/log strings"},
    {"name": "oracle_status","route": "GET /oracle/status",      "reach": "Structured Oracle/Quantower health + blockers"},
    {"name": "oracle_build", "route": "POST /oracle/build-deploy","reach": "Build + deploy + verify in one call"},
    {"name": "codex_handover","route": "GET /codex/handover",    "reach": "Index TIBIN Codex handover files on host"},
    {"name": "eyes",         "route": "GET /ui/screenshot",      "reach": "See the desktop (optional save to inbox/screenshots)"},
    {"name": "hand",         "route": "POST /ui/click",          "reach": "Click the mouse"},
    {"name": "voice",        "route": "POST /ui/type",           "reach": "Type on the keyboard"},
    {"name": "mail",         "route": "POST /notify/email",      "reach": "Email the operator (Gmail to iCloud)"},
    {"name": "inbox_read",   "route": "POST /inbox/read",        "reach": "Read operator/Jules inbox messages"},
    {"name": "inbox_write",  "route": "POST /inbox/write",       "reach": "Write Jules inbox replies"},
]

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "Jules Bridge Online"})


@app.route("/tentacles", methods=["GET"])
def tentacles():
    return jsonify({
        "creature": "Jules Bridge",
        "meaning": "One ngrok URL. Many tentacles. Each route extends reach to the host.",
        "access": "Possession of the bridge URL is possession of host access.",
        "codex_parity": "Use oracle/status + fs/* + ui/* - not shell-only.",
        "mandatory_read": "jules_inbox/JULES_TOOL_REQUIREMENTS.md",
        "tentacles": TENTACLES,
    })


@app.route("/session/log", methods=["GET"])
@route_errors
def session_log():
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        raise BridgeHTTPError(400, "Invalid input", details="limit must be an integer") from None
    if limit < 1:
        raise BridgeHTTPError(400, "Invalid input", details="limit must be >= 1")
    return jsonify({"entries": list(REQUEST_LOG)[:limit]})


# — Inbox routes —

@app.route("/inbox/read", methods=["POST"])
@route_errors
def inbox_read():
    data = json_payload()
    name = inbox_name_field(data, "OPERATOR_RESPONSE.md")
    message, status = modules.inbox_read(file=name)
    return jsonify(dict(message)), status


@app.route("/inbox/write", methods=["POST"])
@route_errors
def inbox_write():
    data = json_payload()
    name = inbox_name_field(data, "JULES_RESPONSE.md")
    content = content_field(data)
    result = modules.inbox_write(content=content, file=name)
    return jsonify(result)


# — Shell route —

@app.route("/shell", methods=["POST"])
@route_errors
def run_shell():
    data = json_payload()
    command = string_field(data, "command")
    shell_name = string_field(data, "shell", default="powershell")
    cwd = path_field(data, "cwd", default=os.getcwd())
    timeout = int_field(data, "timeout", default=30, min_value=1)
    stdin = string_field(data, "stdin", default=None, allow_empty=True)

    if cwd:
        existing_path(cwd, kind="directory")

    LOGGER.info("[JULES SHELL] shell=%s cwd=%s command=%s", shell_name, cwd, command)
    result = modules.execute(command, shell=shell_name, cwd=cwd, timeout=timeout, stdin=stdin)
    return jsonify(dict(result))


# — Filesystem routes —

@app.route("/fs/read", methods=["POST"])
@route_errors
def get_file_content():
    data = json_payload()
    path = existing_path(path_field(data), kind="file")
    offset = int_field(data, "offset", default=0, min_value=0)
    limit = int_field(data, "limit", default=None, min_value=0)
    result = modules.read(path, offset=offset, limit=limit)
    return jsonify(dict(result))


@app.route("/fs/list", methods=["POST"])
@route_errors
def list_directory():
    data = json_payload()
    path = existing_path(path_field(data, default=INBOX_DIR), kind="directory")
    entries = modules.list_dir(path)
    return jsonify({"path": path, "entries": [dict(e) for e in entries]})


@app.route("/fs/tail", methods=["POST"])
@route_errors
def tail_file():
    data = json_payload()
    path = existing_path(path_field(data), kind="file")
    lines = int_field(data, "lines", default=50, min_value=1)
    result = modules.tail(path, lines=lines)
    return jsonify(dict(result))


@app.route("/fs/grep", methods=["POST"])
@route_errors
def grep_file():
    data = json_payload()
    path = existing_path(path_field(data), kind="file")
    pattern = string_field(data, "pattern", default="", allow_empty=True)
    max_matches = int_field(data, "max_matches", default=50, min_value=1)
    result = modules.grep(path, pattern=pattern, max_matches=max_matches)
    return jsonify(dict(result))


@app.route("/fs/write", methods=["POST"])
@route_errors
def save_file_content():
    data = json_payload()
    path = path_field(data)
    content = content_field(data)
    result = modules.write(path, content)
    return jsonify({"status": "success", "path": result["path"]})


# — Oracle routes —

@app.route("/oracle/status", methods=["GET"])
@route_errors
def oracle_status():
    return jsonify(dict(modules.oracle_status()))


@app.route("/oracle/build-deploy", methods=["POST"])
@route_errors
def oracle_build_deploy():
    return jsonify(dict(modules.oracle_build_deploy()))


@app.route("/codex/handover", methods=["GET"])
@route_errors
def codex_handover():
    return jsonify(dict(modules.codex_handover_index()))


# — UI routes —

@app.route("/ui/screenshot", methods=["GET"])
@route_errors
def take_screenshot():
    save = request.args.get("save", "false").lower() in ("1", "true", "yes")
    result = modules.screenshot(save=save)
    return jsonify(dict(result))


@app.route("/ui/click", methods=["POST"])
@route_errors
def click_ui():
    data = json_payload()
    x = int_field(data, "x", min_value=0)
    y = int_field(data, "y", min_value=0)
    button = string_field(data, "button", default="left")
    result = modules.click(x, y, button=button)
    return jsonify(dict(result))


@app.route("/ui/type", methods=["POST"])
@route_errors
def type_text_route():
    data = json_payload()
    text = string_field(data, "text", allow_empty=True)
    result = modules.type_text(text)
    return jsonify(result)


# — Notify route —

@app.route("/notify/email", methods=["POST"])
@route_errors
def send_notify_email():
    data = json_payload()
    subject = string_field(data, "subject", default="Jules Bridge update")
    body = string_field(data, "body")
    mail_to = optional_email(data, "to")
    result = email_service.send_email(subject, body, mail_to=mail_to)
    return jsonify({"status": "sent", **result})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    LOGGER.info("========================================")
    LOGGER.info("JULES GOD-MODE BRIDGE ACTIVATED")
    LOGGER.info("Listening on 0.0.0.0:5000")
    LOGGER.info("Log path: %s", LOG_PATH)
    LOGGER.info("========================================")
    app.run(port=5000, host="0.0.0.0")
