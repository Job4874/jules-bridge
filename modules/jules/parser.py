from __future__ import annotations
from .models import *
from .utils import *
import hashlib
import re
from pathlib import Path
from typing import Iterable

def parse_task_dump(content: str, source_name: str = "") -> list[JulesTask]:
    """Parse a pasted Jules task dump into normalized task cards.

    Args:
        content: Raw pasted text.
        source_name: Optional label for traceability.

    Returns:
        List of JulesTask dictionaries. Never raises.
    """
    try:
        lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        heading_indexes = [
            idx for idx, line in enumerate(lines)
            if _heading_type(line) is not None
        ]
        tasks: list[JulesTask] = []
        for ordinal, start in enumerate(heading_indexes, start=1):
            end = heading_indexes[ordinal] if ordinal < len(heading_indexes) else len(lines)
            block_lines = lines[start:end]
            prefix_status = _nearest_prefix_status(lines, start)
            suffix_status = _nearest_suffix_status(block_lines)
            status = suffix_status or prefix_status or "unknown"
            task_type = _heading_type(lines[start]) or "unknown"
            file_ref, issue = _extract_file_and_issue(block_lines)
            language = _extract_prefixed(block_lines, "Language:")
            rationale = _extract_prefixed(block_lines, "Rationale:")
            fingerprint = _fingerprint(task_type, file_ref, issue, rationale)
            task_id = f"JT-{ordinal:03d}-{fingerprint[:6]}"
            tasks.append(JulesTask(
                id=task_id,
                ordinal=ordinal,
                fingerprint=fingerprint,
                task_type=task_type,
                status=status,
                source=source_name,
                title=_title_for(task_type, issue, file_ref),
                file=file_ref,
                issue=issue,
                language=language,
                rationale=rationale,
                raw_excerpt="\n".join(_compact_lines(block_lines[:80])),
            ))
        return tasks
    except Exception as exc:  # noqa: BLE001
        return [JulesTask(error=f"parse failed: {exc}", status="error")]


