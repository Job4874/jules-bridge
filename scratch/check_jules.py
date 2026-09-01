"""check_jules.py — check status of the Jules VM worker agent."""
import json
import urllib3

VM = "http://34.132.193.73:6000"
http = urllib3.PoolManager()
r = http.request('GET', f"{VM}/status", timeout=10.0)
s = json.loads(r.data.decode('utf-8'))

print(f"Uptime: {s['uptime_s']}s | Completed: {s['tasks_completed']} | Running: {s['tasks_running']}")
print("\nRecent tasks:")
for t in s.get("recent", []):
    print(json.dumps(t, indent=2))
