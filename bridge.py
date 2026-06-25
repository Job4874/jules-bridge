import os
import re
import subprocess
import base64
from collections import deque
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import pyautogui

import oracle_tools

# Safety switch: Move mouse to a corner of the screen to kill the automation if it goes crazy
pyautogui.FAILSAFE = True 

app = Flask(__name__)
CORS(app)

INBOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jules_inbox")
SCREENSHOT_DIR = os.path.join(INBOX_DIR, "screenshots")
REQUEST_LOG = deque(maxlen=200)

TENTACLES = [
    {"name": "pulse", "route": "GET /ping", "reach": "Confirm the bridge is alive"},
    {"name": "manifest", "route": "GET /tentacles", "reach": "List every tentacle (this endpoint)"},
    {"name": "session_log", "route": "GET /session/log", "reach": "Audit which tools Jules used recently"},
    {"name": "shell", "route": "POST /shell", "reach": "Run PowerShell on the host"},
    {"name": "read", "route": "POST /fs/read", "reach": "Read any file on the host (supports offset/limit)"},
    {"name": "write", "route": "POST /fs/write", "reach": "Write any file on the host"},
    {"name": "list", "route": "POST /fs/list", "reach": "List a directory like Codex file tree"},
    {"name": "tail", "route": "POST /fs/tail", "reach": "Tail log/CSV files"},
    {"name": "grep", "route": "POST /fs/grep", "reach": "Search file contents for gate/log strings"},
    {"name": "oracle_status", "route": "GET /oracle/status", "reach": "Structured Oracle/Quantower health + blockers"},
    {"name": "oracle_build", "route": "POST /oracle/build-deploy", "reach": "Build + deploy + verify in one call"},
    {"name": "codex_handover", "route": "GET /codex/handover", "reach": "Index TIBIN Codex handover files on host"},
    {"name": "eyes", "route": "GET /ui/screenshot", "reach": "See the desktop (optional save to inbox/screenshots)"},
    {"name": "hand", "route": "POST /ui/click", "reach": "Click the mouse"},
    {"name": "voice", "route": "POST /ui/type", "reach": "Type on the keyboard"},
    {"name": "mail", "route": "POST /notify/email", "reach": "Email the operator (Gmail to iCloud)"},
    {"name": "inbox_read", "route": "POST /inbox/read", "reach": "Read operator/Jules inbox messages"},
    {"name": "inbox_write", "route": "POST /inbox/write", "reach": "Write Jules inbox replies"},
]


@app.after_request
def _log_request(response):
    REQUEST_LOG.appendleft(
        {
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "remote": request.headers.get("X-Forwarded-For", request.remote_addr),
            "ms": float(response.headers.get("X-Response-Time-Ms", 0) or 0),
        }
    )
    return response


@app.before_request
def _start_timer():
    request._start_time = datetime.now(timezone.utc)


@app.after_request
def _add_timing_header(response):
    started = getattr(request, "_start_time", None)
    if started is not None:
        delta = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        response.headers["X-Response-Time-Ms"] = str(round(delta, 2))
    return response

@app.route('/tentacles', methods=['GET'])
def tentacles():
    """Octopus manifest — each endpoint is a tentacle: far reach through one URL."""
    return jsonify({
        "creature": "Jules Bridge",
        "meaning": "One ngrok URL. Many tentacles. Each route extends reach to the host.",
        "access": "Possession of the bridge URL is possession of host access.",
        "codex_parity": "Use oracle/status + fs/* + ui/* — not shell-only.",
        "mandatory_read": "jules_inbox/JULES_TOOL_REQUIREMENTS.md",
        "tentacles": TENTACLES,
    })


@app.route('/session/log', methods=['GET'])
def session_log():
    limit = int(request.args.get("limit", 50))
    return jsonify({"entries": list(REQUEST_LOG)[:limit]})

