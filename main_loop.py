"""Permanent orchestrator daemon for the Two-Node Zero-Trust loop.

This module runs an infinite loop that:
  1. Monitors local memory/CPU pressure.
  2. Boots a secondary VM if pressure is high and the operator allows it.
  3. Polls the local bridge /inbox/read route for new tasks.
  4. Dispatches tasks to the router controller.
  5. Writes a watchdog heartbeat to memory/system_heartbeat.md every 60s.

Run as a background daemon:
    python -m main_loop

Or from PowerShell:
    Start-Process -FilePath python -ArgumentList "-m", "main_loop" -WindowStyle Hidden
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure the repo root is importable when running as python -m main_loop
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.vm_manager import boot_secondary_vm, VMBootError
from modules.router import dispatch

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_BRIDGE_URL = "http://127.0.0.1:5000"
_DEFAULT_INBOX_ENDPOINT = "/inbox/read"
_MEMORY_THRESHOLD_PERCENT = 85.0
_LOOP_INTERVAL_SECONDS = 30
_HEARTBEAT_INTERVAL_SECONDS = 60
_HEARTBEAT_PATH = os.path.join(PROJECT_ROOT, "memory", "system_heartbeat.md")

LOGGER = logging.getLogger("jules_bridge.orchestrator_daemon")


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class DaemonIterationResult(dict):
    """Result of one daemon loop iteration.

    Keys:
      timestamp_utc (str): ISO timestamp
      memory_percent (float): observed local memory pressure
      vm_action (str): outcome of VM scaling check
      inbox_status (str): ok / no_task / error
      routed (dict | None): dispatched task result
      heartbeat (str): heartbeat outcome
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_memory_dir() -> None:
    os.makedirs(os.path.dirname(_HEARTBEAT_PATH), exist_ok=True)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bridge_url() -> str:
    return os.environ.get("JULES_BRIDGE_URL", _DEFAULT_BRIDGE_URL).rstrip("/")


def _allow_vm_boot() -> bool:
    return os.environ.get("JULES_ALLOW_VM_BOOT", "").lower() in ("1", "true", "yes")


def _try_import_requests() -> Any:
    try:
        import requests  # noqa: PLC0415
        return requests
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read_inbox(bridge_url: str = "") -> dict | None:
    """Poll the local bridge /inbox/read route for a new task.

    Args:
        bridge_url: Base URL of the Jules Bridge. Defaults to
            JULES_BRIDGE_URL env var or http://127.0.0.1:5000.

    Returns:
        Task dict if a new message is found and can be parsed, else None.
    """
    requests = _try_import_requests()
    if requests is None:
        LOGGER.warning("requests not installed; inbox polling disabled")
        return None

    url = (bridge_url or _bridge_url()) + _DEFAULT_INBOX_ENDPOINT
    try:
        response = requests.post(url, json={}, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("inbox poll failed: %s", exc)
        return None

    content = payload.get("content", "")
    if not content or payload.get("error"):
        return None

    # The inbox is free-form markdown; treat the whole content as a task
    # with a synthetic type derived from keywords if present.
    task_type = "Routine/UI"
    lowered = content.lower()
    if any(k in lowered for k in ("code", "dev", "refactor", "test")):
        task_type = "Code/Dev"
    elif any(k in lowered for k in ("vm", "scale", "compute", "azure")):
        task_type = "Compute/Scale"

    return {"type": task_type, "source": "inbox", "content": content}


def write_heartbeat(force: bool = False) -> str:
    """Write a watchdog heartbeat entry to memory/system_heartbeat.md.

    Args:
        force: Write even if 60 seconds have not elapsed since last entry.

    Returns:
        "written" if a new entry was appended, "skipped" otherwise.
    """
    _ensure_memory_dir()
    now = _now_utc()

    last_ts: float | None = None
    if os.path.isfile(_HEARTBEAT_PATH):
        try:
            last_ts = os.path.getmtime(_HEARTBEAT_PATH)
        except OSError:
            last_ts = None

    if not force and last_ts is not None:
        if time.time() - last_ts < _HEARTBEAT_INTERVAL_SECONDS:
            return "skipped"

    with open(_HEARTBEAT_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"- {now} | daemon alive | pid={os.getpid()}\n")
    return "written"


def daemon_loop_iteration(
    bridge_url: str = "",
    memory_threshold: float = _MEMORY_THRESHOLD_PERCENT,
    loop_interval: int = _LOOP_INTERVAL_SECONDS,
) -> DaemonIterationResult:
    """Execute a single iteration of the orchestrator daemon.

    Args:
        bridge_url: Optional bridge base URL.
        memory_threshold: Memory percent that triggers VM boot.
        loop_interval: Seconds between iterations (used for logging).

    Returns:
        DaemonIterationResult summarizing the iteration.
    """
    timestamp = _now_utc()
    heartbeat_status = write_heartbeat()

    # 1. Monitor local memory pressure and boot secondary VM if needed.
    vm_action = "no_action"
    memory_percent: float | None = None
    try:
        allow = _allow_vm_boot()
        result = boot_secondary_vm(
            dry_run=not allow,
            allow_vm_boot=allow,
        )
        memory_percent = result.get("memory_percent")
        vm_action = result.get("status", "unknown")
    except VMBootError as exc:
        vm_action = "blocked"
        LOGGER.warning("vm boot blocked: %s", exc)
    except Exception as exc:  # noqa: BLE001
        vm_action = "error"
        LOGGER.warning("vm manager error: %s", exc)

    # 2. Poll inbox for new tasks.
    inbox_status = "no_task"
    task = read_inbox(bridge_url=bridge_url)
    if task is None:
        inbox_status = "error_or_empty"

    # 3. Dispatch any new task to the router.
    routed = None
    if task:
        inbox_status = "task_found"
        routed = dispatch(task)

    LOGGER.info(
        "daemon iteration: memory=%s vm=%s inbox=%s routed=%s heartbeat=%s",
        memory_percent,
        vm_action,
        inbox_status,
        routed,
        heartbeat_status,
    )

    return DaemonIterationResult(
        timestamp_utc=timestamp,
        memory_percent=memory_percent,
        vm_action=vm_action,
        inbox_status=inbox_status,
        routed=dict(routed) if routed else None,
        heartbeat=heartbeat_status,
    )


def start_daemon(
    bridge_url: str = "",
    loop_interval: int = _LOOP_INTERVAL_SECONDS,
) -> None:
    """Run the daemon loop forever until interrupted.

    Args:
        bridge_url: Optional bridge base URL.
        loop_interval: Seconds between iterations.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    LOGGER.info("orchestrator daemon starting; pid=%s", os.getpid())
    write_heartbeat(force=True)

    try:
        while True:
            daemon_loop_iteration(bridge_url=bridge_url)
            time.sleep(loop_interval)
    except KeyboardInterrupt:
        LOGGER.info("orchestrator daemon stopped by operator")


if __name__ == "__main__":
    start_daemon()
