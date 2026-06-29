import os
import sys
import time
import subprocess
import requests
import json
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(ROOT_DIR, "memory", "auto_fix_log.txt")

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    entry = f"[{ts}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def check_for_problems():
    try:
        # Run pytest to detect any broken tests, syntax errors, or imports
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=ROOT_DIR
        )
        if result.returncode != 0:
            return result.stdout[-2000:]  # Return the last 2000 chars of failure
        return None
    except Exception as e:
        return f"Failed to run pytest: {e}"

def dispatch_to_jules(problem_text):
    log("Dispatching problem to Jules HRM Reasoning Engine...")
    payload = {
        "problem": f"Codebase problems detected. Please fix them. Details:\n{problem_text}",
        "context": "You are the autonomous auto-fix agent. Fix the code causing these errors. Your goal is to make all tests pass.",
        "model": "fast"
    }
    
    try:
        resp = requests.post("http://127.0.0.1:5000/reasoning/solve", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        
        answer = data.get("answer", "No answer provided")
        log(f"Jules completed fix attempt. Answer: {answer}")
    except Exception as e:
        log(f"Error calling Jules: {e}")

def main():
    log("Starting Auto-Fix Watcher (1-minute interval)")
    while True:
        try:
            problem = check_for_problems()
            if problem:
                log(f"Problem detected. Sending to Jules.")
                dispatch_to_jules(problem)
            else:
                log("No problems detected.")
        except Exception as e:
            log(f"Watcher error: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    main()
