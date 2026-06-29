# pylint: disable=wrong-import-order

"""check_openrouter_free.py — find all currently-free models on OpenRouter."""
import os

import requests
from pathlib import Path

env_file = Path(os.path.expanduser("~/.jules_worker.env"))
for line in env_file.read_text(encoding='utf-8').splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip()

OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")

r = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {OR_KEY}"},
    timeout=15
)

models = r.json().get("data", [])
free = [m for m in models if ":free" in m.get("id","") or m.get("pricing",{}).get("prompt","1") == "0"]
print(f"Total models: {len(models)}")
print(f"Free models: {len(free)}")
print("\nFree model IDs (first 20):")
for m in free[:20]:
    print(f"  {m['id']} - ctx={m.get('context_length','?')}")

# Try the first free model
if free:
    test_model = free[0]["id"]
    print(f"\nTesting: {test_model}")
    r2 = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={"model": test_model,
              "messages": [{"role": "user", "content": "Reply OPENROUTER_OK"}],
              "max_tokens": 20},
        headers={"Authorization": f"Bearer {OR_KEY}"},
        timeout=30
    )
    print(f"Status: {r2.status_code}")
    if r2.status_code == 200:
        print(f"Response: {r2.json()['choices'][0]['message']['content']}")
    else:
        print(f"Error: {r2.text[:200]}")
