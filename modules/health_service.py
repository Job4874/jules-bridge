"""Health service deep module — multi-provider connectivity and host status.

Tests API keys (or acknowledges keyless state), cloud reachability, and
resource pressure to provide a proof of system readiness.
"""

from __future__ import annotations

import os
import time
import socket
from datetime import datetime, timezone
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from modules.vm_manager import detect_resource_pressure
from modules.chat_service import test_chat_providers

def _check_gcp() -> Dict[str, Any]:
    from modules.reasoning_module import _gcloud_access_token
    t0 = time.monotonic()
    token = _gcloud_access_token()
    elapsed = int((time.monotonic() - t0) * 1000)
    if token:
        return {"status": "pass", "ms": elapsed, "detail": "gcloud token active"}
    return {"status": "fail", "ms": elapsed, "detail": "No active gcloud session"}

def _check_azure() -> Dict[str, Any]:
    # Use env var or fall back to known worker IP
    az_ip = os.environ.get("AZURE_WORKER_VM_01", os.environ.get("AZURE_WORKER_IP", "74.249.129.209"))
    t0 = time.monotonic()
    try:
        with socket.create_connection((az_ip, 22), timeout=3.0):
            elapsed = int((time.monotonic() - t0) * 1000)
            return {"status": "pass", "ms": elapsed, "detail": f"VM {az_ip} SSH reachable"}
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        return {"status": "fail", "ms": elapsed, "detail": str(exc)}

def get_disk_usage() -> Dict[str, Any]:
    try:
        import psutil
        usage = psutil.disk_usage('/')
        return {
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "percent": usage.percent
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as exc:
        return {"error": str(exc)}

def get_deep_health() -> Dict[str, Any]:
    """Execute all health checks in parallel and return aggregated status."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        f_chat = executor.submit(test_chat_providers)
        f_gcp = executor.submit(_check_gcp)
        f_azure = executor.submit(_check_azure)

        chat_health = f_chat.result()
        results = {
            "gemini": chat_health["providers"]["gemini"],
            "openrouter": chat_health["providers"]["openrouter"],
            "gcp": f_gcp.result(),
            "azure": f_azure.result(),
        }

    # Normalize chat provider statuses to pass/fail/error/keyless for consistency
    for provider in ["gemini", "openrouter"]:
        status = results[provider].get("status")
        if status == "ok":
            results[provider]["status"] = "pass"
            results[provider]["detail"] = "Authenticated probe successful"
        elif status == "no_key":
            results[provider]["status"] = "keyless"
            results[provider]["detail"] = results[provider].get("detail", "API key unset")
        elif status in ("error", "exception"):
            results[provider]["status"] = "fail"

    pressure = detect_resource_pressure()
    disk = get_disk_usage()

    return {
        "status": "ok",
        "keyless_mode": not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "providers": results,
        "resources": {
            "cpu_percent": pressure.get("cpu_percent"),
            "memory_percent": pressure.get("memory_percent"),
            "disk": disk,
            "maxed_out": pressure.get("maxed_out", False) or (disk.get("percent", 0) > 95)
        }
    }
