"""Jules God-Mode Bridge — thin HTTP routing layer.

This file contains ONLY:
  - Flask app setup and middleware
  - HTTP request validation (parsing JSON, field extraction)
  - Route handlers (validate → call module → return JSON)

All business logic lives in modules/:
  fs_service, shell_executor, ui_automation, inbox_service, oracle_session
"""

import errno
import json
import logging
import os
import re
import subprocess
import sys
from typing import Any
from collections import deque
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler

from flask import Flask, g, jsonify, request
from flask_cors import CORS

import notify_email as email_service
from notify_email import load_env
import modules

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(ROOT_DIR, "jules_inbox")
LOG_PATH = os.path.join(ROOT_DIR, "bridge.log")
REQUEST_LOG: deque = deque(maxlen=200)
_BRIDGE_START_UTC = datetime.now(timezone.utc)  # set once at import time for uptime tracking


def configure_logging():
    """Attach rotating file + stdout handlers once per process."""
    if getattr(configure_logging, "configured", False):
        return
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    os.makedirs(ROOT_DIR, exist_ok=True)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=10_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    root_logger.addHandler(fh)
    root_logger.addHandler(sh)
    configure_logging.configured = True


configure_logging()
load_env()
LOGGER = logging.getLogger("jules_bridge")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)

BRIDGE_TOKEN = "JULES-SECURE-999"


@app.before_request
def require_auth():
    if request.path in ("/health", "/ping", "/dashboard/status", "/vm/status", "/chat", "/chat/test"):
        return None
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {BRIDGE_TOKEN}":
        LOGGER.warning("%s %s -> 401 unauthorized", request.method, request.path)
        return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401
    return None

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
        except Exception:  # pylint: disable=broad-exception-caught
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

# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.before_request
def _start_timer():
    g.request_start = datetime.now(timezone.utc)


