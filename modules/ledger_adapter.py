"""
Jules Bridge Ledger Adapter
===========================
Bridges Jules Bridge task queues and workers to the central Canonical Mission Ledger
in ~/.academic-command-center/ledger/ with zero breakage to existing bridge routes.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("jules_bridge.ledger_adapter")

# Add service dir of academic-command-center if accessible
_ACC_SERVICE_DIR = Path("C:/Users/S02748217/academic-command-center-the-one--main/service")
if _ACC_SERVICE_DIR.exists() and str(_ACC_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_ACC_SERVICE_DIR))

try:
    import canonical_mission_ledger as ledger
    _LEDGER_AVAILABLE = True
except ImportError:
    _LEDGER_AVAILABLE = False
    logger.warning("canonical_mission_ledger not importable — ledger adapter running in fallback mode")


def sync_task_to_ledger(task_id: str, title: str, task_type: str, url: str = "", deadline: str = "", status: str = "pending", notes: str = "") -> dict[str, Any]:
    """Sync a Jules Bridge task block into the Canonical Mission Ledger."""
    if not _LEDGER_AVAILABLE:
        return {"ok": False, "reason": "Ledger unavailable"}

    payload = {"url": url, "deadline": deadline, "notes": notes, "bridgeTaskId": task_id}
    mission = ledger.create_or_get_mission(
        title or task_id,
        scope=url or task_type,
        task_type=task_type,
        payload=payload,
        created_by="jules_bridge",
    )

    return mission


def acquire_mission_lease(mission_id: str, worker_id: str = "jules_worker") -> tuple[bool, str, dict[str, Any] | None]:
    if not _LEDGER_AVAILABLE:
        return True, "Fallback lease", None
    return ledger.acquire_lease(mission_id, worker_id)


def record_mission_completion(mission_id: str, worker_id: str, ok: bool, summary: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
    if not _LEDGER_AVAILABLE:
        return {"ok": ok}
    return ledger.record_completion(mission_id, worker_id, ok=ok, summary=summary or {}, error=error)
