First, ensure `psutil` is installed on the VM:

```bash
pip install psutil
```

Here is the complete implementation. This code uses `concurrent.futures` to ensure the endpoint remains responsive regardless of external API latency.

```python
import os
import time
import socket
import psutil
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import jsonify

# --- Health Check Helper Functions ---

def check_gemini():
    try:
        start = time.perf_counter()
        # Using the official models.list endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={os.getenv('GEMINI_API_KEY')}"
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        latency = int((time.perf_counter() - start) * 1000)
        return "gemini", {"ok": True, "latency_ms": latency, "model_count": len(data.get('models', []))}
    except Exception as e:
        return
