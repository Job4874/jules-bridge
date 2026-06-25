"""Jules God-Mode Bridge - Flask API for remote host control via ngrok."""
import base64
import errno
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import shutil
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from functools import wraps

import pyautogui
from flask import Flask, g, jsonify, request
from flask_cors import CORS

import notify_email as email_service
import oracle_tools

# Safety switch: move mouse to a corner of the screen to kill runaway automation.
pyautogui.FAILSAFE = True

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(ROOT_DIR, "jules_inbox")
SCREENSHOT_DIR = os.path.join(INBOX_DIR, "screenshots")
LOG_PATH = os.path.join(ROOT_DIR, "bridge.log")

REQUEST_LOG = deque(maxlen=200)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MISSING = object()

SUPPORTED_SHELLS = ("powershell", "cmd", "bash")
BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
)


def configure_logging():
    """Send bridge logs to stdout and a rotating bridge.log file."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if any(getattr(handler, "_jules_bridge_handler", False) for handler in root_logger.handlers):
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    os.makedirs(ROOT_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=10_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._jules_bridge_handler = True

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler._jules_bridge_handler = True

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


configure_logging()
LOGGER = logging.getLogger("jules_bridge")

app = Flask(__name__)
CORS(app)


class BridgeHTTPError(Exception):
    """Exception that maps directly to a structured HTTP JSON response."""

    def __init__(self, status_code, error, **payload):
        super().__init__(error)
        self.status_code = status_code
        self.error = error
        self.payload = payload


def _json_error(status_code, error, **payload):
    body = {"error": error}
    for key, value in payload.items():
        if value is not None:
            body[key] = value
    return jsonify(body), status_code


def route_errors(func):
    """Translate expected operational failures into semantic JSON responses."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BridgeHTTPError as exc:
            LOGGER.warning("%s %s -> %s %s", request.method, request.path, exc.status_code, exc.error)
            return _json_error(exc.status_code, exc.error, **exc.payload)
        except subprocess.TimeoutExpired as exc:
            timeout = getattr(exc, "timeout", None)
            message = f"Execution timed out after {timeout} seconds" if timeout else "Execution timed out"
            LOGGER.warning("%s %s -> 504 %s", request.method, request.path, message)
            return _json_error(504, message)
        except FileNotFoundError as exc:
            path = getattr(exc, "filename", None)
            LOGGER.warning("%s %s -> 404 Resource not found: %s", request.method, request.path, path)
            return _json_error(404, "Resource not found", path=path)
        except PermissionError as exc:
            LOGGER.warning("%s %s -> 403 Access denied: %s", request.method, request.path, exc)
            return _json_error(403, "Access denied", reason="Insufficient permissions")
        except re.error as exc:
            LOGGER.warning("%s %s -> 400 Invalid regex: %s", request.method, request.path, exc)
            return _json_error(400, "Invalid input", details=f"Invalid regex: {exc}")
        except OSError as exc:
            if getattr(exc, "errno", None) in (errno.EACCES, errno.EPERM, 13):
                LOGGER.warning("%s %s -> 403 Access denied: %s", request.method, request.path, exc)
                return _json_error(403, "Access denied", reason="Insufficient permissions")
            if getattr(exc, "errno", None) in (errno.ENOENT, 2, 3):
                path = getattr(exc, "filename", None)
                LOGGER.warning("%s %s -> 404 Resource not found: %s", request.method, request.path, path)
                return _json_error(404, "Resource not found", path=path)
            LOGGER.exception("%s %s -> 500 OSError", request.method, request.path)
            return _json_error(500, "Internal operational failure")
        except Exception:
            LOGGER.exception("%s %s -> 500 Internal operational failure", request.method, request.path)
            return _json_error(500, "Internal operational failure")

    return wrapper


def json_payload():
    """Return a request JSON object without allowing Flask 415 surprises."""
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


def _reject_control_chars(value, field):
    if CONTROL_CHAR_RE.search(value):
        raise BridgeHTTPError(400, "Invalid input", details=f"{field} contains illegal control characters")


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
    if control_safe:
        _reject_control_chars(value, key)
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
    path = string_field(data, key, default=default, control_safe=True)
    if not isinstance(path, str):
        return path
    return path


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


