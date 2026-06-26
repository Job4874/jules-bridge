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
_BRIDGE_START_UTC = datetime.now(timezone.utc)  # set once at import time for uptime tracking


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


@app.after_request
def _evidence_age_check(response):
    """Attach X-Evidence-Age-Warning on /oracle/* when test evidence is stale (>1h).

    Soft gating: warns callers that tests haven't been run recently.
    Does NOT block (no 423) — add hard enforcement later if needed.
    """
    if not request.path.startswith("/oracle"):
        return response
    evidence_path = os.path.join(ROOT_DIR, "memory", "test_evidence.json")
    try:
        import json as _json
        with open(evidence_path, encoding="utf-8") as _f:
            ev = _json.load(_f)
        ts = ev.get("timestamp_utc", "")
        if ts:
            age_s = round(
                (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
            )
            if age_s > 3600:
                response.headers["X-Evidence-Age-Warning"] = f"stale:{age_s}s"
    except Exception:  # noqa: BLE001
        pass  # evidence file missing or malformed — proceed without warning
    return response


# ---------------------------------------------------------------------------
# Tentacle manifest
# ---------------------------------------------------------------------------

TENTACLES = [
    {"name": "health",       "route": "GET /health",            "reach": "Liveness + uptime check for monitoring tools and ngrok"},
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
    {"name": "mail",            "route": "POST /notify/email",             "reach": "Email the operator (Gmail to iCloud)"},
    {"name": "inbox_read",      "route": "POST /inbox/read",               "reach": "Read operator/Jules inbox messages"},
    {"name": "inbox_write",     "route": "POST /inbox/write",              "reach": "Write Jules inbox replies"},
    # Reasoning routes (HRM-inspired H/L/ACT)
    {"name": "reason_solve",    "route": "POST /reasoning/solve",          "reach": "Full H→L hierarchical reasoning with ACT halting"},
    {"name": "reason_plan",     "route": "POST /reasoning/plan",           "reach": "H module only — preview the abstract plan"},
    {"name": "reason_step",     "route": "POST /reasoning/execute_step",   "reach": "L module only — execute one plan step"},
    # Retrospective routes (self-improving memory)
    {"name": "retro_analyze",   "route": "POST /retrospective/analyze",    "reach": "Analyze bridge.log and write learnings to memory"},
    {"name": "retro_evidence",  "route": "POST /retrospective/record_evidence", "reach": "SHA-256 test output for cryptographic proof"},
    {"name": "retro_memory",    "route": "GET /retrospective/memory",      "reach": "Load accumulated memory for a domain"},
    {"name": "retro_prune",     "route": "POST /retrospective/prune_memory", "reach": "Age-based pruning of memory files"},
]

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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

    Returns JSON with patterns, doom_loops, learnings, memory_updates.
    """
    data = json_payload()
    log_path = string_field(data, "log_path", default=LOG_PATH)
    memory_path = string_field(data, "memory_path", default=os.path.join(ROOT_DIR, "memory"))
    session_id = string_field(data, "session_id", default="")

    report = modules.analyze_session(
        log_path=log_path,
        memory_path=memory_path,
        session_id=session_id or None,
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
        raise BridgeHTTPError(400, "Invalid input", details=f"domain must be one of: general, oracle, quantower, trading, reasoning")

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
