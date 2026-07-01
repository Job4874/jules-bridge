#!/usr/bin/env python3
"""
Jules Two-Way Bridge Relay — vm_relay.py

This runs INSIDE the local bridge (already started as part of bridge.py modules).
It also runs as a standalone bootstrap tool to:
  1. SSH into the GCP VM
  2. Install Python + deps on the VM
  3. Push the jules-worker bootstrap script
  4. Start jules-worker-agent.py on the VM
  5. Maintain a persistent HTTP relay so local bridge <-> VM bridge can exchange tasks

The VM runs its own lightweight agent (jules-worker-agent.py) that:
  - Accepts POST /task packets
  - Executes them (code, research, browser, file ops)
  - Returns results to local bridge relay
  - Delegates model work to an operator-configured browser model loop

Architecture:
  [User/Dashboard] -> [Local Bridge :5000] -> [VM Relay] -> [VM Agent :6000]
                                          <-              <-
"""
from __future__ import annotations

import socket
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent
_ENV_PATH = _ROOT / ".env"
_RELAY_LOG = _ROOT / "jules_inbox" / "relay.log"
_RELAY_LOG.parent.mkdir(parents=True, exist_ok=True)

# VM config from .env
def _env() -> dict:
    env = {}
    try:
        for line in _ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return env

VM_IP   = _env().get("GCE_WORKER_IP", "34.132.193.73")
VM_NAME = _env().get("GCE_WORKER_NAME", "jules-offload-worker")
VM_ZONE = _env().get("GCE_WORKER_ZONE", "us-central1-a")
VM_PROJ = _env().get("GCE_WORKER_PROJECT", "tibin-terminal-2026")
VM_USER = "julesadmin"
VM_PORT = 6000   # The agent port on the VM

_relay_log_lock = threading.Lock()


def _log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}\n"
    with _relay_log_lock:
        with open(_RELAY_LOG, "a", encoding="utf-8") as f:
            f.write(line)


