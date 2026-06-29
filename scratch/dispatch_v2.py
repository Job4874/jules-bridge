# pylint: disable=redefined-outer-name

"""dispatch_v2.py — dispatch tasks to Jules VM with Gemini test first."""
import time

import requests

VM = "http://34.132.193.73:6000"
TOKEN = "JULES-VM-WORKER-999"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
P = {"http": None, "https": None}  # bypass proxy

def post(task, task_type="build", context=""):
    r = requests.post(f"{VM}/task",
        json={"task": task, "task_type": task_type, "context": context},
        headers=H, timeout=30, proxies=P)
    return r.json()

def status():
    r = requests.get(f"{VM}/status", timeout=10, proxies=P)
    return r.json()

# Quick LLM test first
print("[1] Sending Gemini smoke test...")
r = post("Reply with exactly this text and nothing else: GEMINI_OK", "build")
print(f"   queued: {r}")

time.sleep(2)

# Mission task
MISSION = """You are Jules — autonomous AI agent on GCP VM.

Abdul is a solo developer, minimum wage job, 12 months of trying, 1 trillion tokens spent, ZERO production apps to show. He has:
- Jules Bridge Flask API (port 5000) on his Windows PC
- You (Jules VM agent) on GCP at port 6000
- Gemini API key (working)
- Downloads folder with: TIBIN trading terminal code (partially built), OracleV5, order-flow-trader

YOUR MISSION — respond in this exact format:

## 5 Things I Build in 24h

### 1. [Name]
**What**: [1 sentence]
**Time**: [X hours]
**Success proof**: [how we verify it works]

### 2-5. [same format]

## Starting NOW: Item 1

[Write the actual working code for item 1. Not pseudocode. Not a plan. Working code.]"""

print("[2] Sending mission task...")
r = post(MISSION, "build")
print(f"   queued: {r}")

# Compute specs
print("[3] Sending compute specs check...")
r = post("df -h && free -h && nproc && cat /proc/cpuinfo | grep 'model name' | head -1", "shell")
print(f"   queued: {r}")

print("\nAll dispatched. Waiting 60s for Gemini responses...")
time.sleep(60)

s = status()
print(f"\nStatus: uptime={s['uptime_s']}s completed={s['tasks_completed']} running={s['tasks_running']}")
print("\nResults:")
for t in s.get("recent", []):
    print(f"\nTask: {t['task'][:60]}...")
    print(f"Status: {t['status']}")
    print(f"Result:\n{t.get('result','(none)')[:800]}")
    print("-"*60)
