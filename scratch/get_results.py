"""get_results_v2.py — fetch + save all Jules results (UTF-8 safe)."""
import json
import os
import sys

import requests
from pathlib import Path

VM = "http://34.132.193.73:6000"
P = {"http": None, "https": None}

r = requests.get(f"{VM}/status", timeout=10, proxies=P)
s = r.json()

out_file = Path(r"C:\Users\abdul\.jules\jules_inbox\all_results.md")

lines = []
lines.append(f"# Jules VM Results — {s.get('uptime_s')}s uptime")
lines.append(f"Completed: {s['tasks_completed']} | Running: {s['tasks_running']}\n")

for i, t in enumerate(s.get("recent", []), 1):
    lines.append(f"{'='*70}")
    lines.append(f"## Task {i}: {t['task'][:100]}")
    lines.append(f"Status: {t['status']} | Started: {t.get('started','?')[:19]} | Ended: {t.get('ended','?')[:19]}")
    lines.append(f"\n### Result:\n{t.get('result','(none)')}\n")

content = "\n".join(lines)
out_file.write_text(content, encoding="utf-8")
print(f"Saved {len(lines)} lines to {out_file}")
print(f"Tasks: {s['tasks_completed']} completed")

# Also print summary safely
for i, t in enumerate(s.get("recent", []), 1):
    task_preview = t["task"][:80].encode("ascii", "replace").decode()
    result_preview = t.get("result", "")[:200].encode("ascii", "replace").decode()
    print(f"\n[{i}] {task_preview}")
    print(f"    Result: {result_preview}")
