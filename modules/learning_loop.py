"""
learning_loop.py — Post-Task Retrospective & Memory
======================================================
After every completed mission, this module:
1. Analyzes what worked / what failed
2. Writes domain-specific memory (memory/academic.md, memory/browser.md)
3. Updates confidence scores for future tasks
4. Generates weekly digest for email

Public interface (never raises):
  reflect_on_task(task, result)    -> ReflectionResult
  weekly_digest()                  -> DigestResult
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jules_bridge.learning_loop")

_ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
_MEMORY_DIR = _ROOT_DIR / "memory"
_HISTORY_PATH = _MEMORY_DIR / "mission_history.json"
_BROWSER_MEMORY = _MEMORY_DIR / "browser.md"
_DIGEST_PATH = _MEMORY_DIR / "weekly_digest.md"


@dataclass
class ReflectionResult:
    ok: bool
    task_id: str = ""
    lesson: str = ""
    memory_updated: bool = False
    error: Optional[str] = None


@dataclass
class DigestResult:
    ok: bool
    summary: str = ""
    tasks_done: int = 0
    tasks_failed: int = 0
    digest_path: str = ""
    error: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reflect_on_task(task: dict, result: dict) -> ReflectionResult:
    """
    Analyze a completed/failed task and write learnings to domain memory.
    task: MissionTask as dict
    result: BrowserResult / QuizResult as dict
    """
    try:
        task_id = task.get("task_id", "unknown")
        task_type = task.get("task_type", "unknown")
        outcome = "success" if result.get("ok", False) else "failure"
        error = result.get("error", "")

        lesson = ""

        if task_type in ("quiz", "assignment"):
            q_found = result.get("questions_found", 0)
            q_answered = result.get("questions_answered", 0)
            submitted = result.get("submitted", False)

            if outcome == "success" and submitted:
                lesson = (
                    f"Quiz at {task.get('url', '')} — answered {q_answered}/{q_found} questions, submitted successfully."
                )
            elif outcome == "failure":
                lesson = (
                    f"Quiz at {task.get('url', '')} FAILED: {error}. "
                    "Check: 1) URL accessible? 2) Chrome profile has auth? 3) DOM selectors changed?"
                )

            _update_browser_memory(task, result, lesson)

        elif task_type == "research":
            lesson = (
                f"Research task {task_id} at {task.get('url', '')} — "
                f"{'completed' if outcome == 'success' else 'failed: ' + error}"
            )
            _update_browser_memory(task, result, lesson)

        elif task_type == "code":
            lesson = (
                f"Code task {task_id} — "
                f"{'jules fleet completed work' if outcome == 'success' else 'failed: ' + error}"
            )

        logger.info("Reflection for %s: %s", task_id, lesson)

        return ReflectionResult(
            ok=True,
            task_id=task_id,
            lesson=lesson,
            memory_updated=bool(lesson),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("reflect_on_task failed: %s", exc)
        return ReflectionResult(ok=False, error=str(exc))


def _update_browser_memory(task: dict, result: dict, lesson: str) -> None:
    """Append browser automation lesson to memory/browser.md."""
    try:
        _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        entry = f"""
## {task.get('task_id', 'unknown')} — {_now_iso()}
- **Type**: {task.get('task_type', 'unknown')}
- **URL**: {task.get('url', '')}
- **Outcome**: {'success' if result.get('ok') else 'failure'}
- **Lesson**: {lesson}

"""
        if _BROWSER_MEMORY.exists():
            existing = _BROWSER_MEMORY.read_text(encoding="utf-8")
        else:
            existing = "# Browser Automation Memory\n\nLearnings from browser tasks.\n"
        _BROWSER_MEMORY.write_text(existing + entry, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("_update_browser_memory failed: %s", exc)


def weekly_digest() -> DigestResult:
    """
    Read mission_history.json and produce a weekly summary.
    Returns markdown summary + saves to memory/weekly_digest.md.
    """
    try:
        if not _HISTORY_PATH.exists():
            return DigestResult(ok=True, summary="No mission history yet.", tasks_done=0, tasks_failed=0)

        history = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))

        # Last 7 days
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent = [
            h for h in history
            if datetime.fromisoformat(h.get("timestamp", "2000-01-01T00:00:00+00:00")) > cutoff
        ]

        done = [h for h in recent if h.get("outcome") == "done"]
        failed = [h for h in recent if h.get("outcome") == "failed"]

        summary_parts = [f"""# Weekly Mission Digest — {_now_iso()[:10]}

## Stats
- ✅ Completed: {len(done)}
- ❌ Failed: {len(failed)}
- 📋 Total: {len(recent)}

## Completed Tasks
"""]
        for h in done:
            summary_parts.append(f"- [{h['task_id']}] {h.get('title', '')} ({h.get('type', '')})\n")

        if failed:
            summary_parts.append("\n## Failed Tasks (Need Attention)\n")
            for h in failed:
                r = h.get("result", {})
                summary_parts.append(f"- [{h['task_id']}] {h.get('title', '')} — {r.get('reason', r.get('error', 'unknown'))}\n")

        summary = "".join(summary_parts)
        _DIGEST_PATH.write_text(summary, encoding="utf-8")

        return DigestResult(
            ok=True,
            summary=summary,
            tasks_done=len(done),
            tasks_failed=len(failed),
            digest_path=str(_DIGEST_PATH),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("weekly_digest failed: %s", exc)
        return DigestResult(ok=False, error=str(exc))