def inbox_name(data, default):
    if "file" not in data or data.get("file") in (None, ""):
        return default
    name = string_field(data, "file", control_safe=True)
    name = os.path.basename(name)
    if not name:
        raise BridgeHTTPError(400, "Invalid input", details="file cannot be empty")
    return name


def validate_email(value, key="to"):
    if not EMAIL_RE.match(value):
        raise BridgeHTTPError(400, "Invalid input", details=f"{key} must be a valid email address")
    return value


def optional_email(data, key):
    if key not in data or data.get(key) in (None, ""):
        return None
    return validate_email(string_field(data, key), key=key)


def _coerce_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _discover_bash():
    configured = os.environ.get("JULES_BASH_PATH", "").strip()
    if configured:
        if os.path.exists(configured):
            return configured
        raise BridgeHTTPError(
            400,
            "Invalid input",
            details=f"JULES_BASH_PATH is set but not found: {configured}",
        )

    for candidate in BASH_CANDIDATES:
        if os.path.exists(candidate):
            return candidate

    for executable in ("bash.exe", "bash"):
        found = shutil.which(executable)
        if found:
            return found

    raise BridgeHTTPError(
        400,
        "Invalid input",
        details="bash shell is not installed or configured on this host",
        supported_shells=list(SUPPORTED_SHELLS),
    )


def shell_command_args(shell_name, command):
    shell_name = (shell_name or "powershell").strip().lower()
    if shell_name in ("ps", "powershell", "windows-powershell"):
        return "powershell", ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
    if shell_name == "cmd":
        return "cmd", ["cmd.exe", "/d", "/s", "/c", command]
    if shell_name == "bash":
        return "bash", [_discover_bash(), "-lc", command]
    if shell_name in ("wsl", "linux"):
        raise BridgeHTTPError(
            400,
            "Invalid input",
            details="WSL is not enabled for /shell because this host has no installed WSL distribution",
            supported_shells=list(SUPPORTED_SHELLS),
        )
    raise BridgeHTTPError(
        400,
        "Invalid input",
        details=f"Unsupported shell selector: {shell_name}",
        supported_shells=list(SUPPORTED_SHELLS),
    )


def validate_click_target(x, y):
    width, height = pyautogui.size()
    if x >= width or y >= height:
        raise BridgeHTTPError(
            400,
            "Invalid input",
            details=f"x/y must fit within the display bounds {width}x{height}",
        )


TENTACLES = [
    {"name": "pulse", "route": "GET /ping", "reach": "Confirm the bridge is alive"},
    {
        "name": "manifest",
        "route": "GET /tentacles",
        "reach": "List every tentacle (this endpoint)",
    },
    {
        "name": "session_log",
        "route": "GET /session/log",
        "reach": "Audit which tools Jules used recently",
    },
    {
        "name": "shell",
        "route": "POST /shell",
        "reach": "Run PowerShell, cmd.exe, or Git Bash on the host",
    },
    {
        "name": "read",
        "route": "POST /fs/read",
        "reach": "Read any file on the host (supports offset/limit)",
    },
    {"name": "write", "route": "POST /fs/write", "reach": "Write any file on the host"},
    {
        "name": "list",
        "route": "POST /fs/list",
        "reach": "List a directory like Codex file tree",
    },
    {"name": "tail", "route": "POST /fs/tail", "reach": "Tail log/CSV files"},
    {
        "name": "grep",
        "route": "POST /fs/grep",
        "reach": "Search file contents for gate/log strings",
    },
    {
        "name": "oracle_status",
        "route": "GET /oracle/status",
        "reach": "Structured Oracle/Quantower health + blockers",
    },
    {
        "name": "oracle_build",
        "route": "POST /oracle/build-deploy",
        "reach": "Build + deploy + verify in one call",
    },
    {
        "name": "codex_handover",
        "route": "GET /codex/handover",
        "reach": "Index TIBIN Codex handover files on host",
    },
    {
        "name": "eyes",
        "route": "GET /ui/screenshot",
        "reach": "See the desktop (optional save to inbox/screenshots)",
    },
    {"name": "hand", "route": "POST /ui/click", "reach": "Click the mouse"},
    {"name": "voice", "route": "POST /ui/type", "reach": "Type on the keyboard"},
    {
        "name": "mail",
        "route": "POST /notify/email",
        "reach": "Email the operator (Gmail to iCloud)",
    },
    {
        "name": "inbox_read",
        "route": "POST /inbox/read",
        "reach": "Read operator/Jules inbox messages",
    },
    {
        "name": "inbox_write",
        "route": "POST /inbox/write",
        "reach": "Write Jules inbox replies",
    },
]


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
    LOGGER.info(
        "%s %s -> %s %.2fms remote=%s",
        entry["method"],
        entry["path"],
        entry["status"],
        entry["ms"],
        entry["remote"],
    )
    return response