@app.route('/inbox/read', methods=['POST'])
def inbox_read():
    """Read a file from jules_inbox/ by filename."""
    name = (request.json or {}).get("file", "OPERATOR_RESPONSE.md")
    path = os.path.join(INBOX_DIR, os.path.basename(name))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return jsonify({"file": name, "content": f.read()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/inbox/write', methods=['POST'])
def inbox_write():
    """Write a file to jules_inbox/ by filename."""
    data = request.json or {}
    name = os.path.basename(data.get("file", "JULES_RESPONSE.md"))
    content = data.get("content", "")
    path = os.path.join(INBOX_DIR, name)
    try:
        os.makedirs(INBOX_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "success", "file": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "Jules Bridge Online"})

@app.route('/shell', methods=['POST'])
def run_shell():
    """Executes terminal commands (Powershell by default)"""
    data = request.json or {}
    cmd = data.get('command')
    cwd = data.get('cwd', os.getcwd())
    timeout = int(data.get('timeout', 120))
    print(f"[JULES SHELL] -> {cmd}")
    try:
        res = subprocess.run(
            ["powershell", "-Command", cmd],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return jsonify({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/oracle/status', methods=['GET'])
def oracle_status():
    try:
        return jsonify(oracle_tools.oracle_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/oracle/build-deploy', methods=['POST'])
def oracle_build_deploy():
    try:
        return jsonify(oracle_tools.oracle_build_deploy())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/codex/handover', methods=['GET'])
def codex_handover():
    try:
        return jsonify(oracle_tools.codex_handover_index())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/fs/read', methods=['POST'])
def get_file_content():
    """Reads local files"""
    data = request.json or {}
    path = data.get('path')
    offset = int(data.get('offset', 0))
    limit = data.get('limit')
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            if limit is None:
                content = f.read()
            else:
                lines = f.readlines()
                content = ''.join(lines[offset: offset + int(limit)])
        return jsonify({"path": path, "offset": offset, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/fs/list', methods=['POST'])
def list_directory():
    data = request.json or {}
    path = data.get('path', INBOX_DIR)
    try:
        entries = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            entries.append({
                "name": name,
                "path": full,
                "is_dir": os.path.isdir(full),
                "size": os.path.getsize(full) if os.path.isfile(full) else None,
            })
        entries.sort(key=lambda item: (not item["is_dir"], item["name"].lower()))
        return jsonify({"path": path, "entries": entries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/fs/tail', methods=['POST'])
def tail_file():
    data = request.json or {}
    path = data.get('path')
    lines = int(data.get('lines', 50))
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            content = handle.readlines()
        tail = content[-lines:]
        return jsonify({"path": path, "lines": len(tail), "content": ''.join(tail)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/fs/grep', methods=['POST'])
def grep_file():
    data = request.json or {}
    path = data.get('path')
    pattern = data.get('pattern', '')
    max_matches = int(data.get('max_matches', 50))
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        matches = []
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            for line_no, line in enumerate(handle, start=1):
                if regex.search(line):
                    matches.append({"line": line_no, "text": line.rstrip()})
                    if len(matches) >= max_matches:
                        break
        return jsonify({"path": path, "pattern": pattern, "matches": matches})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/fs/write', methods=['POST'])
def save_file_content():
    """Writes files to local disk"""
    path = request.json.get('path')
    content = request.json.get('content')
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ui/screenshot', methods=['GET'])
def take_screenshot():
    """Takes a screenshot of the desktop"""
    try:
        save = request.args.get("save", "false").lower() in ("1", "true", "yes")
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = os.path.join(SCREENSHOT_DIR, f"screen_{stamp}.png")
        pyautogui.screenshot(path)
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        payload = {"image_base64": encoded_string}
        if save:
            payload["saved_path"] = path
        else:
            os.remove(path)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ui/click', methods=['POST'])
def click_ui():
    """Moves mouse and clicks"""
    x = request.json.get('x')
    y = request.json.get('y')
    button = request.json.get('button', 'left')
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(button=button)
        return jsonify({"status": f"Clicked {x}, {y}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ui/type', methods=['POST'])
def type_text():
    """Types text on keyboard"""
    text = request.json.get('text')
    try:
        pyautogui.write(text, interval=0.01)
        return jsonify({"status": "Typed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notify/email', methods=['POST'])
def notify_email():
    """Sends email from Gmail to operator iCloud (see .env)"""
    data = request.json or {}
    subject = data.get('subject', 'Jules Bridge update')
    body = data.get('body', '')
    if not body:
        return jsonify({"error": "body is required"}), 400
    try:
        import notify_email
        result = notify_email.send_email(subject, body)
        return jsonify({"status": "sent", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("========================================")
    print("🚀 JULES GOD-MODE BRIDGE ACTIVATED 🚀")
    print("========================================")
    app.run(port=5000, host='0.0.0.0')
