import os
import subprocess
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import pyautogui

# Safety switch: Move mouse to a corner of the screen to kill the automation if it goes crazy
pyautogui.FAILSAFE = True 

app = Flask(__name__)
CORS(app)

INBOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jules_inbox")

TENTACLES = [
    {"name": "pulse", "route": "GET /ping", "reach": "Confirm the bridge is alive"},
    {"name": "shell", "route": "POST /shell", "reach": "Run PowerShell on the host"},
    {"name": "read", "route": "POST /fs/read", "reach": "Read any file on the host"},
    {"name": "write", "route": "POST /fs/write", "reach": "Write any file on the host"},
    {"name": "eyes", "route": "GET /ui/screenshot", "reach": "See the desktop"},
    {"name": "hand", "route": "POST /ui/click", "reach": "Click the mouse"},
    {"name": "voice", "route": "POST /ui/type", "reach": "Type on the keyboard"},
    {"name": "mail", "route": "POST /notify/email", "reach": "Email the operator (Gmail to iCloud)"},
    {"name": "inbox_read", "route": "POST /inbox/read", "reach": "Read operator/Jules inbox messages"},
    {"name": "inbox_write", "route": "POST /inbox/write", "reach": "Write Jules inbox replies"},
    {"name": "manifest", "route": "GET /tentacles", "reach": "List every tentacle (this endpoint)"},
]

@app.route('/tentacles', methods=['GET'])
def tentacles():
    """Octopus manifest — each endpoint is a tentacle: far reach through one URL."""
    return jsonify({
        "creature": "Jules Bridge",
        "meaning": "One ngrok URL. Many tentacles. Each route extends reach to the host.",
        "access": "Possession of the bridge URL is possession of host access.",
        "tentacles": TENTACLES,
    })

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
    data = request.json
    cmd = data.get('command')
    cwd = data.get('cwd', os.getcwd())
    print(f"[JULES SHELL] -> {cmd}")
    try:
        res = subprocess.run(["powershell", "-Command", cmd], cwd=cwd, capture_output=True, text=True, timeout=120)
        return jsonify({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/fs/read', methods=['POST'])
def get_file_content():
    """Reads local files"""
    path = request.json.get('path')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify({"content": f.read()})
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
        path = "temp_screen.png"
        pyautogui.screenshot(path)
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        if os.path.exists(path):
            os.remove(path)
        return jsonify({"image_base64": encoded_string})
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