def _gcloud_ssh(remote_cmd: str, timeout: int = 60) -> tuple[str, str, int]:
    """Run a command on the VM via gcloud compute ssh."""
    cmd = [
        "gcloud", "compute", "ssh",
        f"{VM_USER}@{VM_NAME}",
        f"--zone={VM_ZONE}",
        f"--project={VM_PROJ}",
        "--tunnel-through-iap",
        "--command", remote_cmd,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return proc.stdout, proc.stderr, proc.returncode


def _gcloud_scp(local_path: str, remote_path: str) -> tuple[str, str, int]:
    """Copy a local file to the VM via gcloud compute scp."""
    cmd = [
        "gcloud", "compute", "scp",
        local_path,
        f"{VM_USER}@{VM_NAME}:{remote_path}",
        f"--zone={VM_ZONE}",
        f"--project={VM_PROJ}",
        "--tunnel-through-iap",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    return proc.stdout, proc.stderr, proc.returncode


def bootstrap_vm() -> dict[str, Any]:
    """
    SSH into the VM and install the jules-worker-agent.
    Safe to call multiple times — idempotent.
    """
    _log(f"Bootstrapping VM {VM_NAME} at {VM_IP}")
    results = []

    # Step 1: Install deps
    _log("Installing Python deps...")
    _, stderr, rc = _gcloud_ssh(
        "sudo apt-get update -qq && sudo apt-get install -y -qq "
        "python3 python3-pip git curl && "
        "pip3 install flask requests --quiet",
        timeout=180
    )
    results.append({"step": "install_deps", "rc": rc, "stderr": stderr[:200] if stderr else ""})
    _log(f"deps rc={rc}")

    # Step 2: Push the worker agent script
    agent_script = _build_worker_agent_script()
    agent_path = _ROOT / "scratch" / "jules-worker-agent.py"
    agent_path.parent.mkdir(parents=True, exist_ok=True)
    agent_path.write_text(agent_script, encoding="utf-8")

    _, _, rc = _gcloud_scp(str(agent_path), "/home/julesadmin/jules-worker-agent.py")
    results.append({"step": "push_agent", "rc": rc})
    _log(f"push_agent rc={rc}")

    # Step 3: Push env (loop endpoints only, no provider API keys)
    env_vars = _env()
    minimal_env = _build_worker_env(env_vars, _get_local_ip())
    env_path = _ROOT / "scratch" / "vm.env"
    env_path.write_text(minimal_env, encoding="utf-8")
    _, _, rc = _gcloud_scp(str(env_path), "/home/julesadmin/.jules_worker.env")
    results.append({"step": "push_env", "rc": rc})
    _log(f"push_env rc={rc}")

    # Step 4: Start (or restart) the worker agent
    _, _, rc = _gcloud_ssh(
        "pkill -f 'jules-worker-agent' 2>/dev/null || true; "
        "nohup python3 /home/julesadmin/jules-worker-agent.py "
        "> /home/julesadmin/worker.log 2>&1 &",
        timeout=30
    )
    results.append({"step": "start_agent", "rc": rc})
    _log(f"start_agent rc={rc}")

    return {"ok": all(r["rc"] == 0 for r in results), "steps": results, "vm": VM_IP}


def _build_worker_env(env_vars: dict[str, str], local_ip: str) -> str:
    bridge_token = env_vars.get("LOCAL_BRIDGE_TOKEN") or env_vars.get("BRIDGE_TOKEN", "")
    return "\n".join([
        f"BROWSER_MODEL_LOOP_URL={env_vars.get('BROWSER_MODEL_LOOP_URL','')}",
        f"LOCAL_BRIDGE_URL=http://{local_ip}:5000",
        f"LOCAL_BRIDGE_TOKEN={bridge_token}",
    ])


def _get_local_ip() -> str:
    """Get the local machine's LAN IP so the VM can call back."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:  # pylint: disable=broad-exception-caught
        return "127.0.0.1"


def send_task_to_vm(task: str, task_type: str = "build", context: str = "") -> dict[str, Any]:
    """
    Send a task packet to the jules-worker-agent on the VM via direct HTTP.
    The VM agent listens on port 6000 (firewall rule: jules-agent-port).
    Returns the agent's response dict.
    """
    import requests as _req  # pylint: disable=import-outside-toplevel
    payload = {
        "task": task,
        "task_type": task_type,
        "context": context,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _log(f"Sending task to VM http://{VM_IP}:{VM_PORT}/task: {task[:80]}")
    try:
        r = _req.post(
            f"http://{VM_IP}:{VM_PORT}/task",
            json=payload, timeout=30,
            headers={"Authorization": "Bearer JULES-VM-WORKER-999"}
        )
        return r.json()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _log(f"Task send failed: {exc}")
        return {"ok": False, "error": str(exc)}



def get_vm_status() -> dict[str, Any]:
    """Poll the VM agent's /status endpoint."""
    import requests as _req  # pylint: disable=import-outside-toplevel
    try:
        r = _req.get(f"http://{VM_IP}:{VM_PORT}/status", timeout=5)
        return r.json()
    except Exception:  # pylint: disable=broad-exception-caught
        return {"online": False}


def _build_worker_agent_script() -> str:
    """Generate the jules-worker-agent.py that runs on the GCP VM."""
    return '''#!/usr/bin/env python3
"""
jules-worker-agent.py — runs on the GCP VM (jules-offload-worker)
Accepts task packets from the local bridge relay and executes them.
Calls back to local bridge with results. Self-improving: it reads its
own instructions and can modify them via the local bridge /chat endpoint.
"""
import json, os, subprocess, threading, time, requests
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify

# Load env
for line in Path("/home/julesadmin/.jules_worker.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip()

app = Flask(__name__)
TOKEN = "JULES-VM-WORKER-999"
BROWSER_MODEL_LOOP_URL = os.environ.get("BROWSER_MODEL_LOOP_URL", "")
LOCAL_BRIDGE = os.environ.get("LOCAL_BRIDGE_URL", "http://127.0.0.1:5000")
LOCAL_TOKEN = os.environ.get("LOCAL_BRIDGE_TOKEN", "")

_START = datetime.now(timezone.utc)
_TASKS_COMPLETED = []
_TASKS_RUNNING = []

def auth():
    if request.headers.get("Authorization") != f"Bearer {TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

@app.before_request
def check_auth():
    if request.path in ("/status", "/ping"):
        return None
    return auth()

@app.route("/ping")
def ping():
    return jsonify({"ok": True, "agent": "jules-worker", "ip": os.popen("curl -s ifconfig.me").read().strip()})

@app.route("/status")
def status():
    up = (datetime.now(timezone.utc) - _START).total_seconds()
    return jsonify({
        "online": True,
        "uptime_s": int(up),
        "tasks_completed": len(_TASKS_COMPLETED),
        "tasks_running": len(_TASKS_RUNNING),
        "recent": _TASKS_COMPLETED[-5:],
        "browser_model_loop": bool(BROWSER_MODEL_LOOP_URL),
    })

@app.route("/task", methods=["POST"])
def task():
    data = request.get_json() or {}
    task_text = data.get("task", "")
    task_type = data.get("task_type", "build")
    context   = data.get("context", "")
    if not task_text:
        return jsonify({"error": "task required"}), 400

    entry = {"task": task_text[:120], "status": "running", "started": datetime.now(timezone.utc).isoformat()}
    _TASKS_RUNNING.append(entry)

    def run():
        result = execute_task(task_text, task_type, context)
        entry["status"] = "done"
        entry["result"] = str(result)[:500]
        entry["ended"] = datetime.now(timezone.utc).isoformat()
        _TASKS_RUNNING.remove(entry)
        _TASKS_COMPLETED.append(entry)
        # Call back to local bridge
        try:
            requests.post(f"{LOCAL_BRIDGE}/inbox/append", json={
                "file": "vm_results.jsonl",
                "content": json.dumps(entry)
            }, headers={"Authorization": f"Bearer {LOCAL_TOKEN}"}, timeout=10)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True, "task": task_text[:80], "status": "queued"})

def execute_task(task: str, task_type: str, context: str) -> str:
    """Route task to appropriate executor."""
    if task_type == "shell":
        proc = subprocess.run(task, shell=True, capture_output=True, text=True, timeout=60)
        return proc.stdout + proc.stderr
    elif task_type in ("build", "research", "chat"):
        return call_llm(task, context)
    else:
        return call_llm(task, context)

def call_llm(prompt: str, context: str = "") -> str:
    """Call the configured browser model loop with the task."""
    system = (
        "You are Jules — an autonomous AI engineering agent running on a GCP VM. "
        "You are the worker node in a multi-agent system. Your job is to build, fix, research, "
        "and ship code. You have access to a Linux shell (Ubuntu 22.04), Python, git, curl, and pip. "
        "When asked to build something, produce complete working code. "
        "Be direct and production-focused. No placeholders, no TODOs."
    )
    full_prompt = f"{context}\\n\\n{prompt}" if context else prompt

    if not BROWSER_MODEL_LOOP_URL:
        return "No browser model loop configured. Set BROWSER_MODEL_LOOP_URL in the worker env."
    try:
        r = requests.post(
            BROWSER_MODEL_LOOP_URL,
            json={"system": system, "prompt": full_prompt},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        for key in ("response", "result", "text", "content"):
            if data.get(key):
                return str(data[key])
        return json.dumps(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return f"Browser model loop failed: {exc}"

if __name__ == "__main__":
    print(f"Jules Worker Agent starting on port 6000...")
    app.run(host="0.0.0.0", port=6000)
'''
