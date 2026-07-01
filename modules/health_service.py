"""Health service deep module — model-loop connectivity and host status.

Tests the VM/browser model loop, cloud reachability, and
resource pressure to provide a proof of system readiness.
"""

from __future__ import annotations

import time
import socket
import subprocess
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from modules.chat_service import test_chat_providers
from modules.vm_manager import detect_resource_pressure

def _check_model_loop() -> Dict[str, Any]:
    """Check the local VM/browser model loop without probing provider API keys."""
    t0 = time.monotonic()
    try:
        result = test_chat_providers()
        elapsed = int((time.monotonic() - t0) * 1000)
        return {
            "status": "pass" if result.get("healthy") else "fail",
            "ms": elapsed,
            "detail": "VM/browser model loop reachable" if result.get("healthy") else "VM/browser model loop unavailable",
            "providers": result.get("providers", {}),
        }
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        return {"status": "error", "ms": elapsed, "detail": str(exc)}

def _check_gcp() -> Dict[str, Any]:
    t0 = time.monotonic()
    token = ""
    for cmd in (["gcloud", "auth", "print-access-token"], ["gcloud.cmd", "auth", "print-access-token"]):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                shell=True,
                check=False,
            )
            candidate = result.stdout.strip()
            if result.returncode == 0 and candidate:
                token = candidate
                break
        except Exception:  # pylint: disable=broad-exception-caught
            continue
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
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_model_loop = executor.submit(_check_model_loop)
        f_gcp = executor.submit(_check_gcp)
        f_azure = executor.submit(_check_azure)

        results = {
            "model_loop": f_model_loop.result(),
            "gcp": f_gcp.result(),
            "azure": f_azure.result(),
        }

    pressure = detect_resource_pressure()
    disk = get_disk_usage()

    return {
        "status": "ok",
        "keyless_mode": True,
        "model_loop_mode": "vm_browser",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "providers": results,
        "resources": {
            "cpu_percent": pressure.get("cpu_percent"),
            "memory_percent": pressure.get("memory_percent"),
            "disk": disk,
            "maxed_out": pressure.get("maxed_out", False) or (disk.get("percent", 0) > 95)
        }
    }