@app.route("/tentacles", methods=["GET"])
def tentacles():
    """Octopus manifest - each endpoint is a distinct reach into the host."""
    return jsonify(
        {
            "creature": "Jules Bridge",
            "meaning": "One ngrok URL. Many tentacles. Each route extends reach to the host.",
            "access": "Possession of the bridge URL is possession of host access.",
            "codex_parity": "Use oracle/status + fs/* + ui/* - not shell-only.",
            "mandatory_read": "jules_inbox/JULES_TOOL_REQUIREMENTS.md",
            "tentacles": TENTACLES,
        }
    )


@app.route("/session/log", methods=["GET"])
@route_errors
def session_log():
    """Return recent bridge requests for operator audit."""
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        raise BridgeHTTPError(400, "Invalid input", details="limit must be an integer") from None
    if limit < 1:
        raise BridgeHTTPError(400, "Invalid input", details="limit must be >= 1")
    return jsonify({"entries": list(REQUEST_LOG)[:limit]})


@app.route("/inbox/read", methods=["POST"])
@route_errors
def inbox_read():
    """Read a file from jules_inbox/ by filename."""
    data = json_payload()
    name = inbox_name(data, "OPERATOR_RESPONSE.md")
    path = os.path.join(INBOX_DIR, name)
    if not os.path.isfile(path):
        return jsonify(
            {
                "error": f"inbox file not found: {name}",
                "hint": "Playbooks and host paths use POST /fs/read with full path.",
                "inbox_files": sorted(
                    f for f in os.listdir(INBOX_DIR) if os.path.isfile(os.path.join(INBOX_DIR, f))
                ),
            }
        ), 404

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return jsonify({"file": name, "content": handle.read()})


@app.route("/inbox/write", methods=["POST"])
@route_errors
def inbox_write():
    """Write a file to jules_inbox/ by filename."""
    data = json_payload()
    name = inbox_name(data, "JULES_RESPONSE.md")
    content = content_field(data)
    path = os.path.join(INBOX_DIR, name)
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return jsonify({"status": "success", "file": name})


@app.route("/ping", methods=["GET"])
def ping():
    """Health check."""
    return jsonify({"status": "Jules Bridge Online"})


@app.route("/shell", methods=["POST"])
@route_errors
def run_shell():
    """Execute terminal commands through a selected native shell."""
    data = json_payload()
    command = string_field(data, "command")
    shell_name = string_field(data, "shell", default="powershell")
    cwd = path_field(data, "cwd", default=os.getcwd())
    timeout = int_field(data, "timeout", default=30, min_value=1)
    stdin = string_field(data, "stdin", default=None, allow_empty=True)
    shell_name, args = shell_command_args(shell_name, command)

    if cwd:
        existing_path(cwd, kind="directory")

    LOGGER.info("[JULES SHELL] shell=%s cwd=%s command=%s", shell_name, cwd, command)
    res = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        input=stdin,
        timeout=timeout,
        check=False,
    )
    return jsonify(
        {
            "stdout": _coerce_text(res.stdout),
            "stderr": _coerce_text(res.stderr),
            "code": res.returncode,
            "exit_code": res.returncode,
            "shell": shell_name,
        }
    )


@app.route("/oracle/status", methods=["GET"])
@route_errors
def oracle_status():
    """Return structured Oracle/Quantower health and blockers."""
    return jsonify(oracle_tools.oracle_status())


@app.route("/oracle/build-deploy", methods=["POST"])
@route_errors
def oracle_build_deploy():
    """Build, deploy, and verify Oracle strategy in one call."""
    return jsonify(oracle_tools.oracle_build_deploy())


@app.route("/codex/handover", methods=["GET"])
@route_errors
def codex_handover():
    """Index Codex handover files available on the host."""
    return jsonify(oracle_tools.codex_handover_index())


