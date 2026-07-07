"""Background worker that advances dashboard commands through their lifecycle."""

from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger("jules_bridge.command_worker")

_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()
_worker_lock = threading.Lock()
_bridge_start_utc: datetime | None = None
_worker_started = False
_worker_id = f"dashboard-worker-{uuid.uuid4().hex[:12]}"
_last_tick_at: str | None = None
_last_command_id: str | None = None


def _poll_interval_s() -> float:
    raw = os.environ.get("DASHBOARD_COMMAND_WORKER_INTERVAL_S", "1.0").strip()
    try:
        return max(0.25, float(raw))
    except ValueError:
        return 1.0


def worker_enabled() -> bool:
    raw = os.environ.get("DASHBOARD_COMMAND_WORKER", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _background_running() -> bool:
    return bool(_worker_thread and _worker_thread.is_alive())


def worker_mode() -> str:
    return "background" if _background_running() else "manual_tick"


def worker_status() -> dict[str, Any]:
    from modules.dashboard_commands import get_command_status_counts  # pylint: disable=import-outside-toplevel

    counts = get_command_status_counts()
    return {
        "ok": True,
        "workerId": _worker_id,
        "enabled": worker_enabled(),
        "mode": worker_mode(),
        "pendingCount": counts["pendingCount"],
        "runningCount": counts["runningCount"],
        "terminalCount": counts["terminalCount"],
        "lastTickAt": _last_tick_at,
        "lastCommandId": _last_command_id,
        "running": _background_running(),
        "poll_interval_s": _poll_interval_s(),
    }


def tick_command_worker(*, bridge_start_utc: datetime | None = None, limit: int = 5) -> dict[str, Any]:
    """Process admitted commands once and return deterministic tick counts."""
    global _last_tick_at, _last_command_id  # pylint: disable=global-statement

    from modules.dashboard_commands import process_pending_commands  # pylint: disable=import-outside-toplevel

    with _worker_lock:
        result = process_pending_commands(bridge_start_utc=bridge_start_utc, limit=limit)

    _last_tick_at = datetime.now(timezone.utc).isoformat()
    processed_commands = result.get("processed") if isinstance(result.get("processed"), list) else []
    if processed_commands:
        _last_command_id = str(processed_commands[-1].get("commandId") or "") or _last_command_id

    return {
        "ok": True,
        "processed": int(result.get("processedCount", result.get("count", 0))),
        "skipped": int(result.get("skipped", 0)),
        "succeeded": int(result.get("succeeded", 0)),
        "failed": int(result.get("failed", 0)),
        "blocked": int(result.get("blocked", 0)),
        "not_implemented": int(result.get("not_implemented", 0)),
        "lastTickAt": _last_tick_at,
        "lastCommandId": _last_command_id,
    }


def _worker_loop() -> None:
    from modules.dashboard_commands import process_pending_commands  # pylint: disable=import-outside-toplevel

    while not _worker_stop.is_set():
        try:
            tick_command_worker(bridge_start_utc=_bridge_start_utc, limit=5)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            LOGGER.exception("command worker tick failed: %s", exc)
        _worker_stop.wait(_poll_interval_s())


def start_command_worker(*, bridge_start_utc: datetime | None = None) -> dict[str, Any]:
    """Start the dashboard command worker thread if explicitly enabled."""
    global _worker_thread, _bridge_start_utc, _worker_started  # pylint: disable=global-statement

    _bridge_start_utc = bridge_start_utc
    if not worker_enabled():
        return {**worker_status(), "started": False, "reason": "disabled"}

    if _worker_thread and _worker_thread.is_alive():
        return {**worker_status(), "started": False, "reason": "already_running"}

    _worker_stop.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name="dashboard-command-worker",
        daemon=True,
    )
    _worker_thread.start()
    _worker_started = True
    LOGGER.info("dashboard command worker started (poll=%ss)", _poll_interval_s())
    return {**worker_status(), "started": True}


def stop_command_worker() -> dict[str, Any]:
    """Stop the dashboard command worker thread."""
    global _worker_thread  # pylint: disable=global-statement

    _worker_stop.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5.0)
    _worker_thread = None
    return worker_status()