def _stale_evidence_state():
    evidence_path = os.path.join(ROOT_DIR, "memory", "test_evidence.json")
    threshold_s = 3600
    try:
        with open(evidence_path, encoding="utf-8") as _f:
            ev = json.load(_f)
        if isinstance(ev, list):
            ev = ev[-1] if ev else {}
        if not isinstance(ev, dict):
            return None
        ts = ev.get("timestamp_utc", "")
        if not ts:
            return None
        age_s = round((datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds())
        if age_s <= threshold_s:
            return None
        return {"age_s": age_s, "threshold_s": threshold_s}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None  # evidence file missing or malformed — proceed without warning


@app.before_request
def _evidence_hard_gate():
    if not request.path.startswith("/oracle/"):
        return None
    if os.environ.get("EVIDENCE_GATE_HARD") != "1":
        return None
    stale = _stale_evidence_state()
    if not stale:
        return None
    return jsonify({
        "error": "evidence_stale",
        "age_s": stale["age_s"],
        "threshold_s": stale["threshold_s"],
    }), 423


@app.before_request
def _circuit_breaker_check():
    # pylint: disable=import-outside-toplevel
    from modules.circuit_breaker import check_circuit_breaker

    is_open, retry_after = check_circuit_breaker(request.path)
    if is_open:
        LOGGER.warning("Circuit breaker OPEN for %s", request.path)
        return jsonify({
            "error": "circuit_open",
            "route": request.path,
            "retry_after_s": retry_after
        }), 429

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


@app.after_request
def _evidence_age_check(response):
    """Attach stale-evidence warning headers on /oracle/* responses.

    Hard mode is enforced before the route runs by _evidence_hard_gate().
    """
    if not request.path.startswith("/oracle/"):
        return response
    stale = _stale_evidence_state()
    if stale:
        response.headers["X-Evidence-Age-Warning"] = f"stale:{stale['age_s']}s"
    return response


# ---------------------------------------------------------------------------
# Tentacle manifest
# ---------------------------------------------------------------------------

TENTACLES = [
    {"name": "root",         "route": "GET /",                  "reach": "Authenticated bridge discovery and next-step pointers"},  # pylint: disable=line-too-long
    {"name": "info",         "route": "GET /info",              "reach": "Authenticated bridge metadata without the full manifest"},  # pylint: disable=line-too-long
    {"name": "health",       "route": "GET /health",            "reach": "Liveness + uptime check for monitoring tools and ngrok"},  # pylint: disable=line-too-long
    {"name": "pulse",        "route": "GET /ping",              "reach": "Confirm the bridge is alive"},
    {"name": "manifest",     "route": "GET /tentacles",          "reach": "List every tentacle (this endpoint)"},
    {"name": "session_log",  "route": "GET /session/log",        "reach": "Audit which tools Jules used recently"},
    {"name": "shell",        "route": "POST /shell",             "reach": "Run PowerShell, cmd.exe, or Git Bash on the host"},  # pylint: disable=line-too-long
    {"name": "read",         "route": "POST /fs/read",           "reach": "Read any file on the host (supports offset/limit)"},  # pylint: disable=line-too-long
    {"name": "write",        "route": "POST /fs/write",          "reach": "Write any file on the host"},
    {"name": "list",         "route": "POST /fs/list",           "reach": "List a directory like Codex file tree"},
    {"name": "tail",         "route": "POST /fs/tail",           "reach": "Tail log/CSV files"},
    {"name": "grep",         "route": "POST /fs/grep",           "reach": "Search file contents for gate/log strings"},
    {"name": "oracle_status","route": "GET /oracle/status",      "reach": "Structured Oracle/Quantower health + blockers"},  # pylint: disable=line-too-long
    {"name": "oracle_build", "route": "POST /oracle/build-deploy","reach": "Build + deploy + verify in one call"},
    {"name": "codex_handover","route": "GET /codex/handover",    "reach": "Index TIBIN Codex handover files on host"},
    {"name": "eyes",         "route": "GET /ui/screenshot",      "reach": "See the desktop (optional save to inbox/screenshots)"},  # pylint: disable=line-too-long
    {"name": "operator",     "route": "POST /execute",           "reach": "Universal driver — click, type, and launch shell actions in one call"},  # pylint: disable=line-too-long
    {"name": "hand",         "route": "POST /ui/click",          "reach": "Click the mouse"},
    {"name": "voice",        "route": "POST /ui/type",           "reach": "Type on the keyboard"},
    {"name": "ui_quantower_driver", "route": "POST /ui/drive_quantower_login", "reach": "Run guarded H/L/ACT Quantower login driver"},  # pylint: disable=line-too-long
    {"name": "vm_pressure",       "route": "POST /vm/resource_pressure", "reach": "Detect CPU/memory pressure before local VM actions"},  # pylint: disable=line-too-long
    {"name": "vm_boot_secondary", "route": "POST /vm/boot_secondary",    "reach": "Dry-run-first allowlisted secondary VM boot script"},  # pylint: disable=line-too-long
    {"name": "app_browser",       "route": "POST /apps/launch_browser",      "reach": "Explicitly launch Edge to an approved http(s) URL"},  # pylint: disable=line-too-long
    {"name": "mail",            "route": "POST /notify/email",             "reach": "Email the operator (Gmail to iCloud)"},  # pylint: disable=line-too-long
    {"name": "inbox_read",      "route": "POST /inbox/read",               "reach": "Read operator/Jules inbox messages"},  # pylint: disable=line-too-long
    {"name": "inbox_write",     "route": "POST /inbox/write",              "reach": "Write Jules inbox replies"},
    {"name": "jules_dispatch",  "route": "POST /jules/dispatch",           "reach": "Parse Jules task dumps into worker packets and explicit launch commands"},  # pylint: disable=line-too-long
    {"name": "jules_launch",    "route": "POST /jules/launch",             "reach": "Launch prepared Jules worker packets when dry_run=false"},  # pylint: disable=line-too-long
    {"name": "jules_sessions",  "route": "POST /jules/sessions",           "reach": "List remote Jules sessions with timeout protection"},  # pylint: disable=line-too-long
    {"name": "jules_preflight", "route": "POST /jules/preflight",          "reach": "Diagnose Jules CLI install/auth/remote readiness without launching"},  # pylint: disable=line-too-long
    {"name": "jules_pull",      "route": "POST /jules/pull",               "reach": "Pull one remote Jules session with timeout protection"},  # pylint: disable=line-too-long
    {"name": "jules_cot",       "route": "POST /jules/cot",                "reach": "Build a completion-of-task ledger from Jules launch and pull artifacts"},  # pylint: disable=line-too-long
    {"name": "jules_cycle",     "route": "POST /jules/cycle",              "reach": "Run one dry-run-first Jules dispatch/launch/pull/COT communication cycle"},  # pylint: disable=line-too-long
    {"name": "jules_watch",     "route": "POST /jules/watch",              "reach": "Poll Jules sessions, pull completed results, and refresh COT until bounded stop"},  # pylint: disable=line-too-long
    {"name": "jules_fleet",     "route": "POST /jules/fleet",              "reach": "Scale Jules workers within max_concurrent and refresh pull/COT state"},  # pylint: disable=line-too-long
    {"name": "jules_fleet_watch", "route": "POST /jules/fleet-watch",      "reach": "Loop fleet scale-out, pull, and COT refresh until complete or timed out"},  # pylint: disable=line-too-long
    # Reasoning routes (HRM-inspired H/L/ACT)
    {"name": "reason_solve",    "route": "POST /reasoning/solve",          "reach": "Full H→L hierarchical reasoning with ACT halting"},  # pylint: disable=line-too-long
    {"name": "reason_plan",     "route": "POST /reasoning/plan",           "reach": "H module only — preview the abstract plan"},  # pylint: disable=line-too-long
    {"name": "reason_step",     "route": "POST /reasoning/execute_step",   "reach": "L module only — execute one plan step"},  # pylint: disable=line-too-long
    {"name": "reason_skills",   "route": "GET /reasoning/skills",          "reach": "Inventory of available agent skills"},  # pylint: disable=line-too-long
    {"name": "reason_gotcha",   "route": "POST /reasoning/inject_gotcha",  "reach": "Inject new edge case into gotchas context"},  # pylint: disable=line-too-long
    # Retrospective routes (self-improving memory)
    {"name": "retro_analyze",   "route": "POST /retrospective/analyze",    "reach": "Analyze bridge.log and write learnings to memory"},  # pylint: disable=line-too-long
    {"name": "retro_evidence",  "route": "POST /retrospective/record_evidence", "reach": "SHA-256 test output for cryptographic proof"},  # pylint: disable=line-too-long
    {"name": "retro_memory",    "route": "GET /retrospective/memory",      "reach": "Load accumulated memory for a domain"},  # pylint: disable=line-too-long
    {"name": "retro_prune",     "route": "POST /retrospective/prune_memory", "reach": "Age-based pruning of memory files"},  # pylint: disable=line-too-long
    {"name": "retro_quality",   "route": "GET /retrospective/memory_quality", "reach": "Assess memory structural quality"},  # pylint: disable=line-too-long
    # Agent Knowledge Context routes
    {"name": "akc_context",      "route": "GET /akc/context",               "reach": "Load the current Agent Knowledge Context checkpoint"},  # pylint: disable=line-too-long
    {"name": "akc_build",        "route": "POST /akc/context",              "reach": "Build source-backed AKC checkpoint from explicit transcript/context files"},  # pylint: disable=line-too-long
    {"name": "akc_readiness",    "route": "GET /akc/readiness",             "reach": "Verify AKC checkpoint readiness before session start"},  # pylint: disable=line-too-long
    {"name": "akc_subagents",    "route": "POST /akc/subagents",            "reach": "Build budgeted context capsules and sub-agent packets without launching workers"},  # pylint: disable=line-too-long
    # Dashboard + Chat routes
    {"name": "dashboard_status", "route": "GET /dashboard/status",           "reach": "Live dashboard metrics: CPU, memory, fleet, VMs, logs, env"},  # pylint: disable=line-too-long
    {"name": "chat",             "route": "POST /chat",                      "reach": "Multi-provider conversational endpoint (Gemini + OpenRouter fallback)"},  # pylint: disable=line-too-long
    {"name": "chat_test",        "route": "GET /chat/test",                  "reach": "Diagnostic: test each LLM provider and report status per provider"},  # pylint: disable=line-too-long
]

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def bridge_info_payload(include_routes=False):
    uptime_s = round(
        (datetime.now(timezone.utc) - _BRIDGE_START_UTC).total_seconds(), 1
    )
    payload = {
        "status": "ok",
        "bridge": "Jules Bridge",
        "uptime_s": uptime_s,
        "auth": {
            "type": "bearer",
            "public_routes": ["GET /health", "GET /ping"],
            "protected_routes": "All other routes require Authorization: Bearer <token>",
        },
        "manifest": "GET /tentacles",
        "session_log": "GET /session/log",
        "mandatory_read": "jules_inbox/JULES_TOOL_REQUIREMENTS.md",
        "route_count": len(TENTACLES),
    }
    if include_routes:
        payload["routes"] = TENTACLES
    return payload


@app.route("/", methods=["GET"])
@route_errors
def root_info():
    """GET / - Authenticated bridge discovery for browser/manual probes."""
    return jsonify(bridge_info_payload(include_routes=True))


@app.route("/info", methods=["GET"])
@route_errors
def bridge_info():
    """GET /info - Compact authenticated bridge metadata."""
    return jsonify(bridge_info_payload(include_routes=False))


@app.route("/health", methods=["GET"])
def health():
    """GET /health — Liveness + uptime check for monitoring tools and ngrok.

    Returns uptime since the bridge process started. This route stops
    monitoring tools (ngrok health checks, agents) from flooding the log
    with 404s when polling for bridge availability.
    """
    uptime_s = round(
        (datetime.now(timezone.utc) - _BRIDGE_START_UTC).total_seconds(), 1
    )
    return jsonify({
        "status": "ok",
        "bridge": "Jules Bridge",
        "uptime_s": uptime_s,
    })


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


# Jules dispatch route

@app.route("/jules/dispatch", methods=["POST"])
@route_errors
def jules_dispatch():
    """POST /jules/dispatch - Build dry-run Jules worker packets.

    Body (JSON):
        content/data       (str, optional): Raw pasted Jules task dump
        source_path/path   (str, optional): File path containing a task dump
        max_instances      (int, optional, default=4): Max packets to select
        include_statuses   (str|list, optional): Statuses to include
        write_packets      (bool, optional, default=false): Write packet files
        output_dir         (str, optional): Packet destination directory
        repo_path          (str, optional): Repo workers should launch from

    Returns a dispatch preview. It never launches remote Jules sessions.
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    result = modules.build_dispatch(
        content=content,
        source_path=source_path,
        max_instances=int_field(data, "max_instances", default=4, min_value=1, max_value=50),
        include_statuses=include_statuses,
        write_packets=bool_field(data, "write_packets", default=False),
        output_dir=string_field(data, "output_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/launch", methods=["POST"])
@route_errors
def jules_launch():
    """POST /jules/launch - Launch prepared Jules worker packets.

    Body (JSON):
        packet_dir    (str, optional): Directory containing JT-*.md packets
        packet_files  (list[str], optional): Explicit packet paths
        repo_path     (str, optional): Working directory for `jules new`
        limit         (int, optional, default=0): Max packets; 0 means all
        dry_run       (bool, optional, default=true): False starts sessions
        timeout_s     (int, optional, default=120): Per-packet timeout
        jules_command (str, optional, default="jules"): CLI path/name
        write_state   (bool, optional, default=true): Persist launch state JSON
        state_path    (str, optional): Explicit state file path
        skip_launched (bool, optional, default=false): Skip packets already launched in state
        force_packet_files (list[str], optional): Explicit packet paths to relaunch
        preserve_existing_session_ids (bool, optional, default=false): Keep older session ids on duplicate launches
    """
    data = json_payload()
    packet_files = data.get("packet_files")
    if packet_files is not None:
        if not isinstance(packet_files, list) or not all(isinstance(item, str) for item in packet_files):
            raise BridgeHTTPError(400, "Invalid input", details="packet_files must be a list of strings")
    force_packet_files = data.get("force_packet_files")
    if force_packet_files is not None:
        if not isinstance(force_packet_files, list) or not all(isinstance(item, str) for item in force_packet_files):
            raise BridgeHTTPError(400, "Invalid input", details="force_packet_files must be a list of strings")

    result = modules.launch_packets(
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        packet_files=packet_files,
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        limit=int_field(data, "limit", default=0, min_value=0, max_value=100),
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        write_state=bool_field(data, "write_state", default=True),
        state_path=string_field(data, "state_path", default="", allow_empty=True, control_safe=True),
        skip_launched=bool_field(data, "skip_launched", default=False),
        force_packet_files=force_packet_files,
        preserve_existing_session_ids=bool_field(data, "preserve_existing_session_ids", default=False),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/sessions", methods=["POST"])
@route_errors
def jules_sessions():
    """POST /jules/sessions - List remote Jules sessions.

    Body (JSON):
        dry_run       (bool, optional, default=true): False invokes the CLI
        timeout_s     (int, optional, default=30): CLI timeout
        jules_command (str, optional, default="jules"): CLI path/name
    """
    data = json_payload()
    result = modules.list_remote_sessions(
        jules_command=string_field(data, "jules_command", default="jules"),
        timeout_s=int_field(data, "timeout_s", default=30, min_value=1, max_value=300),
        dry_run=bool_field(data, "dry_run", default=True),
    )
    return jsonify(dict(result))


@app.route("/jules/preflight", methods=["POST"])
@route_errors
def jules_preflight_route():
    """POST /jules/preflight - Diagnose Jules CLI readiness.

    Body (JSON):
        jules_command (str, optional, default="jules"): CLI path/name
        timeout_s     (int, optional, default=8): Probe timeout
        check_remote  (bool, optional, default=true): Run remote list probe
        write_state   (bool, optional, default=true): Persist preflight JSON
        state_path    (str, optional): Explicit state file path
    """
    data = json_payload()
    result = modules.jules_preflight(
        jules_command=string_field(data, "jules_command", default="jules"),
        timeout_s=int_field(data, "timeout_s", default=8, min_value=1, max_value=300),
        check_remote=bool_field(data, "check_remote", default=True),
        write_state=bool_field(data, "write_state", default=True),
        state_path=string_field(data, "state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/pull", methods=["POST"])
@route_errors
def jules_pull():
    """POST /jules/pull - Pull one remote Jules session.

    Body (JSON):
        session_id    (str, required): Remote Jules session id
        repo_path     (str, optional): Working directory for pull
        output_dir    (str, optional): Directory for persisted pull JSON
        dry_run       (bool, optional, default=true): False invokes the CLI
        timeout_s     (int, optional, default=120): CLI timeout
        jules_command (str, optional, default="jules"): CLI path/name
        write_result  (bool, optional, default=true): Persist pull result JSON
    """
    data = json_payload()
    result = modules.pull_remote_session(
        session_id=string_field(data, "session_id"),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        output_dir=string_field(data, "output_dir", default="", allow_empty=True, control_safe=True),
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        write_result=bool_field(data, "write_result", default=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/cot", methods=["POST"])
@route_errors
def jules_cot():
    """POST /jules/cot - Build a completion-of-task ledger.

    Body (JSON):
        packet_dir         (str, optional): Dispatch packet directory
        launch_state_path  (str, optional): Explicit launch state JSON path
        report_dir         (str, optional): Completion report or pull JSON dir
        output_path        (str, optional): Markdown ledger destination
        write_ledger       (bool, optional, default=true): Persist ledger files
    """
    data = json_payload()
    result = modules.build_cot_ledger(
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        launch_state_path=string_field(data, "launch_state_path", default="", allow_empty=True, control_safe=True),
        report_dir=string_field(data, "report_dir", default="", allow_empty=True, control_safe=True),
        output_path=string_field(data, "output_path", default="", allow_empty=True, control_safe=True),
        write_ledger=bool_field(data, "write_ledger", default=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/cycle", methods=["POST"])
@route_errors
def jules_cycle():
    """POST /jules/cycle - Run one Jules communication cycle.

    Body (JSON):
        content/data          (str, optional): Raw pasted Jules task dump
        source_path/path      (str, optional): File path containing task dump
        packet_dir            (str, optional): Packet/state directory
        repo_path             (str, optional): Repo workers should launch from
        max_instances         (int, optional, default=4): Max packets
        include_statuses      (str|list, optional): Statuses to include
        launch                (bool, optional, default=false): Request launch
        launch_limit          (int, optional, default=0): Max launches
        pull                  (bool, optional, default=false): Pull session ids
        session_ids           (list[str], optional): Explicit session ids
        dry_run               (bool, optional, default=true): False enables live CLI
        check_remote          (bool, optional, default=true): Probe remote sessions
        require_remote_ready  (bool, optional, default=true): Gate live launch/pull
        timeout_s             (int, optional, default=120): CLI timeout
        jules_command         (str, optional, default="jules"): CLI path/name
        write_state           (bool, optional, default=true): Persist cycle JSON
        cycle_state_path      (str, optional): Explicit cycle state path
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    session_ids = data.get("session_ids")
    if session_ids is not None:
        if not isinstance(session_ids, list) or not all(isinstance(item, str) for item in session_ids):
            raise BridgeHTTPError(400, "Invalid input", details="session_ids must be a list of strings")

    result = modules.run_jules_cycle(
        content=content,
        source_path=source_path,
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_instances=int_field(data, "max_instances", default=4, min_value=1, max_value=50),
        include_statuses=include_statuses,
        write_packets=bool_field(data, "write_packets", default=True),
        launch=bool_field(data, "launch", default=False),
        launch_limit=int_field(data, "launch_limit", default=0, min_value=0, max_value=100),
        pull=bool_field(data, "pull", default=False),
        session_ids=session_ids,
        dry_run=bool_field(data, "dry_run", default=True),
        check_remote=bool_field(data, "check_remote", default=True),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        write_state=bool_field(data, "write_state", default=True),
        cycle_state_path=string_field(data, "cycle_state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/watch", methods=["POST"])
@route_errors
def jules_watch():
    """POST /jules/watch - Watch launched Jules sessions until COT progresses.

    Body (JSON):
        packet_dir            (str, optional): Packet/state directory
        repo_path             (str, optional): Repo workers launched from
        max_wait_s            (int, optional, default=300): Watch time budget
        poll_interval_s       (int, optional, default=30): Seconds between polls
        timeout_s             (int, optional, default=120): CLI timeout
        jules_command         (str, optional, default="jules"): CLI path/name
        dry_run               (bool, optional, default=true): False enables live pulls
        require_remote_ready  (bool, optional, default=true): Gate live pull
        write_state           (bool, optional, default=true): Persist watch JSON
        watch_state_path      (str, optional): Explicit watch state path
    """
    data = json_payload()
    result = modules.run_jules_watch(
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_wait_s=int_field(data, "max_wait_s", default=300, min_value=0, max_value=7200),
        poll_interval_s=int_field(data, "poll_interval_s", default=30, min_value=1, max_value=600),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        dry_run=bool_field(data, "dry_run", default=True),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        write_state=bool_field(data, "write_state", default=True),
        watch_state_path=string_field(data, "watch_state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/fleet", methods=["POST"])
@route_errors
def jules_fleet():
    """POST /jules/fleet - Maintain a bounded Jules worker fleet.

    Body (JSON):
        content/data          (str, optional): Raw pasted Jules task dump
        source_path/path      (str, optional): File path containing task dump
        packet_dir            (str, optional): Packet/state directory
        repo_path             (str, optional): Repo workers should launch from
        max_instances         (int, optional, default=12): Queue size to maintain
        max_concurrent        (int, optional, default=6): Max active remote sessions
        launch_batch_size     (int, optional, default=2): Max launches this cycle
        include_statuses      (str|list, optional): Statuses to include
        dry_run               (bool, optional, default=true): False enables live CLI
        timeout_s             (int, optional, default=120): CLI timeout
        jules_command         (str, optional, default="jules"): CLI path/name
        require_remote_ready  (bool, optional, default=true): Gate live launch/pull
        write_state           (bool, optional, default=true): Persist fleet JSON
        fleet_state_path      (str, optional): Explicit fleet state path
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    result = modules.run_jules_fleet(
        content=content,
        source_path=source_path,
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_instances=int_field(data, "max_instances", default=12, min_value=1, max_value=100),
        max_concurrent=int_field(data, "max_concurrent", default=6, min_value=0, max_value=50),
        launch_batch_size=int_field(data, "launch_batch_size", default=2, min_value=0, max_value=50),
        include_statuses=include_statuses,
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        write_state=bool_field(data, "write_state", default=True),
        fleet_state_path=string_field(data, "fleet_state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@app.route("/jules/fleet-watch", methods=["POST"])
@route_errors
def jules_fleet_watch():
    """POST /jules/fleet-watch - Scale, pull, and watch COT in one loop.

    Body (JSON):
        content/data             (str, optional): Raw pasted Jules task dump
        source_path/path         (str, optional): File path containing task dump
        packet_dir               (str, optional): Packet/state directory
        repo_path                (str, optional): Repo workers should launch from
        max_instances            (int, optional, default=12): Queue size to maintain
        max_concurrent           (int, optional, default=6): Max active remote sessions
        launch_batch_size        (int, optional, default=2): Max launches per loop
        include_statuses         (str|list, optional): Statuses to include
        max_wait_s               (int, optional, default=900): Watch time budget
        poll_interval_s          (int, optional, default=30): Seconds between loops
        dry_run                  (bool, optional, default=true): False enables live CLI
        timeout_s                (int, optional, default=120): CLI timeout
        jules_command            (str, optional, default="jules"): CLI path/name
        require_remote_ready     (bool, optional, default=true): Gate live launch/pull
        write_state              (bool, optional, default=true): Persist state JSON
        fleet_watch_state_path   (str, optional): Explicit state path
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    result = modules.run_jules_fleet_watch(
        content=content,
        source_path=source_path,
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_instances=int_field(data, "max_instances", default=12, min_value=1, max_value=100),
        max_concurrent=int_field(data, "max_concurrent", default=6, min_value=0, max_value=50),
        launch_batch_size=int_field(data, "launch_batch_size", default=2, min_value=0, max_value=50),
        include_statuses=include_statuses,
        max_wait_s=int_field(data, "max_wait_s", default=900, min_value=0, max_value=14400),
        poll_interval_s=int_field(data, "poll_interval_s", default=30, min_value=1, max_value=600),
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        write_state=bool_field(data, "write_state", default=True),
        fleet_watch_state_path=string_field(
            data,
            "fleet_watch_state_path",
            default="",
            allow_empty=True,
            control_safe=True,
        ),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


# Shell route

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


# — Universal operator route —

@app.route("/execute", methods=["POST"])
@route_errors
def execute_operator():
    """POST /execute — Run one or more host actions in a single request.

    Body (JSON), at least one field required:
        click (object): {x, y, button?} — mouse click via ui_automation
        type  (str): text to type at current focus
        text  (str): alias for type (matches /ui/type)
        shell (str): command to run; defaults to fire-and-forget spawn via cmd
        wait  (bool): when true with shell, block on /shell-style execute
        shell_name (str): shell selector for shell — cmd (default), powershell, bash
        cwd (str): working directory for shell actions
        timeout (int): seconds when wait=true
    """
    data = json_payload()
    has_click = "click" in data
    has_type = "type" in data or "text" in data
    has_shell = "shell" in data
    if not (has_click or has_type or has_shell):
        raise BridgeHTTPError(
            400,
            "Invalid input",
            details="At least one of click, type, text, or shell is required",
        )

    results = {"status": "executed", "actions": {}}

    if has_shell:
        command = string_field(data, "shell")
        shell_name = string_field(data, "shell_name", default="cmd")
        cwd = path_field(data, "cwd", default=os.getcwd())
        wait = bool_field(data, "wait", default=False)
        if cwd:
            existing_path(cwd, kind="directory")
        if wait:
            timeout = int_field(data, "timeout", default=30, min_value=1)
            LOGGER.info("[JULES EXECUTE] wait shell=%s cwd=%s command=%s", shell_name, cwd, command)
            shell_result = modules.execute(
                command,
                shell=shell_name,
                cwd=cwd,
                timeout=timeout,
            )
            results["actions"]["shell"] = dict(shell_result)
        else:
            LOGGER.info("[JULES EXECUTE] spawn shell=%s cwd=%s command=%s", shell_name, cwd, command)
            shell_result = modules.spawn(command, shell=shell_name, cwd=cwd)
            results["actions"]["shell"] = dict(shell_result)

    if has_click:
        click_data = data["click"]
        if not isinstance(click_data, dict):
            raise BridgeHTTPError(400, "Invalid input", details="click must be an object")
        x = int_field(click_data, "x", min_value=0)
        y = int_field(click_data, "y", min_value=0)
        button = string_field(click_data, "button", default="left")
        LOGGER.info("[JULES EXECUTE] click x=%s y=%s button=%s", x, y, button)
        results["actions"]["click"] = dict(modules.click(x, y, button=button))

    if has_type:
        if "type" in data:
            text = string_field(data, "type", allow_empty=True)
        else:
            text = string_field(data, "text", allow_empty=True)
        LOGGER.info("[JULES EXECUTE] type chars=%s", len(text))
        results["actions"]["type"] = modules.type_text(text)

    return jsonify(results)


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


@app.route("/ui/drive_quantower_login", methods=["POST"])
@route_errors
def drive_quantower_login_route():
    """POST /ui/drive_quantower_login — Run guarded Quantower login ACT loop.

    Body (JSON):
        ocr_text         (str, optional): OCR text from the current screen
        submit_x         (int, required): Submit button x-coordinate
        submit_y         (int, required): Submit button y-coordinate
        allow_secret_use (bool, optional): Runtime credential-use gate
        notify           (bool, optional): Send operator email on completion/failure

    Returns JSON with status, detected state, action flag, and message.
    """
    data = json_payload()
    ocr_text = string_field(data, "ocr_text", default="", allow_empty=True)
    submit_x = int_field(data, "submit_x", min_value=0)
    submit_y = int_field(data, "submit_y", min_value=0)
    allow_secret_use = bool_field(data, "allow_secret_use", default=False)
    notify = bool_field(data, "notify", default=False)

    def _send_completion_email(subject, body):
        return email_service.send_email(
            f"[Jules Bridge] {subject}",
            body,
        )

    notify_func = _send_completion_email if notify else None

    secret_provider = None
    if allow_secret_use:
        secret_provider = modules.build_windows_secret_provider()

    result = modules.drive_quantower_login(
        ocr_text=ocr_text,
        submit_x=submit_x,
        submit_y=submit_y,
        allow_secret_use=allow_secret_use,
        secret_provider=secret_provider,
        notify_func=notify_func,
    )
    return jsonify(dict(result))


# - VM routes -

@app.route("/vm/resource_pressure", methods=["POST"])
@route_errors
def vm_resource_pressure_route():
    """POST /vm/resource_pressure - Detect local CPU/memory pressure.

    Body (JSON):
        cpu_percent      (int, optional): Injected CPU percent
        memory_percent   (int, optional): Injected memory percent
        cpu_threshold    (int, optional): CPU pressure threshold, default 90
        memory_threshold (int, optional): Memory pressure threshold, default 90
    """
    data = json_payload()
    result = modules.detect_resource_pressure(
        cpu_percent=int_field(data, "cpu_percent", default=None, min_value=0, max_value=100),
        memory_percent=int_field(data, "memory_percent", default=None, min_value=0, max_value=100),
        thresholds={
            "cpu_percent": int_field(data, "cpu_threshold", default=90, min_value=1, max_value=100),
            "memory_percent": int_field(
                data,
                "memory_threshold",
                default=90,
                min_value=1,
                max_value=100,
            ),
        },
    )
    return jsonify(dict(result))


@app.route("/vm/boot_secondary", methods=["POST"])
@route_errors
def vm_boot_secondary_route():
    """POST /vm/boot_secondary - Dry-run-first secondary VM boot.

    Body (JSON):
        script_name    (str, required): Allowlisted script file name
        allow_vm_boot  (bool, optional): Required for real boot, default false
        dry_run        (bool, optional): Validate only, default true
    """
    data = json_payload()
    result = modules.boot_secondary_vm(
        string_field(data, "script_name", control_safe=True),
        allow_vm_boot=bool_field(data, "allow_vm_boot", default=False),
        dry_run=bool_field(data, "dry_run", default=True),
    )
    return jsonify(dict(result))


# - App launcher routes -

@app.route("/apps/launch_browser", methods=["POST"])
@route_errors
def launch_browser_route():
    """POST /apps/launch_browser — Launch Edge to an approved http(s) URL.

    Body (JSON):
        url (str, required): Target http:// or https:// URL
        allow_launch (bool, optional): Runtime launch gate (default false)
    """
    data = json_payload()
    url = string_field(data, "url")
    allow_launch = bool_field(data, "allow_launch", default=False)
    result = modules.launch_browser_to_url(url, allow_launch=allow_launch)
    return jsonify(dict(result))


# — Notify route —

@app.route("/notify/email", methods=["POST"])
@route_errors
def send_notify_email():
    """POST /notify/email - Email the operator, optionally with local attachments."""
    data = json_payload()
    subject = string_field(data, "subject", default="Jules Bridge update")
    body = string_field(data, "body")
    mail_to = optional_email(data, "to")
    attachments = [
        existing_path(path, kind="file")
        for path in string_list_field(data, "attachments", default=[], control_safe=True)
    ]
    result = email_service.send_email(subject, body, mail_to=mail_to, attachments=attachments)
    return jsonify({"status": "sent", **result})


# — Reasoning routes (HRM-inspired H/L/ACT) —

@app.route("/reasoning/solve", methods=["POST"])
@route_errors
def reasoning_solve():
    """POST /reasoning/solve — Run hierarchical H→L reasoning with ACT halting.

    Body (JSON):
        problem  (str, required): The problem to solve
        context  (str, optional): Additional context / background
        halt_budget (int, optional, default=8): Max L-module steps
        model    (str, optional, default="stub"): LLM model identifier

    Returns JSON with plan, actions, halt decision, answer, and feedback.
    """
    data = json_payload()
    problem = string_field(data, "problem")
    context = string_field(data, "context", default="")
    halt_budget = int_field(data, "halt_budget", default=8, min_value=1)
    model = string_field(data, "model", default="stub")

    trace = modules.reason(problem, context=context, halt_budget=halt_budget, model=model)

    return jsonify({
        "problem": trace.problem,
        "answer": trace.answer,
        "succeeded": trace.succeeded,
        "elapsed_ms": round(trace.elapsed_ms, 1),
        "plan": {
            "goal_statement": trace.plan.goal_statement,
            "steps": trace.plan.steps,
            "confidence": trace.plan.confidence,
            "model": trace.plan.model,
        },
        "actions": [
            {
                "step_index": a.step_index,
                "step_description": a.step_description,
                "action_type": a.action_type,
                "payload": a.payload,
                "confidence": a.confidence,
                "executed": a.should_execute,
            }
            for a in trace.actions
        ],
        "halt": {
            "reason": trace.halt.reason,
            "steps_used": trace.halt.steps_used,
            "steps_budget": trace.halt.steps_budget,
            "halted_early": trace.halt.halted_early,
        },
        "feedback": trace.feedback,
    })


@app.route("/reasoning/plan", methods=["POST"])
@route_errors
def reasoning_plan():
    """POST /reasoning/plan — Run only the H module, return the abstract plan.

    Use this to preview the plan before committing to full execution.

    Body (JSON):
        problem  (str, required): The problem to plan for
        context  (str, optional): Additional context
        model    (str, optional, default="stub"): LLM model identifier
    """
    data = json_payload()
    problem = string_field(data, "problem")
    context = string_field(data, "context", default="")
    model = string_field(data, "model", default="stub")

    plan = modules.plan_only(problem, context=context, model=model)

    return jsonify({
        "goal_statement": plan.goal_statement,
        "steps": plan.steps,
        "step_count": plan.step_count,
        "confidence": plan.confidence,
        "model": plan.model,
    })


@app.route("/reasoning/execute_step", methods=["POST"])
@route_errors
def reasoning_execute_step():
    """POST /reasoning/execute_step — Run only the L module for one step.

    Use for manual, step-by-step control of the execution.

    Body (JSON):
        step     (str, required): The step description to execute
        context  (str, optional): Additional context
        problem  (str, optional): Original problem for full context
        step_index (int, optional, default=0): Step index for logging
        model    (str, optional, default="stub"): LLM model identifier
    """
    data = json_payload()
    step = string_field(data, "step")
    context = string_field(data, "context", default="")
    problem = string_field(data, "problem", default="")
    step_index = int_field(data, "step_index", default=0, min_value=0)
    model = string_field(data, "model", default="stub")

    action = modules.execute_step(
        step, context=context, step_index=step_index, problem=problem, model=model
    )

    return jsonify({
        "step_index": action.step_index,
        "step_description": action.step_description,
        "action_type": action.action_type,
        "payload": action.payload,
        "confidence": action.confidence,
        "should_execute": action.should_execute,
    })



@app.route("/reasoning/skills", methods=["GET"])
@route_errors
def reasoning_skills():
    """GET /reasoning/skills — Inventory of available agent skills."""
    skills_dir = request.args.get("skills_dir", os.path.join(ROOT_DIR, ".agents", "skills"))
    skills = modules.reasoning_module.discover_skills(skills_dir)
    return jsonify({"skills": skills})


@app.route("/reasoning/inject_gotcha", methods=["POST"])
@route_errors
def reasoning_inject_gotcha():
    """POST /reasoning/inject_gotcha — Inject new edge case into gotchas context."""
    data = json_payload()
    module = string_field(data, "module")
    text = string_field(data, "text")
    result = modules.reasoning_module.inject_gotcha(module, text)
    return jsonify(result)


# — Retrospective routes (Nick Ni's "Case" harness pattern) —

@app.route("/retrospective/analyze", methods=["POST"])
@route_errors
def retrospective_analyze():
    """POST /retrospective/analyze — Analyze a session and write to memory.

    Reads bridge.log, detects doom loops and error patterns, extracts
    learnings, writes them to per-domain memory markdown files.

    Nick's principle: "Every failure is a harness bug."

    Body (JSON):
        log_path     (str, optional): Override path to bridge.log
        memory_path  (str, optional): Override path to memory/ dir
        session_id   (str, optional): Label for this session
        auto_prune   (bool, optional): Run prune_memory after analysis

    Returns JSON with patterns, doom_loops, learnings, memory_updates.
    """
    data = json_payload()
    log_path = string_field(data, "log_path", default=LOG_PATH)
    memory_path = string_field(data, "memory_path", default=os.path.join(ROOT_DIR, "memory"))
    session_id = string_field(data, "session_id", default="")
    auto_prune = bool_field(data, "auto_prune", default=False)

    report = modules.analyze_session(
        log_path=log_path,
        memory_path=memory_path,
        session_id=session_id or None,
        auto_prune=auto_prune,
    )

    return jsonify({
        "session_id": report.session_id,
        "analyzed_at_utc": report.analyzed_at_utc,
        "log_lines_analyzed": report.log_lines_analyzed,
        "patterns": [
            {
                "pattern_type": p.pattern_type,
                "description": p.description,
                "count": p.count,
                "examples": p.examples[:3],
            }
            for p in report.patterns
        ],
        "doom_loops": [
            {
                "tool_name": d.tool_name,
                "call_count": d.call_count,
                "consecutive": d.consecutive,
                "recommendation": d.recommendation,
            }
            for d in report.doom_loops
        ],
        "learnings": report.learnings,
        "memory_domains_updated": list(report.memory_updates.keys()),
        "has_doom_loops": report.has_doom_loops,
        "evidence": {
            "output_hash": report.evidence.output_hash,
            "timestamp_utc": report.evidence.timestamp_utc,
            "passed": report.evidence.passed,
            "test_count": report.evidence.test_count,
        } if report.evidence else None,
        "summary": report.to_summary(),
    })


@app.route("/retrospective/record_evidence", methods=["POST"])
@route_errors
def retrospective_record_evidence():
    """POST /retrospective/record_evidence — SHA-256 test output for cryptographic proof.

    Nick: "Take the test output and SHA-256 that and save that into the
    tested file, then verify cryptographically that you actually ran the tests."

    Body (JSON):
        test_output  (str, required): Full stdout of the test run
        memory_path  (str, optional): Where to store test_evidence.json
    """
    data = json_payload()
    test_output = string_field(data, "test_output")
    memory_path = string_field(data, "memory_path", default=os.path.join(ROOT_DIR, "memory"))

    evidence = modules.record_test_evidence(test_output, memory_path)

    return jsonify({
        "output_hash": evidence.output_hash,
        "timestamp_utc": evidence.timestamp_utc,
        "passed": evidence.passed,
        "test_count": evidence.test_count,
        "evidence_line": evidence.evidence_line,
        "verified": True,  # The existence of this hash IS the proof
    })


@app.route("/retrospective/memory", methods=["GET"])
@route_errors
def retrospective_memory():
    """GET /retrospective/memory?domain=general — Load memory for a domain.

    Returns the accumulated learnings markdown for a domain.
    Call this at the start of each session to load what the harness learned.

    Query params:
        domain  (str, optional, default="general"): general | oracle | quantower | trading | reasoning
        memory_path (str, optional): Override path to memory/ dir
    """
    domain = request.args.get("domain", "general")
    memory_path = request.args.get("memory_path", os.path.join(ROOT_DIR, "memory"))

    if domain not in ("general", "oracle", "quantower", "trading", "reasoning"):
        raise BridgeHTTPError(
            400,
            "Invalid input",
            details="domain must be one of: general, oracle, quantower, trading, reasoning",
        )

    memory_content = modules.load_memory(memory_path=memory_path, domain=domain)

    return jsonify({
        "domain": domain,
        "has_memory": bool(memory_content.strip()),
        "content": memory_content,
        "char_count": len(memory_content),
    })


@app.route("/retrospective/prune_memory", methods=["POST"])
@route_errors
def retrospective_prune_memory():
    """POST /retrospective/prune_memory — Age-based pruning of memory files.

    Removes learning sections older than max_age_days from all memory/*.md files.
    Sections with no parseable datestamp are kept (conservative default).
    Header sections (Initial Notes, How to use) are always preserved.

    Body (JSON):
        memory_path   (str, optional): Override path to memory/ dir
        max_age_days  (int, optional, default=30): Drop sections older than this

    Returns JSON with pruned_count and domains_affected.
    """
    data = json_payload()
    memory_path = string_field(data, "memory_path", default=os.path.join(ROOT_DIR, "memory"))
    max_age_days = int_field(data, "max_age_days", default=30, min_value=1)

    result = modules.prune_memory(memory_path=memory_path, max_age_days=max_age_days)

    return jsonify({
        "pruned_count": result["pruned_count"],
        "domains_affected": result["domains_affected"],
        "max_age_days": max_age_days,
    })



@app.route("/retrospective/memory_quality", methods=["GET"])
@route_errors
def retrospective_memory_quality():
    """GET /retrospective/memory_quality — Assess memory structural quality."""
    domain = request.args.get("domain", "general")
    memory_path = os.path.join(ROOT_DIR, "memory", f"{domain}.md")
    result = modules.retrospective_module.assess_memory_quality(memory_path)
    return jsonify(result)


# - AKC routes (Agent Knowledge Context) -

@app.route("/akc/context", methods=["GET"])
@route_errors
def akc_context_get():
    """GET /akc/context - Load the current Agent Knowledge Context checkpoint.

    Query params:
        checkpoint_path (str, optional): Override markdown checkpoint path
    """
    checkpoint_path = request.args.get(
        "checkpoint_path",
        os.path.join(ROOT_DIR, "context", "08_akc_context_checkpoint.md"),
    )
    if CONTROL_CHAR_RE.search(checkpoint_path):
        raise BridgeHTTPError(400, "Invalid input", details="checkpoint_path contains illegal control characters")

    result = modules.load_akc_checkpoint(checkpoint_path=checkpoint_path)
    return jsonify(dict(result))


@app.route("/akc/readiness", methods=["GET"])
@route_errors
def akc_readiness_get():
    """GET /akc/readiness - Check AKC readiness for session start.

    Query params:
        checkpoint_path (str, optional): Override markdown checkpoint path
    """
    checkpoint_path = request.args.get(
        "checkpoint_path",
        os.path.join(ROOT_DIR, "context", "08_akc_context_checkpoint.md"),
    )
    if CONTROL_CHAR_RE.search(checkpoint_path):
        raise BridgeHTTPError(400, "Invalid input", details="checkpoint_path contains illegal control characters")

    result = modules.check_akc_readiness(checkpoint_path=checkpoint_path)
    return jsonify(dict(result))


@app.route("/akc/context", methods=["POST"])
@route_errors
def akc_context_post():
    """POST /akc/context - Build a source-backed AKC checkpoint.

    Body (JSON):
        source_paths     (list[str], required): Transcript/context files to inventory
        checkpoint_path  (str, optional): Markdown checkpoint destination
    """
    data = json_payload()
    source_paths = data.get("source_paths", [])
    if source_paths is None:
        source_paths = []
    if not isinstance(source_paths, list):
        raise BridgeHTTPError(400, "Invalid input", details="source_paths must be a list of strings")
    if not source_paths:
        raise BridgeHTTPError(400, "Invalid input", details="source_paths must include at least one file")
    if any(not isinstance(path, str) or not path.strip() for path in source_paths):
        raise BridgeHTTPError(400, "Invalid input", details="source_paths must be a list of non-empty strings")
    if any(CONTROL_CHAR_RE.search(path) for path in source_paths):
        raise BridgeHTTPError(400, "Invalid input", details="source_paths contains illegal control characters")

    checkpoint_path = string_field(
        data,
        "checkpoint_path",
        default=os.path.join(ROOT_DIR, "context", "08_akc_context_checkpoint.md"),
        control_safe=True,
    )
    result = modules.build_akc_context(source_paths, checkpoint_path=checkpoint_path)
    return jsonify(dict(result))


@app.route("/akc/subagents", methods=["POST"])
@route_errors
def akc_subagents_post():
    """POST /akc/subagents - Build budgeted context sub-agent packets.

    Body (JSON):
        content / data    (str, optional): Inline source material
        source_paths      (list[str], optional): Source files to capsule
        task              (str, optional): Operator goal
        roles             (list[str], optional): Context role ids
        write_packets     (bool, optional, default=false): Write packet files

    Returns JSON with source capsules, role packets, and context metrics.
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_paths = string_list_field(data, "source_paths", default=[], control_safe=True)
    if not content and not source_paths:
        raise BridgeHTTPError(400, "Invalid input", details="content or source_paths is required")

    result = modules.build_context_subagents(
        content=content,
        source_paths=source_paths,
        task=string_field(data, "task", default="", allow_empty=True),
        roles=string_list_field(data, "roles", default=[]),
        head_chars=int_field(data, "head_chars", default=800, min_value=80, max_value=10000),
        tail_chars=int_field(data, "tail_chars", default=800, min_value=80, max_value=10000),
        max_packet_chars=int_field(data, "max_packet_chars", default=12000, min_value=1000, max_value=200000),
        context_window_chars=int_field(data, "context_window_chars", default=170000, min_value=1000),
        max_context_utilization=(
            int_field(data, "max_context_utilization_percent", default=40, min_value=1, max_value=100)
            / 100.0
        ),
        write_packets=bool_field(data, "write_packets", default=False),
        output_dir=string_field(data, "output_dir", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard/status", methods=["GET"])
@route_errors
def dashboard_status():
    """GET /dashboard/status — real-time multi-cloud mission control snapshot."""
    from modules.dashboard_module import get_dashboard_status  # pylint: disable=import-outside-toplevel
    result = get_dashboard_status(bridge_start_utc=_BRIDGE_START_UTC)
    return jsonify(result), 200 if result.get("ok") else 500


# ---------------------------------------------------------------------------
# VM Two-Way Relay — local bridge <-> jules-worker-agent on GCP VM
# ---------------------------------------------------------------------------

@app.route("/vm/bootstrap", methods=["POST"])
@route_errors
def vm_bootstrap():
    """POST /vm/bootstrap — install jules-worker-agent on the GCP VM."""
    from modules.vm_relay import bootstrap_vm  # pylint: disable=import-outside-toplevel
    result = bootstrap_vm()
    return jsonify(result), 200 if result.get("ok") else 500


@app.route("/vm/task", methods=["POST"])
@route_errors
def vm_task():
    """POST /vm/task — dispatch a task to the jules-worker-agent on the GCP VM.

    Body: {"task": "...", "task_type": "build|research|shell|chat", "context": "..."}
    """
    data = json_payload()
    task = string_field(data, "task")
    task_type = string_field(data, "task_type", default="build", allow_empty=False)
    context = string_field(data, "context", default="", allow_empty=True)
    from modules.vm_relay import send_task_to_vm  # pylint: disable=import-outside-toplevel
    result = send_task_to_vm(task=task, task_type=task_type, context=context)
    return jsonify(result), 200


@app.route("/vm/status", methods=["GET"])
@route_errors
def vm_relay_status():
    """GET /vm/status — get live status from the jules-worker-agent on the VM."""
    from modules.vm_relay import get_vm_status  # pylint: disable=import-outside-toplevel
    result = get_vm_status()
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Chat — multi-provider conversational endpoint + diagnostics
# ---------------------------------------------------------------------------

@app.route("/chat/test", methods=["GET"])
@route_errors
def chat_test():
    """GET /chat/test — probe each LLM provider with a minimal request.

    Returns per-provider status so operators can debug which keys work.
    """
    result = modules.test_chat_providers()
    return jsonify(dict(result)), 200

@app.route("/chat", methods=["POST"])
@route_errors
def chat() -> Any:
    """POST /chat — send a message (+ optional screenshot) to Jules.

    Body (JSON):
        message (str): user message
        image_base64 (str, optional): base64-encoded PNG/JPEG screenshot
        model (str, optional): "fast" | "smart" | "stub" (default: "fast")
        system (str, optional): override system prompt
        history (list, optional): prior turns [{"role": "user"|"assistant", "content": "..."}]
    """
    data = json_payload()
    LOGGER.debug("[CHAT] Processing payload with keys: %s", list(data.keys()))
    message = string_field(data, "message", allow_empty=False)
    model_alias = string_field(data, "model", default="fast", allow_empty=False)
    system_prompt = string_field(data, "system", default="", allow_empty=True)
    image_b64 = string_field(data, "image_base64", default="", allow_empty=True)
    history = data.get("history", [])

    result = modules.chat(
        message=message,
        model_alias=model_alias,
        system_prompt=system_prompt,
        image_base64=image_b64,
        history=history,
    )
    return jsonify(dict(result)), 200



# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    LOGGER.info("========================================")
    LOGGER.info("JULES GOD-MODE BRIDGE ACTIVATED")
    LOGGER.info("Listening on 0.0.0.0:5000")
    LOGGER.info("Log path: %s", LOG_PATH)
    LOGGER.info("Token auth: ENABLED (Bearer JULES-SECURE-999)")
    LOGGER.info("========================================")
    app.run(port=5000, host="0.0.0.0")
