#!/usr/bin/env python3
"""
jules-worker-agent.py — runs on the GCP VM (jules-offload-worker)
Accepts task packets from the local bridge relay and executes them.
Calls back to local bridge with results.
"""
import json
import os
import subprocess
import threading
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify

# Load env
env_file = Path("/home/julesadmin/.jules_worker.env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()

app = Flask(__name__)
TOKEN = "JULES-VM-WORKER-999"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LOCAL_BRIDGE = os.environ.get("LOCAL_BRIDGE_URL", "http://127.0.0.1:5000")
LOCAL_TOKEN = os.environ.get("LOCAL_BRIDGE_TOKEN", "JULES-SECURE-999")

_START = datetime.now(timezone.utc)
_TASKS_COMPLETED = []
_TASKS_RUNNING = []


def auth_check():
    if request.headers.get("Authorization") != f"Bearer {TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    return None


@app.before_request
def check_auth():
    if request.path in ("/status", "/ping"):
        return None
    result = auth_check()
    if result is not None:
        return result


@app.route("/ping")
def ping():
    ext_ip = ""
    try:
        ext_ip = subprocess.check_output(["curl", "-s", "--max-time", "3", "ifconfig.me"],
                                          text=True).strip()
    except Exception:
        pass
    return jsonify({"ok": True, "agent": "jules-worker", "ip": ext_ip})


@app.route("/status")
def status():
    up = (datetime.now(timezone.utc) - _START).total_seconds()
    return jsonify({
        "online": True,
        "uptime_s": int(up),
        "tasks_completed": len(_TASKS_COMPLETED),
        "tasks_running": len(_TASKS_RUNNING),
        "recent": _TASKS_COMPLETED[-5:],
        "gemini": bool(GEMINI_KEY),
        "openrouter": bool(OR_KEY),
        "local_bridge": LOCAL_BRIDGE,
    })


@app.route("/task", methods=["POST"])
def task():
    data = request.get_json() or {}
    task_text = data.get("task", "")
    task_type = data.get("task_type", "build")
    context = data.get("context", "")
    if not task_text:
        return jsonify({"error": "task required"}), 400

    entry = {
        "task": task_text[:120],
        "status": "running",
        "started": datetime.now(timezone.utc).isoformat()
    }
    _TASKS_RUNNING.append(entry)

    def run():
        try:
            result = execute_task(task_text, task_type, context)
        except Exception as exc:
            result = f"ERROR: {exc}"
        entry["status"] = "done"
        entry["result"] = str(result)[:1000]
        entry["ended"] = datetime.now(timezone.utc).isoformat()
        if entry in _TASKS_RUNNING:
            _TASKS_RUNNING.remove(entry)
        _TASKS_COMPLETED.append(entry)
        # Call back to local bridge
        try:
            requests.post(
                f"{LOCAL_BRIDGE}/inbox/append",
                json={"file": "vm_results.jsonl", "content": json.dumps(entry)},
                headers={"Authorization": f"Bearer {LOCAL_TOKEN}"},
                timeout=10
            )
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True, "task": task_text[:80], "status": "queued"})


def execute_task(task: str, task_type: str, context: str) -> str:
    """Route task to appropriate executor."""
    if task_type == "shell":
        proc = subprocess.run(task, shell=True, capture_output=True, text=True, timeout=60)
        return (proc.stdout + proc.stderr).strip()
    else:
        return call_llm(task, context)


def call_llm(prompt: str, context: str = "") -> str:
    """Call Gemini or OpenRouter with the task."""
    system = (
        "You are Jules — an autonomous AI engineering agent running on a GCP VM (Ubuntu 22.04). "
        "You are the worker node in a multi-agent system owned by Abdul (solo developer). "
        "Your job: build, fix, research, and ship production-grade code. "
        "You have access to a Linux shell, Python 3, git, curl, pip, and the Internet. "
        "When asked to build something, produce complete working code — no placeholders, no TODOs. "
        "When asked to research, give concrete findings with URLs and evidence. "
        "Be direct. Abdul has spent 12 months and real money. Make every response count."
    )
    full_prompt = f"{context}\n\n{prompt}" if context else prompt

    # Try Gemini Flash first
    if GEMINI_KEY:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                    "generationConfig": {"maxOutputTokens": 4096}
                },
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            pass

    # OpenRouter fallback (free tier)
    if OR_KEY:
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": "google/gemma-3-27b-it:free",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": full_prompt}
                    ]
                },
                headers={"Authorization": f"Bearer {OR_KEY}"},
                timeout=60
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    return "No LLM available — check GEMINI_API_KEY and OPENROUTER_API_KEY in /home/julesadmin/.jules_worker.env"


if __name__ == "__main__":
    print(f"[{datetime.now(timezone.utc).isoformat()}] Jules Worker Agent starting on port 6000...", flush=True)
    print(f"  Gemini: {'configured' if GEMINI_KEY else 'MISSING'}", flush=True)
    print(f"  OpenRouter: {'configured' if OR_KEY else 'MISSING'}", flush=True)
    print(f"  Local Bridge: {LOCAL_BRIDGE}", flush=True)
    app.run(host="0.0.0.0", port=6000)
