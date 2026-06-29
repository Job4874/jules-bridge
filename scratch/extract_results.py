# pylint: disable=wrong-import-order

"""extract_and_run_tibin.py — pull tibin_core.py from Jules result and run it on VM."""
import re

import requests
from pathlib import Path

VM = "http://34.132.193.73:6000"
P = {"http": None, "https": None}

r = requests.get(f"{VM}/status", timeout=10, proxies=P)
tasks = r.json().get("recent", [])

# Find the TIBIN build task
tibin_task = next((t for t in tasks if "TIBIN Core Integration" in t.get("task","")), None)
health_task = next((t for t in tasks if "/health/deep" in t.get("task","")), None)
compute_task = next((t for t in tasks if "FREE compute" in t.get("task","")), None)

# Save TIBIN result
if tibin_task:
    result = tibin_task["result"]
    # Extract python code block
    match = re.search(r'```python\n(.*?)```', result, re.DOTALL)
    if match:
        code = match.group(1)
        Path(r"C:\Users\abdul\.jules\modules\tibin_core.py").write_text(code, encoding="utf-8")
        print(f"[TIBIN] Saved tibin_core.py ({len(code)} chars)")
    else:
        Path(r"C:\Users\abdul\.jules\jules_inbox\tibin_core_raw.md").write_text(result, encoding="utf-8")
        print(f"[TIBIN] Saved raw result ({len(result)} chars) - no code block found")

# Save health check result
if health_task:
    result = health_task["result"]
    match = re.search(r'```python\n(.*?)```', result, re.DOTALL)
    if match:
        code = match.group(1)
        Path(r"C:\Users\abdul\.jules\jules_inbox\health_deep_code.py").write_text(code, encoding="utf-8")
        print(f"[HEALTH] Saved health_deep_code.py ({len(code)} chars)")
    else:
        Path(r"C:\Users\abdul\.jules\jules_inbox\health_deep_raw.md").write_text(result, encoding="utf-8")
        print(f"[HEALTH] Saved raw result ({len(result)} chars)")

# Save compute research
if compute_task:
    result = compute_task["result"]
    Path(r"C:\Users\abdul\.jules\jules_inbox\free_compute.md").write_text(result, encoding="utf-8")
    print(f"[COMPUTE] Saved free_compute.md ({len(result)} chars)")

print("\nDone. Check jules_inbox/ and modules/ for extracted files.")
