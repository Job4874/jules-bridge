"""
autopilot_runner.py -- Starts the bridge, runs the mission cycle, executes the picked task.
Run with: python autopilot_runner.py
"""
import subprocess
import sys
import time
import os
import json
import urllib.request

# --- Config ---
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".env")
BRIDGE_URL = "http://127.0.0.1:5000"
BRIDGE_SCRIPT = os.path.join(os.path.dirname(__file__), "bridge.py")

# Load .env
token = ""
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                os.environ[k] = v
                if k == "BRIDGE_TOKEN":
                    token = v

print(f"\n{'='*50}")
print("  ANTIGRAVITY AUTOPILOT -- F1 DRIVER")
print(f"{'='*50}\n")
print(f"[CONFIG] Bridge: {BRIDGE_URL}")
print(f"[CONFIG] Token: {len(token)}c")


def _get(path, timeout=10):
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _post(path, body=None, timeout=60):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# --- Step 1: Start bridge if not up ---
bridge_up = False
try:
    h = _get("/health", timeout=2)
    if h.get("status") == "ok":
        print(f"[BRIDGE] Already running (uptime={h.get('uptime_s')}s)")
        bridge_up = True
except Exception:
    pass

if not bridge_up:
    print("[BRIDGE] Starting...")
    bridge_proc = subprocess.Popen(
        [sys.executable, BRIDGE_SCRIPT],
        cwd=os.path.dirname(__file__),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    print(f"[BRIDGE] PID {bridge_proc.pid}")
    for i in range(15):
        time.sleep(1)
        try:
            h = _get("/health", timeout=2)
            if h.get("status") == "ok":
                print(f"[BRIDGE] UP after {i+1}s (uptime={h.get('uptime_s')}s)")
                bridge_up = True
                break
        except Exception:
            pass
    if not bridge_up:
        print("[ERROR] Bridge failed to start. Check bridge.log")
        sys.exit(1)

# --- Step 2: Read queue ---
q = _get("/mission/queue", timeout=10)
print(f"\n[QUEUE] Pending={q['pending']} Active={q['active']} Done={q['done']}")

if q["pending"] == 0 and q["active"] == 0:
    print("[MISSION] Queue clear. Add tasks to jules_inbox/MISSION_QUEUE.md")
    sys.exit(0)

# --- Step 3: Run cycle (pick next task) ---
print("[MISSION] Running cycle...")
cycle = _post("/mission/cycle", timeout=15)
print(f"[CYCLE]  ok={cycle['ok']} error={cycle.get('error')}")

if not cycle.get("ok") or not cycle.get("active_task"):
    print(f"[MISSION] No task picked: {cycle.get('error', 'unknown')}")
    sys.exit(0)

task = cycle["active_task"]
print(f"\n{'='*50}")
print(f"  ACTIVE: {task['task_id']} -- {task['task_type']}")
print(f"  Title: {task['title']}")
print(f"  URL:   {task['url']}")
print(f"  Agent: {task['assigned_to']}")
print(f"{'='*50}\n")

task_result = {"ok": False, "note": "not executed"}

# --- Step 4: Execute ---
if task["assigned_to"] == "playwright_agent":
    if task["task_type"] == "quiz":
        print(f"[BROWSER] Solving quiz: {task['url']}")
        result = _post("/browser/quiz", {"url": task["url"], "model": "fast"}, timeout=120)
        print(f"[RESULT] Answered: {result.get('questions_answered')}/{result.get('questions_found')} | Submitted: {result.get('submitted')}")
        if result.get("screenshot_path"):
            print(f"[PROOF]  Screenshot: {result['screenshot_path']}")
        task_result = result

    elif task["task_type"] == "research":
        print(f"[BROWSER] Navigating for research: {task['url']}")
        result = _post("/browser/navigate", {"url": task["url"]}, timeout=60)
        text = result.get("page_text", "")
        print(f"[RESULT] Page loaded. {len(text)} chars extracted.")
        print(f"[PREVIEW] {text[:500]}..." if len(text) > 500 else f"[TEXT] {text}")

        # Save to memory
        mem_path = os.path.join(os.path.dirname(__file__), "memory", "daily_briefing.md")
        os.makedirs(os.path.dirname(mem_path), exist_ok=True)
        from datetime import datetime, timezone
        with open(mem_path, "w", encoding="utf-8") as fh:
            fh.write(f"# Daily Briefing — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n")
            fh.write(f"**Source**: {task['url']}\n\n")
            fh.write(text[:3000])
        print(f"[SAVED]  memory/daily_briefing.md")
        task_result = result

# --- Step 5: Mark done ---
_post("/mission/done", {"task_id": task["task_id"], "result": task_result}, timeout=10)
print(f"\n[MISSION] {task['task_id']} marked DONE")

# --- Step 6: Learning retrospective ---
try:
    _post("/learning/reflect", {"task": task, "result": task_result}, timeout=10)
    print("[LEARNING] Memory updated")
except Exception as e:
    print(f"[LEARNING] Skipped: {e}")

print(f"\n{'='*50}")
print("  AUTOPILOT CYCLE COMPLETE")
print(f"{'='*50}\n")
