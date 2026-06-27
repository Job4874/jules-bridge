import requests, json
VM = "http://34.132.193.73:6000"
r = requests.get(f"{VM}/status", timeout=10, proxies={"http":None,"https":None})
s = r.json()
print(f"Uptime: {s['uptime_s']}s | Completed: {s['tasks_completed']} | Running: {s['tasks_running']}")
print("\nRecent tasks:")
for t in s.get("recent", []):
    print(json.dumps(t, indent=2))