@app.route("/fs/read", methods=["POST"])
@route_errors
def get_file_content():
    """Read a local file, optionally by line offset/limit."""
    data = json_payload()
    path = existing_path(path_field(data), kind="file")
    offset = int_field(data, "offset", default=0, min_value=0)
    limit = int_field(data, "limit", default=None, min_value=0)
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        if limit is None:
            content = handle.read()
        else:
            lines = handle.readlines()
            content = "".join(lines[offset : offset + limit])
    return jsonify({"path": path, "offset": offset, "content": content, "data": content})


@app.route("/fs/list", methods=["POST"])
@route_errors
def list_directory():
    """List files and folders under a path."""
    data = json_payload()
    path = existing_path(path_field(data, default=INBOX_DIR), kind="directory")
    entries = []
    for name in os.listdir(path):
        full = os.path.join(path, name)
        entries.append(
            {
                "name": name,
                "path": full,
                "is_dir": os.path.isdir(full),
                "size": os.path.getsize(full) if os.path.isfile(full) else None,
            }
        )
    entries.sort(key=lambda item: (not item["is_dir"], item["name"].lower()))
    return jsonify({"path": path, "entries": entries})


@app.route("/fs/tail", methods=["POST"])
@route_errors
def tail_file():
    """Return the last N lines of a file."""
    data = json_payload()
    path = existing_path(path_field(data), kind="file")
    lines = int_field(data, "lines", default=50, min_value=1)
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.readlines()
    tail = content[-lines:]
    content = "".join(tail)
    return jsonify({"path": path, "lines": len(tail), "content": content, "data": content})


@app.route("/fs/grep", methods=["POST"])
@route_errors
def grep_file():
    """Search a file for a regex pattern."""
    data = json_payload()
    path = existing_path(path_field(data), kind="file")
    pattern = string_field(data, "pattern", default="", allow_empty=True)
    max_matches = int_field(data, "max_matches", default=50, min_value=1)
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            if regex.search(line):
                matches.append({"line": line_no, "text": line.rstrip()})
                if len(matches) >= max_matches:
                    break
    return jsonify({"path": path, "pattern": pattern, "matches": matches})


@app.route("/fs/write", methods=["POST"])
@route_errors
def save_file_content():
    """Write content to a local file."""
    data = json_payload()
    path = path_field(data)
    content = content_field(data)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return jsonify({"status": "success", "path": path})


@app.route("/ui/screenshot", methods=["GET"])
@route_errors
def take_screenshot():
    """Capture the desktop and return a base64 PNG."""
    save = request.args.get("save", "false").lower() in ("1", "true", "yes")
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"screen_{stamp}.png")
    pyautogui.screenshot(path)
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    payload = {"image_base64": encoded_string}
    if save:
        payload["saved_path"] = path
    else:
        os.remove(path)
    return jsonify(payload)


@app.route("/ui/click", methods=["POST"])
@route_errors
def click_ui():
    """Move the mouse and click."""
    data = json_payload()
    x = int_field(data, "x", min_value=0)
    y = int_field(data, "y", min_value=0)
    button = string_field(data, "button", default="left")
    if button not in ("left", "right", "middle"):
        raise BridgeHTTPError(400, "Invalid input", details="button must be left, right, or middle")
    validate_click_target(x, y)
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click(button=button)
    return jsonify({"status": f"Clicked {x}, {y}"})


@app.route("/ui/type", methods=["POST"])
@route_errors
def type_text():
    """Type text on the keyboard."""
    data = json_payload()
    text = string_field(data, "text", allow_empty=True)
    pyautogui.write(text, interval=0.01)
    return jsonify({"status": "Typed successfully"})


@app.route("/notify/email", methods=["POST"])
@route_errors
def send_notify_email():
    """Send email from Gmail to operator iCloud (see .env)."""
    data = json_payload()
    subject = string_field(data, "subject", default="Jules Bridge update")
    body = string_field(data, "body")
    mail_to = optional_email(data, "to")
    result = email_service.send_email(subject, body, mail_to=mail_to)
    return jsonify({"status": "sent", **result})


if __name__ == "__main__":
    LOGGER.info("========================================")
    LOGGER.info("JULES GOD-MODE BRIDGE ACTIVATED")
    LOGGER.info("Listening on 0.0.0.0:5000")
    LOGGER.info("Log path: %s", LOG_PATH)
    LOGGER.info("========================================")
    app.run(port=5000, host="0.0.0.0")
