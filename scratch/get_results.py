"""get_full_results.py — fetch complete task results from Jules VM."""
import requests, json

VM = "http://34.132.193.73:6000"
P = {"http": None, "https": None}

r = requests.get(f"{VM}/status", timeout=10, proxies=P)
s = r.json()
print(f"Completed: {s['tasks_completed']} | Running: {s['tasks_running']}")

for t in s.get("recent", []):
    print("\n" + "="*70)
    print(f"TASK: {t['task'][:120]}")
    print(f"STATUS: {t['status']}")
    print(f"STARTED: {t.get('started','?')}")
    print(f"ENDED: {t.get('ended','?')}")
    print(f"\nFULL RESULT:\n{t.get('result','(none)')}")
    print("="*70)