def parse_antigravity_queue(
    content: str,
    source_name: str = "",
    prompt_dir: str = "",
) -> list[JulesTask]:
    """Parse pipe-delimited Antigravity offload queue lines into Jules tasks.

    Expected line format::

        Needs review | Antigravity offload: CODEX_PROMPT.md | repo=C:\\path\\to\\repo

    Args:
        content: Raw queue text.
        source_name: Optional label for traceability.
        prompt_dir: Directory containing Codex prompt markdown files.

    Returns:
        List of JulesTask dictionaries. Never raises.
    """
    try:
        prompt_root = _antigravity_prompt_dir(prompt_dir)
        tasks: list[JulesTask] = []
        ordinal = 0
        for raw_line in (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            match = _ANTIGRAVITY_LINE_RE.match(line)
            if not match:
                continue
            ordinal += 1
            status = _normalize_status(match.group("status")) or "unknown"
            prompt_name = (match.group("prompt") or "").strip()
            repo_path = (match.group("repo") or "").strip()
            prompt_path = prompt_root / prompt_name
            prompt_excerpt = ""
            if prompt_path.is_file():
                prompt_excerpt = prompt_path.read_text(encoding="utf-8", errors="replace")
            elif prompt_name:
                prompt_excerpt = f"(prompt file not found: {prompt_path})"
            title = Path(prompt_name).stem.replace("_", " ") if prompt_name else "Antigravity prompt"
            fingerprint = _fingerprint("antigravity", prompt_name, title, repo_path)
            task_id = f"JT-{ordinal:03d}-{fingerprint[:6]}"
            tasks.append(JulesTask(
                id=task_id,
                ordinal=ordinal,
                fingerprint=fingerprint,
                task_type="antigravity",
                status=status,
                source=source_name,
                title=title,
                file=str(prompt_path),
                issue="Execute Antigravity Codex handover prompt end-to-end",
                language="markdown",
                rationale="Offload large Codex handover work to Jules remote workers.",
                repo_path=repo_path,
                raw_excerpt=prompt_excerpt[:12000],
            ))
        return tasks
    except Exception as exc:  # noqa: BLE001
        return [JulesTask(error=f"antigravity parse failed: {exc}", status="error")]


def _antigravity_prompt_dir(prompt_dir: str = "") -> Path:
    if prompt_dir:
        return Path(prompt_dir)
    configured = os.environ.get("JULES_ANTIGRAVITY_PROMPT_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(_DEFAULT_ANTIGRAVITY_PROMPT_DIR)


def _is_antigravity_queue(content: str) -> bool:
    for raw_line in (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _ANTIGRAVITY_LINE_RE.match(raw_line.strip()):
            return True
    return False


def _heading_type(line: str) -> str | None:
    for task_type, phrase in _TASK_HEADINGS:
        if phrase in line:
            return task_type
    return None


def _normalize_status(line: str) -> str | None:
    clean = (line or "").strip().strip(":")
    lower = clean.lower()
    if lower == "needs review":
        return "needs_review"
    if lower == "ready for review":
        return "ready_for_review"
    if lower == "failed":
        return "failed"
    if lower == "complete" or lower.startswith("completed "):
        return "complete"
    return None


def _nearest_prefix_status(lines: list[str], start_index: int) -> str | None:
    for idx in range(start_index - 1, max(-1, start_index - 6), -1):
        status = _normalize_status(lines[idx])
        if status:
            return status
        if lines[idx].strip() and _heading_type(lines[idx]):
            break
    return None


def _nearest_suffix_status(block_lines: list[str]) -> str | None:
    for line in reversed(block_lines):
        status = _normalize_status(line)
        if status:
            return status
    return None


def _extract_file_and_issue(block_lines: list[str]) -> tuple[str, str]:
    for line in block_lines:
        if "File:" not in line:
            continue
        match = re.search(r"File:\s*(?P<file>.*?)(?:\s+Issue:\s*(?P<issue>.*))?$", line)
        if match:
            return (
                (match.group("file") or "").strip(),
                (match.group("issue") or "").strip(),
            )
    return "", ""


def _extract_prefixed(block_lines: list[str], prefix: str) -> str:
    for line in block_lines:
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()
    return ""


def _title_for(task_type: str, issue: str, file_ref: str) -> str:
    if issue:
        return issue
    if file_ref:
        return f"{task_type.replace('_', ' ').title()} for {file_ref}"
    return task_type.replace("_", " ").title()


def _fingerprint(*parts: str) -> str:
    material = "\n".join(part or "" for part in parts)
    return hashlib.sha1(material.encode("utf-8", errors="replace")).hexdigest()[:12]


def _compact_lines(lines: Iterable[str]) -> list[str]:
    compact: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        compact.append(line.rstrip())
        previous_blank = blank
    return compact


def _count_statuses(tasks: Iterable[JulesTask]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _dedupe_tasks(tasks: Iterable[JulesTask]) -> list[JulesTask]:
    """Keep one card per fingerprint, preferring the most urgent status."""
    best: dict[str, JulesTask] = {}
    for task in tasks:
        fingerprint = str(task.get("fingerprint") or task.get("id") or "")
        if not fingerprint:
            fingerprint = _fingerprint(str(task.get("title", "")), str(task.get("ordinal", "")))
        current = best.get(fingerprint)
        if current is None:
            best[fingerprint] = task
            continue
        task_priority = _STATUS_PRIORITY.get(str(task.get("status")), 99)
        current_priority = _STATUS_PRIORITY.get(str(current.get("status")), 99)
        if task_priority < current_priority:
            best[fingerprint] = task
    return list(best.values())


def _status_filter(include_statuses: str | Iterable[str] | None) -> tuple[str, ...]:
    if include_statuses is None or include_statuses == "":
        return _DEFAULT_INCLUDED_STATUSES
    if isinstance(include_statuses, str):
        values = [item.strip() for item in include_statuses.split(",")]
    else:
        values = [str(item).strip() for item in include_statuses]
    normalized = tuple(value for value in values if value)
    return normalized or _DEFAULT_INCLUDED_STATUSES


def _select_tasks(
    tasks: Iterable[JulesTask],
    statuses: Iterable[str],
    max_instances: int,
) -> list[JulesTask]:
    allowed = set(statuses)
    eligible = [
        task for task in _dedupe_tasks(tasks)
        if task.get("status", "unknown") in allowed
    ]
    eligible.sort(key=lambda task: (
        _STATUS_PRIORITY.get(str(task.get("status")), 99),
        int(task.get("ordinal", 0)),
    ))
    return eligible[:max_instances]


def _packet_id_from_path(path: str) -> str:
    name = Path(path).name
    match = re.search(r"(JT-\d{3}-[A-Za-z0-9]+)", name)
    if match:
        return match.group(1)
    match = re.search(r"(JT-\d{3})", name)
    return match.group(1) if match else ""


def _extract_packet_ids(text: str) -> list[str]:
    candidates = re.findall(r"\bJT-\d{3}(?:-[A-Za-z0-9]+)?\b", text or "")
    return _merge_unique([], candidates)
