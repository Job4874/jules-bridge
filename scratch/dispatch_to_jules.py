"""dispatch_to_jules.py — send work packets directly to Jules VM agent."""
import json
import requests

VM = "http://34.132.193.73:6000"
TOKEN = "JULES-VM-WORKER-999"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Check status first
print("=== Jules VM Agent Status ===")
try:
    r = requests.get(f"{VM}/status", timeout=10, proxies={"http": None, "https": None})
    s = r.json()
    print(f"Online: {s.get('online')}")
    print(f"Uptime: {s.get('uptime_s')}s")
    print(f"Gemini: {s.get('gemini')}")
    print(f"OpenRouter: {s.get('openrouter')}")
    print(f"Local bridge: {s.get('local_bridge')}")
    print(f"Tasks completed: {s.get('tasks_completed')}")
    print(f"Recent: {s.get('recent')}")
except Exception as e:
    print(f"STATUS FAILED: {e}")
    exit(1)

# Dispatch mission planning task
MISSION = """You are Jules — an autonomous AI engineering agent running on a GCP VM (ubuntu-22.04, 2 vCPU, 4GB RAM).

Abdul is a solo developer. He has spent 12 months and real money (minimum wage job savings) building towards one goal: a production-grade trading terminal called TIBIN Terminal. He has used 1 trillion tokens and cannot show a single working production app from any of it. Every app is either riddled with bugs or has no real design.

Your context:
- Jules Bridge runs locally on his Windows PC at http://10.0.0.48:5000 (Flask, port 5000)
- You (Jules VM agent) run at http://34.132.193.73:6000 
- Bridge has modules: reasoning (HRM), file system, shell execution, UI automation, email
- Abdul has: Gemini API key (working), OpenRouter (working), Azure Student sub, GCP project tibin-terminal-2026
- His Downloads has: TIBIN_CODEX_HANDOVER_BUNDLE.zip, OracleV5-main.zip, order-flow-trader-main.zip

YOUR MISSION (respond with this exact structure):

## 5 Things I Will Build in the Next 24 Hours

For each item:
### [N]. [Name]
**What it is**: [1 sentence]  
**Time**: [estimate]
**Needs**: [tools/APIs required]
**Success criteria**: [measurable, verifiable]
**First action**: [exact first command or code I will write]

## Starting Now: Item #1

[Begin building item #1 — write the actual code, not a description of code]"""

print("\n=== Dispatching Mission Task ===")
try:
    r = requests.post(
        f"{VM}/task",
        json={"task": MISSION, "task_type": "build"},
        headers=HEADERS,
        timeout=30,
        proxies={"http": None, "https": None}
    )
    result = r.json()
    print(f"Dispatch result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"DISPATCH FAILED: {e}")

# Also dispatch a compute specs task
SPECS_TASK = "Run these commands and report results: df -h && free -h && nproc && cat /proc/cpuinfo | grep 'model name' | head -1 && pip list 2>/dev/null || ~/venv/bin/pip list"

print("\n=== Dispatching Compute Specs Task ===")
try:
    r = requests.post(
        f"{VM}/task",
        json={"task": SPECS_TASK, "task_type": "shell"},
        headers=HEADERS,
        timeout=30,
        proxies={"http": None, "https": None}
    )
    result = r.json()
    print(f"Specs dispatch: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"SPECS FAILED: {e}")

print("\n=== Done. Tasks queued on Jules VM. Check /status in 60s for results. ===")
