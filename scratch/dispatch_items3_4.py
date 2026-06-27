"""dispatch_items3_4.py — dispatch order-flow engine and deployment pipeline."""
import requests, time

VM = "http://34.132.193.73:6000"
TOKEN = "JULES-VM-WORKER-999"
H = {"Authorization": f"Bearer {TOKEN}"}
P = {"http": None, "https": None}

def q(task, task_type="build"):
    r = requests.post(f"{VM}/task", json={"task": task, "task_type": task_type},
                      headers=H, timeout=30, proxies=P)
    return r.json()

# Item 3: Free compute research — find where to run Jules 24/7 for free
COMPUTE_TASK = """Research task: Find all FREE compute platforms where I (Jules, an AI agent running Python Flask) can run 24/7 in 2025.

For each platform, provide:
- Platform name
- Free tier limits (CPU, RAM, storage, hours/month)
- Signup URL
- How to deploy a Python Flask app
- Estimated monthly cost: $0

Platforms to research:
1. Oracle Cloud Always Free (ARM and x86 VMs - truly always free)
2. Fly.io free tier (3 shared VMs)
3. Render.com free tier (750h/month)  
4. Railway.app ($5 free credits/month)
5. Hugging Face Spaces (ZeroGPU, CPU free)
6. Deno Deploy (free edge runtime)
7. Vercel free tier (serverless)
8. Azure Student credits (Abdul has this - how much is left?)

Format as a markdown table with columns: Platform | Free RAM | Free vCPU | Always Free? | Deploy Command | Notes

Then recommend the TOP 2 for running a persistent Python agent (not serverless)."""

print("[3] Dispatching compute research task...")
r3 = q(COMPUTE_TASK, "research")
print(f"   {r3}")
time.sleep(1)

# Item 4: Deep health check endpoint
HEALTH_TASK = """Build a /health/deep endpoint for Jules Bridge (Flask app at port 5000).

The endpoint must:
1. Test each configured API key by making a real lightweight call:
   - GEMINI_API_KEY: call models.list endpoint
   - OPENROUTER_API_KEY: call /models endpoint  
   - GMAIL_USER: check if env var exists (don't test SMTP)
   - GCE_WORKER_IP: TCP ping port 6000

2. Return JSON with this exact structure:
{
  "ok": true/false,
  "checks": {
    "gemini": {"ok": true, "latency_ms": 245, "model_count": 50},
    "openrouter": {"ok": true, "latency_ms": 180, "free_models": 26},
    "gmail": {"ok": true, "configured": true},
    "gce_vm": {"ok": true, "ip": "34.132.193.73", "latency_ms": 12}
  },
  "system": {
    "cpu_percent": 12.5,
    "memory_percent": 45.2,
    "disk_free_gb": 141
  },
  "timestamp": "2026-06-27T..."
}

3. Uses psutil for system metrics (pip install psutil)
4. All checks are non-blocking (parallel with concurrent.futures)
5. Total endpoint must respond in <5s even if some checks fail

Write the complete Python function to add to bridge.py.
The function signature: def health_deep() -> tuple
Route: GET /health/deep
No auth required (add to whitelist)."""

print("[4] Dispatching deep health check build task...")
r4 = q(HEALTH_TASK, "build")
print(f"   {r4}")

print("\nAll dispatched. Jules is working on 3 tasks in parallel.")
print("Check results with: python scratch\\get_results.py")
