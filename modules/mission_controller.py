"""
mission_controller.py — F1 Race Engineer
=========================================
Reads MISSION_QUEUE.md, picks the next pending task, routes it to the right
agent (playwright_agent, jules_fleet, cursor, claude, or self), and tracks
active/completed missions in ACTIVE_MISSION.md.

Public interface (never raises):
  load_queue()              -> MissionQueue
  pick_next_task(queue)     -> MissionTask | None
  mark_task_active(task)    -> None
  mark_task_done(task, result) -> None
  mark_task_failed(task, reason) -> None
  run_mission_cycle()       -> MissionCycleResult
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from modules import ledger_adapter
except ImportError:
    import ledger_adapter  # type: ignore[no-redef]

logger = logging.getLogger("jules_bridge.mission_controller")

_ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
_QUEUE_PATH = _ROOT_DIR / "jules_inbox" / "MISSION_QUEUE.md"
_ACTIVE_PATH = _ROOT_DIR / "jules_inbox" / "ACTIVE_MISSION.md"
_HISTORY_PATH = _ROOT_DIR / "memory" / "mission_history.json"

AGENT_MAP = {
    "playwright_agent": "browser",
    "jules_fleet": "jules",
    "cursor": "cursor",
    "claude": "claude",
    "self": "self",
}


@dataclass
class MissionTask:
    task_id: str
    task_type: str  # quiz | research | code | form | email | trading
    title: str
    url: str
    deadline: str
    assigned_to: str
    status: str  # pending | active | done | failed
    notes: str = ""


@dataclass
class MissionQueue:
    tasks: list = field(default_factory=list)
    pending_count: int = 0
    active_count: int = 0
    done_count: int = 0
    parsed_at: str = ""


@dataclass
class MissionCycleResult:
    ok: bool
    active_task: Optional[dict] = None
    queue_summary: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_task_block(block: str) -> Optional[MissionTask]:
    """Parse a single ## TASK-NNN markdown block into a MissionTask."""
    try:
        task_id_match = re.search(r"## (TASK-\w+)", block)
        if not task_id_match:
            return None
        task_id = task_id_match.group(1)

        def _field(name: str, default: str = "") -> str:
            m = re.search(rf"\*\*{name}\*\*\s*:\s*(.+)", block)
            return m.group(1).strip() if m else default

        return MissionTask(
            task_id=task_id,
            task_type=_field("type", "unknown"),
            title=_field("title", task_id),
            url=_field("url", ""),
            deadline=_field("deadline", ""),
            assigned_to=_field("assigned_to", "self"),
            status=_field("status", "pending"),
            notes=_field("notes", ""),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse task block: %s", exc)
        return None


def load_queue() -> MissionQueue:
    """Read MISSION_QUEUE.md and return a structured queue."""
    result = MissionQueue(parsed_at=_now_iso())
    try:
        if not _QUEUE_PATH.exists():
            result.error = "MISSION_QUEUE.md not found"  # type: ignore[attr-defined]
            return result

        content = _QUEUE_PATH.read_text(encoding="utf-8")
        # Split on ## TASK- headers
        blocks = re.split(r"\n(?=## TASK-)", content)
        for block in blocks:
            if not block.strip().startswith("## TASK-"):
                continue
            task = _parse_task_block(block)
            if task is None:
                continue
            result.tasks.append(task)
            if task.status == "pending":
                result.pending_count += 1
            elif task.status == "active":
                result.active_count += 1
            elif task.status == "done":
                result.done_count += 1

        logger.info(
            "Mission queue loaded: %d pending, %d active, %d done",
            result.pending_count, result.active_count, result.done_count
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("load_queue failed: %s", exc)
        result.error = str(exc)  # type: ignore[attr-defined]
    return result


def pick_next_task(queue: MissionQueue) -> Optional[MissionTask]:
    """Return the highest-priority pending task, or None if queue is clear."""
    # Priority: deadline-aware (non-'daily'/'weekly' closest deadline first)
    pending = [t for t in queue.tasks if t.status == "pending"]
    if not pending:
        return None

    def _deadline_sort_key(t: MissionTask):
        try:
            dt = datetime.fromisoformat(t.deadline)
            # Ensure timezone-aware so mixed comparison never crashes
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return datetime(9999, 12, 31, tzinfo=timezone.utc)

    timed = [t for t in pending if t.deadline not in ("daily", "weekly", "")]
    untimed = [t for t in pending if t.deadline in ("daily", "weekly", "")]
    sorted_timed = sorted(timed, key=_deadline_sort_key)
    return (sorted_timed + untimed)[0]


def _update_queue_status(task_id: str, new_status: str) -> None:
    """Rewrite the status field for a task in MISSION_QUEUE.md in place."""
    try:
        content = _QUEUE_PATH.read_text(encoding="utf-8")
        # Replace only the status line within the matching task block
        pattern = rf"(## {re.escape(task_id)}.*?- \*\*status\*\*: )(\w+)"
        updated = re.sub(pattern, rf"\g<1>{new_status}", content, count=1, flags=re.DOTALL)
        _QUEUE_PATH.write_text(updated, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("_update_queue_status failed for %s: %s", task_id, exc)


def mark_task_active(task: MissionTask) -> None:
    """Write ACTIVE_MISSION.md and update queue status."""
    try:
        _update_queue_status(task.task_id, "active")
        m = ledger_adapter.sync_task_to_ledger(task.task_id, task.title, task.task_type, task.url, task.deadline, "active", task.notes)
        if m and isinstance(m, dict) and m.get("missionId"):
            ledger_adapter.acquire_mission_lease(m["missionId"], task.assigned_to or "jules_worker")
        content = f"""# ACTIVE MISSION — {task.task_id}

- **Started**: {_now_iso()}
- **Type**: {task.task_type}
- **Title**: {task.title}
- **URL**: {task.url}
- **Assigned to**: {task.assigned_to}
- **Deadline**: {task.deadline}
- **Notes**: {task.notes}

## Status
Working...
"""
        _ACTIVE_PATH.write_text(content, encoding="utf-8")
        logger.info("Mission active: %s — %s", task.task_id, task.title)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mark_task_active failed: %s", exc)


def mark_task_done(task: MissionTask, result: dict) -> None:
    """Mark task done in queue, append to history."""
    try:
        _update_queue_status(task.task_id, "done")
        _append_history(task, "done", result)
        m = ledger_adapter.sync_task_to_ledger(task.task_id, task.title, task.task_type, task.url, task.deadline, "done", task.notes)
        if m and isinstance(m, dict) and m.get("missionId"):
            ledger_adapter.record_mission_completion(m["missionId"], task.assigned_to or "jules_worker", ok=True, summary=result)
        content = f"""# MISSION COMPLETE — {task.task_id}

- **Completed**: {_now_iso()}
- **Type**: {task.task_type}
- **Title**: {task.title}
- **Result**: {json.dumps(result, indent=2)}
"""
        _ACTIVE_PATH.write_text(content, encoding="utf-8")
        logger.info("Mission done: %s", task.task_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mark_task_done failed: %s", exc)


def mark_task_failed(task: MissionTask, reason: str) -> None:
    """Mark task failed in queue, append to history."""
    try:
        _update_queue_status(task.task_id, "failed")
        _append_history(task, "failed", {"reason": reason})
        m = ledger_adapter.sync_task_to_ledger(task.task_id, task.title, task.task_type, task.url, task.deadline, "failed", task.notes)
        if m and isinstance(m, dict) and m.get("missionId"):
            ledger_adapter.record_mission_completion(m["missionId"], task.assigned_to or "jules_worker", ok=False, error=reason)
        logger.warning("Mission failed: %s — %s", task.task_id, reason)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mark_task_failed failed: %s", exc)


def _append_history(task: MissionTask, outcome: str, result: dict) -> None:
    try:
        _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if _HISTORY_PATH.exists():
            try:
                history = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                history = []
        history.append({
            "task_id": task.task_id,
            "title": task.title,
            "type": task.task_type,
            "assigned_to": task.assigned_to,
            "outcome": outcome,
            "timestamp": _now_iso(),
            "result": result,
        })
        _HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("_append_history failed: %s", exc)


def run_mission_cycle() -> MissionCycleResult:
    """
    One full cycle: load queue → pick task → mark active → return task info.
    The actual execution is done by the caller (bridge route or autopilot).
    """
    try:
        queue = load_queue()
        task = pick_next_task(queue)

        if task is None:
            logger.info("Mission queue is clear — nothing to do.")
            return MissionCycleResult(
                ok=True,
                active_task=None,
                queue_summary={
                    "pending": queue.pending_count,
                    "active": queue.active_count,
                    "done": queue.done_count,
                },
                timestamp=_now_iso(),
            )

        mark_task_active(task)
        return MissionCycleResult(
            ok=True,
            active_task=asdict(task),
            queue_summary={
                "pending": queue.pending_count,
                "active": queue.active_count,
                "done": queue.done_count,
            },
            timestamp=_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_mission_cycle failed: %s", exc)
        return MissionCycleResult(ok=False, error=str(exc), timestamp=_now_iso())
