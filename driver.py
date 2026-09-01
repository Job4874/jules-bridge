"""
driver.py — F1 Autonomous Driver
==================================
The self-driving loop. Runs alongside bridge.py.
Polls MISSION_QUEUE.md every 30 seconds, picks the next task,
executes it through the right module, learns from the result.

Usage:
    python3.12 driver.py

Environment:
    BRIDGE_URL   = http://127.0.0.1:5000 (default)
    BRIDGE_TOKEN = your token from .env
    DRIVER_POLL_SECONDS = 30 (default)
    DRIVER_DRY_RUN = 1 (set to skip actual browser/submit)
"""

import json
import logging
import os
import sys
import time

# Force UTF-8 output on Windows so non-ASCII chars in identity/logs don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "driver.log", encoding="utf-8"),
    ],
)
LOGGER = logging.getLogger("f1_driver")

ROOT_DIR = Path(__file__).parent
BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:5000")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")
POLL_SECONDS = int(os.environ.get("DRIVER_POLL_SECONDS", "30"))
DRY_RUN = os.environ.get("DRIVER_DRY_RUN", "0") == "1"


def _load_env():
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():  # utf-8-sig strips BOM
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception as exc:
        LOGGER.warning("Could not load .env: %s", exc)


_load_env()
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", BRIDGE_TOKEN)


def _call_bridge(path, payload=None, method="POST"):
    import urllib.request
    import urllib.error
    url = f"{BRIDGE_URL}{path}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {BRIDGE_TOKEN}"}
    try:
        body = json.dumps(payload or {}).encode("utf-8") if method == "POST" else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _notify(subject, body, screenshot=""):
    payload = {"subject": subject, "body": body}
    if screenshot:
        payload["attachments"] = [screenshot]
    result = _call_bridge("/notify/email", payload)
    if not result.get("ok"):
        LOGGER.warning("Email notify failed: %s", result.get("error"))
    else:
        LOGGER.info("Email sent: %s", subject)


def _execute_browser_task(task):
    task_type = task.get("task_type", "research")
    url = task.get("url", "")
    if not url:
        return {"ok": False, "error": "No URL specified"}
    if DRY_RUN:
        LOGGER.info("[DRY RUN] browser task: %s -> %s", task_type, url)
        return {"ok": True, "dry_run": True, "url": url}
    profile = os.environ.get("PLAYWRIGHT_CHROME_PROFILE", "")
    if task_type == "quiz":
        return _call_bridge("/browser/quiz", {"url": url, "model": "fast", "profile": profile})
    elif task_type == "assignment":
        return _call_bridge("/browser/assignment", {"url": url, "profile": profile})
    else:
        return _call_bridge("/browser/navigate", {"url": url, "profile": profile})


def _execute_jules_task(task):
    if DRY_RUN:
        LOGGER.info("[DRY RUN] jules fleet for: %s", task.get("title"))
        return {"ok": True, "dry_run": True}
    return _call_bridge("/jules/fleet-watch", {"max_wait_s": 300, "poll_s": 30, "dry_run": False})


def _execute_shell_task(task):
    notes = task.get("notes", "")
    if not notes:
        return {"ok": False, "error": "No command in notes"}
    if DRY_RUN:
        LOGGER.info("[DRY RUN] shell: %s", notes)
        return {"ok": True, "dry_run": True}
    return _call_bridge("/shell", {"command": notes, "timeout_s": 60})


def _execute_task(task):
    assigned_to = task.get("assigned_to", "playwright_agent")
    task_type = task.get("task_type", "research")
    LOGGER.info("Executing %s [%s] assigned_to=%s", task.get("task_id"), task_type, assigned_to)
    if assigned_to == "playwright_agent" or task_type in ("quiz", "assignment", "research", "form"):
        return _execute_browser_task(task)
    elif assigned_to == "jules_fleet" or task_type == "code":
        return _execute_jules_task(task)
    elif assigned_to == "self" or task_type == "shell":
        return _execute_shell_task(task)
    else:
        LOGGER.warning("Unknown assigned_to=%s — browser fallback", assigned_to)
        return _execute_browser_task(task)


def run_cycle():
    cycle = _call_bridge("/mission/cycle", {})
    if not cycle.get("ok"):
        LOGGER.error("Mission cycle failed: %s", cycle.get("error"))
        return False
    active_task = cycle.get("active_task")
    if not active_task:
        q = cycle.get("queue_summary", {})
        LOGGER.info("Queue clear — pending=%s done=%s", q.get("pending", 0), q.get("done", 0))
        return False

    task_id = active_task.get("task_id", "unknown")
    LOGGER.info("=" * 60)
    LOGGER.info("MISSION START: %s — %s", task_id, active_task.get("title"))
    LOGGER.info("=" * 60)

    result = _execute_task(active_task)

    if result.get("ok"):
        _call_bridge("/mission/done", {"task_id": task_id, "result": result})
        _call_bridge("/learning/reflect", {"task": active_task, "result": result})
        LOGGER.info("MISSION DONE: %s", task_id)
        screenshot = result.get("screenshot_path", "")
        _notify(
            f"✅ Mission Complete: {active_task.get('title', task_id)}",
            f"Task {task_id} completed.\nType: {active_task.get('task_type')}\nURL: {active_task.get('url')}\n"
            f"Answered: {result.get('questions_answered', 'N/A')}\nSubmitted: {result.get('submitted', 'N/A')}",
            screenshot,
        )
    else:
        error = result.get("error", "unknown")
        _call_bridge("/mission/failed", {"task_id": task_id, "reason": error})
        LOGGER.error("MISSION FAILED: %s — %s", task_id, error)
        _notify(
            f"❌ Mission Failed: {active_task.get('title', task_id)}",
            f"Task {task_id} failed.\nError: {error}\nURL: {active_task.get('url')}\nCheck driver.log for details.",
        )
    return True


def main():
    LOGGER.info("=" * 60)
    LOGGER.info("F1 DRIVER — AUTONOMOUS LOOP ACTIVATED")
    LOGGER.info("Bridge: %s | Poll: %ds | Dry run: %s", BRIDGE_URL, POLL_SECONDS, DRY_RUN)
    LOGGER.info("=" * 60)

    for attempt in range(120):
        health = _call_bridge("/health", method="GET")
        if health.get("status") == "ok":
            LOGGER.info("Bridge ready: %s", health.get("identity", ""))
            break
        if attempt % 6 == 0:
            LOGGER.info("Waiting for bridge... %d/120", attempt + 1)
        time.sleep(0.5)
    else:
        LOGGER.error("Bridge not available after 60s. Is bridge.py running?")
        sys.exit(1)

    LOGGER.info("Watching: jules_inbox/MISSION_QUEUE.md")
    consecutive_empty = 0
    while True:
        try:
            executed = run_cycle()
            if executed:
                consecutive_empty = 0
                time.sleep(5)
            else:
                consecutive_empty += 1
                sleep_s = min(POLL_SECONDS * min(consecutive_empty, 4), 120)
                LOGGER.info("Sleeping %ds (idle streak: %d)", sleep_s, consecutive_empty)
                time.sleep(sleep_s)
        except KeyboardInterrupt:
            LOGGER.info("Driver stopped.")
            break
        except Exception as exc:
            LOGGER.exception("Driver error: %s", exc)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
