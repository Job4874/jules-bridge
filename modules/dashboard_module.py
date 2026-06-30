"""Dashboard module — real-time multi-cloud status aggregator.

Collects GCP VM, Azure VM, bridge health, resource pressure, Jules fleet
state, and recent log lines into a single snapshot dict.

Public interface:
    get_dashboard_status() -> dict
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from functools import lru_cache

from modules.vm_manager import detect_resource_pressure

_ROOT = Path(__file__).parent.parent
_LOG_PATH = _ROOT / "bridge.log"
_LAUNCH_STATE = _ROOT / "JULES_LAUNCH_STATE.json"
_COT_LEDGER = _ROOT / "JULES_COT_LEDGER.json"
_WATCH_STATE = _ROOT / "JULES_WATCH_STATE.json"
_ENV_PATH = _ROOT / ".env"

_LOG_TAIL_LINES = 40


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _env_vars() -> dict[str, str]:
    """Read .env file into a dict (no process env side effects)."""
    env: dict[str, str] = {}
    try:
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return env


def _tcp_reachable(host: str, port: int = 22, timeout: float = 3.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _tail_log(n: int = _LOG_TAIL_LINES) -> list[str]:
    """Return the last n lines of bridge.log."""
    try:
        text = _LOG_PATH.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return lines[-n:] if len(lines) >= n else lines
    except Exception:  # pylint: disable=broad-exception-caught
        return []


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _fleet_status() -> dict[str, Any]:
    """Summarise Jules fleet state from persisted JSON files."""
    cot = _read_json(_COT_LEDGER)
    launch = _read_json(_LAUNCH_STATE)
    watch = _read_json(_WATCH_STATE)

    launched = 0
    completed = 0
    pending = 0
    failed = 0
    in_progress = 0
    all_complete = False

    if cot and isinstance(cot, dict):
        launched = cot.get("selected_count", 0)
        completed = cot.get("completed_count", 0)
        pending = cot.get("pending_count", 0)
        all_complete = bool(cot.get("all_complete", False))

    if launch and isinstance(launch, dict):
        rows = launch.get("launched", [])
        if isinstance(rows, list):
            for row in rows:
                s = (row.get("remote_status") or "").lower()
                if s in ("failed",):
                    failed += 1
                elif s in ("in progress", "planning", "awaiting plan", "awaiting user"):
                    in_progress += 1

    sessions_total = 0
    if watch and isinstance(watch, dict):
        sessions_total = watch.get("sessions_checked", 0)

    return {
        "launched": launched,
        "completed": completed,
        "pending": pending,
        "failed": failed,
        "in_progress": in_progress,
        "all_complete": all_complete,
        "sessions_tracked": sessions_total,
    }


def _vm_info(env: dict[str, str]) -> dict[str, Any]:
    """Build status for all known cloud VMs from .env variables."""
    vms: list[dict] = []

    # GCP worker
    gcp_ip = env.get("GCE_WORKER_IP", "")
    gcp_name = env.get("GCE_WORKER_NAME", "jules-offload-worker")
    gcp_project = env.get("GCE_WORKER_PROJECT", "tibin-terminal-2026")
    gcp_zone = env.get("GCE_WORKER_ZONE", "us-central1-a")
    gcp_reachable = _tcp_reachable(gcp_ip) if gcp_ip else False
    vms.append({
        "provider": "GCP",
        "name": gcp_name,
        "ip": gcp_ip or "unknown",
        "project": gcp_project,
        "zone": gcp_zone,
        "reachable": gcp_reachable,
        "status": "online" if gcp_reachable else ("provisioned" if gcp_ip else "not_configured"),
    })

    # Azure workers — scan env for AZURE_WORKER_* keys
    for key, val in env.items():
        if key.startswith("AZURE_WORKER_") and val:
            raw_name = key.replace("AZURE_WORKER_", "").replace("_", "-").lower()
            az_reachable = _tcp_reachable(val)
            vms.append({
                "provider": "Azure",
                "name": raw_name,
                "ip": val,
                "project": "jules-offload-rg",
                "zone": "eastus",
                "reachable": az_reachable,
                "status": "online" if az_reachable else "provisioning",
            })

    return {"vms": vms, "total": len(vms), "online": sum(1 for v in vms if v["reachable"])}


_dashboard_status_cache: dict = {}
# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_dashboard_status(bridge_start_utc: datetime | None = None) -> dict[str, Any]:
    """Aggregate full dashboard status. Never raises."""
    try:
        cache_ttl = int(os.environ.get('DASHBOARD_CACHE_TTL_S', '5'))
        now_ts = time.time()

        if _dashboard_status_cache:
            ts, cached_res = _dashboard_status_cache.get('last', (0, {}))
            if now_ts - ts < cache_ttl:
                cached_res['cache_age_s'] = int(now_ts - ts)
                return cached_res

        now = datetime.now(timezone.utc)
        uptime_s = int((now - bridge_start_utc).total_seconds()) if bridge_start_utc else 0

        env = _env_vars()
        pressure = detect_resource_pressure()
        fleet = _fleet_status()
        cloud = _vm_info(env)
        logs = _tail_log()

        ngrok_url = ""
        # Try to extract ngrok URL from recent logs
        for line in reversed(logs):
            if "ngrok-free.dev" in line or "ngrok.io" in line:
                match = re.search(r"https://[a-z0-9\-]+\.ngrok[a-z.\-]*/", line)
                if match:
                    ngrok_url = match.group(0).rstrip("/")
                    break

        result = {
            "ok": True,
            "timestamp": now.isoformat(),
            "cache_age_s": 0,
            "bridge": {
                "status": "running",
                "uptime_s": uptime_s,
                "uptime_human": _fmt_uptime(uptime_s),
                "ngrok_url": ngrok_url,
                "local_url": "http://127.0.0.1:5000",
            },
            "resource_pressure": {
                "status": pressure.get("status", "unknown"),
                "cpu_percent": pressure.get("cpu_percent"),
                "memory_percent": pressure.get("memory_percent"),
                "maxed_out": pressure.get("maxed_out", False),
                "reasons": pressure.get("reasons", []),
            },
            "cloud": cloud,
            "jules_fleet": fleet,
            "recent_logs": logs,
            "env_keys_present": [
                k for k in ["GEMINI_API_KEY", "GCE_WORKER_IP", "OPENROUTER_API_KEY", "GMAIL_USER"]
                if env.get(k)
            ],
        }
        _dashboard_status_cache['last'] = (now_ts, result)
        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {"ok": False, "error": str(exc)}


def _fmt_uptime(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"
