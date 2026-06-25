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

if __name__ == '__main__':
    print("========================================")
    print("🚀 JULES GOD-MODE BRIDGE ACTIVATED 🚀")
    print("========================================")
    app.run(port=5000, host='0.0.0.0')
