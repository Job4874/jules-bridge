"""Jules task dispatch orchestration.

This module turns pasted Jules review/task dumps into deterministic worker
packets. It does not launch remote Jules sessions; callers can review the
generated launch commands and run them explicitly.

Public interface:
    parse_task_dump(content) -> list[JulesTask]
    build_dispatch(...) -> JulesDispatchResult
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class JulesTask(dict):
    """A normalized Jules task card."""


class JulesDispatchResult(dict):
    """Result of parsing and preparing Jules worker dispatch packets."""


class JulesLaunchResult(dict):
    """Result of launching prepared Jules worker packets."""


class JulesRemoteResult(dict):
    """Result of a Jules remote session CLI query."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "jules_inbox" / "jules_dispatch"
_DEFAULT_STATE_FILE = "JULES_LAUNCH_STATE.json"
_DEFAULT_INCLUDED_STATUSES = ("failed", "needs_review", "ready_for_review", "unknown")
_TASK_HEADINGS = (
    ("testing", "Testing Improvement Task"),
    ("performance", "Performance Optimization Task"),
    ("code_health", "Code Health Improvement Task"),
)
_STATUS_PRIORITY = {
    "failed": 0,
    "needs_review": 1,
    "ready_for_review": 2,
    "unknown": 3,
    "complete": 4,
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

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


def build_dispatch(
    content: str = "",
    source_path: str = "",
    max_instances: int = 4,
    include_statuses: str | Iterable[str] | None = None,
    write_packets: bool = False,
    output_dir: str = "",
    repo_path: str = "",
) -> JulesDispatchResult:
    """Build a dry-run Jules worker dispatch plan.

    Args:
        content: Raw pasted task dump. Optional when source_path is provided.
        source_path: Path to a task dump file.
        max_instances: Maximum worker packets to select.
        include_statuses: Comma string or iterable of normalized statuses.
        write_packets: If true, write packet files and an index under output_dir.
        output_dir: Destination directory for packets. Defaults to jules_inbox/jules_dispatch.
        repo_path: Local repository path workers should use. Empty means current repo default.

    Returns:
        JulesDispatchResult with task counts, selected tasks, packets, and commands.
        Never raises.
    """
    try:
        source_label = source_path or "inline"
        loaded_content = content or ""
        if source_path:
            with open(source_path, "r", encoding="utf-8", errors="replace") as handle:
                loaded_content = handle.read()
        if not loaded_content:
            return JulesDispatchResult(
                error="content or source_path is required",
                source=source_label,
                task_count=0,
                selected_count=0,
                status_counts={},
                selected_tasks=[],
                packet_files=[],
                launch_commands=[],
            )

        max_instances = max(1, int(max_instances or 1))
        statuses = _status_filter(include_statuses)
        tasks = parse_task_dump(loaded_content, source_name=source_label)
        tasks = [task for task in tasks if not task.get("error")]
        status_counts = _count_statuses(tasks)
        selected = _select_tasks(tasks, statuses, max_instances)
        packets = [
            _packet_text(task, repo_path=repo_path, instance_index=index + 1)
            for index, task in enumerate(selected)
        ]
        commands = [
            _launch_command(packet_path=None, task=task, repo_path=repo_path)
            for task in selected
        ]

        packet_files: list[str] = []
        if write_packets:
            packet_files, commands = _write_dispatch_files(
                selected=selected,
                packets=packets,
                commands=commands,
                output_dir=Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR,
                repo_path=repo_path,
                source_label=source_label,
                source_hash=_sha256(loaded_content),
            )

        return JulesDispatchResult(
            source=source_label,
            source_sha256=_sha256(loaded_content),
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            task_count=len(tasks),
            selected_count=len(selected),
            status_counts=status_counts,
            include_statuses=list(statuses),
            max_instances=max_instances,
            write_packets=write_packets,
            output_dir=str(Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR),
            repo_path=repo_path,
            selected_tasks=selected,
            packet_files=packet_files,
            launch_commands=commands,
            note=(
                "Dry-run by default. Commands are generated for explicit operator "
                "launch; no remote Jules sessions were started."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return JulesDispatchResult(
            error=str(exc),
            source=source_path or "inline",
            task_count=0,
            selected_count=0,
            status_counts={},
            selected_tasks=[],
            packet_files=[],
            launch_commands=[],
        )


def launch_packets(
    packet_dir: str = "",
    packet_files: Iterable[str] | None = None,
    repo_path: str = "",
    limit: int = 0,
    dry_run: bool = True,
    timeout_s: int = 120,
    jules_command: str = "jules",
    write_state: bool = True,
    state_path: str = "",
) -> JulesLaunchResult:
    """Launch prepared Jules worker packets with `jules new`.

    Args:
        packet_dir: Directory containing `JT-*.md` packet files.
        packet_files: Explicit packet paths. Overrides packet_dir discovery.
        repo_path: Working directory for `jules new`.
        limit: Optional max packets to launch. 0 means all selected packets.
        dry_run: If true, never invokes the Jules CLI.
        timeout_s: Per-packet CLI timeout.
        jules_command: CLI executable name/path.
        write_state: Write `JULES_LAUNCH_STATE.json` near packet_dir/state_path.
        state_path: Explicit state JSON destination.

    Returns:
        JulesLaunchResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        packets = _resolve_packet_files(packet_dir=packet_dir, packet_files=packet_files)
        if limit and limit > 0:
            packets = packets[:limit]
        results = []
        for packet in packets:
            command = [jules_command, "new"]
            result = {
                "packet": str(packet),
                "command": command,
                "repo_path": repo_path,
                "status": "dry_run" if dry_run else "pending",
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "timed_out": False,
                "session_ids": [],
            }
            if not dry_run:
                packet_text = packet.read_text(encoding="utf-8", errors="replace")
                try:
                    completed = subprocess.run(
                        command,
                        cwd=repo_path or None,
                        input=packet_text,
                        capture_output=True,
                        text=True,
                        timeout=max(1, int(timeout_s or 1)),
                        check=False,
                    )
                    result.update(
                        status="launched" if completed.returncode == 0 else "failed",
                        exit_code=completed.returncode,
                        stdout=completed.stdout or "",
                        stderr=completed.stderr or "",
                        session_ids=_extract_session_ids(
                            f"{completed.stdout or ''}\n{completed.stderr or ''}"
                        ),
                    )
                except subprocess.TimeoutExpired as exc:
                    result.update(
                        status="timeout",
                        timed_out=True,
                        stdout=_coerce_text(exc.stdout),
                        stderr=_coerce_text(exc.stderr),
                    )
                except Exception as exc:  # noqa: BLE001
                    result.update(status="error", stderr=str(exc))
            results.append(result)

        launched_count = sum(1 for item in results if item.get("status") == "launched")
        timeout_count = sum(1 for item in results if item.get("timed_out"))
        payload = JulesLaunchResult(
            generated_at_utc=generated_at,
            dry_run=dry_run,
            packet_dir=str(Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR),
            selected_count=len(packets),
            launched_count=launched_count,
            timeout_count=timeout_count,
            jules_command=jules_command,
            repo_path=repo_path,
            results=results,
            state_path="",
            note=(
                "Dry run only; no remote Jules sessions were started."
                if dry_run
                else "Live launch attempted through the Jules CLI."
            ),
        )
        if write_state:
            destination = _state_path_for(packet_dir=packet_dir, state_path=state_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            payload["state_path"] = str(destination)
        return payload
    except Exception as exc:  # noqa: BLE001
        return JulesLaunchResult(
            error=str(exc),
            generated_at_utc=generated_at,
            dry_run=dry_run,
            selected_count=0,
            launched_count=0,
            timeout_count=0,
            results=[],
        )


def list_remote_sessions(
    jules_command: str = "jules",
    timeout_s: int = 30,
    dry_run: bool = True,
) -> JulesRemoteResult:
    """List remote Jules sessions with a timeout.

    Args:
        jules_command: CLI executable name/path.
        timeout_s: CLI timeout.
        dry_run: If true, do not invoke the CLI.

    Returns:
        JulesRemoteResult. Never raises.
    """
    command = [jules_command, "remote", "list", "--session"]
    if dry_run:
        return JulesRemoteResult(
            dry_run=True,
            command=command,
            status="dry_run",
            exit_code=None,
            stdout="",
            stderr="",
            timed_out=False,
            session_ids=[],
        )
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_s or 1)),
            check=False,
        )
        combined = f"{completed.stdout or ''}\n{completed.stderr or ''}"
        return JulesRemoteResult(
            dry_run=False,
            command=command,
            status="ok" if completed.returncode == 0 else "failed",
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            timed_out=False,
            session_ids=_extract_session_ids(combined),
        )
    except subprocess.TimeoutExpired as exc:
        return JulesRemoteResult(
            dry_run=False,
            command=command,
            status="timeout",
            exit_code=None,
            stdout=_coerce_text(exc.stdout),
            stderr=_coerce_text(exc.stderr),
            timed_out=True,
            session_ids=[],
        )
    except Exception as exc:  # noqa: BLE001
        return JulesRemoteResult(
            dry_run=False,
            command=command,
            status="error",
            exit_code=None,
            stdout="",
            stderr=str(exc),
            timed_out=False,
            session_ids=[],
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

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


def _sha256(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8", errors="replace")).hexdigest()


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


def _slug(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-").lower()
    return safe[:60] or "task"


def _packet_text(task: JulesTask, repo_path: str, instance_index: int) -> str:
    title = task.get("title", "Jules task")
    lines = [
        f"# Jules Worker Packet {task.get('id')}",
        "",
        f"- instance_index: {instance_index}",
        f"- status: {task.get('status', 'unknown')}",
        f"- task_type: {task.get('task_type', 'unknown')}",
        f"- source: {task.get('source', '')}",
        f"- fingerprint: {task.get('fingerprint', '')}",
        f"- repo_path: {repo_path or '(use current repository)'}",
        "",
        "## Objective",
        f"Complete exactly this Jules card: {title}",
        "",
        "## Task Details",
        f"- File: {task.get('file', '') or '(not provided)'}",
        f"- Issue: {task.get('issue', '') or '(not provided)'}",
        f"- Language: {task.get('language', '') or '(not provided)'}",
        f"- Rationale: {task.get('rationale', '') or '(not provided)'}",
        "",
        "## Operating Rules",
        "- Work on one card only; do not opportunistically refactor unrelated code.",
        "- Preserve existing behavior unless the card explicitly asks for behavior change.",
        "- Run the narrowest relevant verification first, then the broader suite if practical.",
        "- Record concrete evidence: commands, test result summaries, hashes, screenshots, or PR links.",
        "- Do not reveal private chain-of-thought. Use a concise rationale, decision log, and evidence checklist instead.",
        "- If blocked, write the blocker, attempted evidence, and the exact next question.",
        "",
        "## Completion report",
        "Write a short report with:",
        "- what changed",
        "- verification performed",
        "- files touched",
        "- whether a PR/commit was created",
        "- next action or blocker",
        "",
        "## Raw Card Excerpt",
        "```text",
        str(task.get("raw_excerpt", "")).strip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def _launch_command(packet_path: str | None, task: JulesTask, repo_path: str) -> str:
    prompt = f"{task.get('id')}: {task.get('title')}"
    if packet_path:
        packet = _ps_quote(packet_path)
        if repo_path:
            repo = _ps_quote(repo_path)
            return f"Push-Location {repo}; Get-Content -Raw -LiteralPath {packet} | jules new; Pop-Location"
        return f"Get-Content -Raw -LiteralPath {packet} | jules new"
    if repo_path:
        repo = _ps_quote(repo_path)
        return f"Push-Location {repo}; jules new {_ps_quote(prompt)}; Pop-Location"
    return f"jules new {_ps_quote(prompt)}"


def _write_dispatch_files(
    selected: list[JulesTask],
    packets: list[str],
    commands: list[str],
    output_dir: Path,
    repo_path: str,
    source_label: str,
    source_hash: str,
) -> tuple[list[str], list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_previous_dispatch(output_dir)
    packet_files: list[str] = []
    packet_commands: list[str] = []
    for task, packet in zip(selected, packets):
        filename = f"{task.get('id')}-{_slug(str(task.get('title', 'task')))}.md"
        path = output_dir / filename
        path.write_text(packet, encoding="utf-8")
        packet_files.append(str(path))
        packet_commands.append(_launch_command(str(path), task, repo_path))

    index = _dispatch_index(selected, packet_files, source_label, source_hash, repo_path)
    (output_dir / "JULES_DISPATCH_INDEX.md").write_text(index, encoding="utf-8")
    launch_script = _launch_script(packet_commands)
    (output_dir / "jules_launch_commands.ps1").write_text(launch_script, encoding="utf-8")
    return packet_files, packet_commands


def _clear_previous_dispatch(output_dir: Path) -> None:
    """Remove stale generated files from a prior dispatch run."""
    for path in output_dir.glob("JT-*.md"):
        if path.is_file():
            path.unlink()


def _resolve_packet_files(
    packet_dir: str = "",
    packet_files: Iterable[str] | None = None,
) -> list[Path]:
    if packet_files:
        paths = [Path(path) for path in packet_files if str(path).strip()]
    else:
        base = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
        paths = sorted(base.glob("JT-*.md"))
    return [path for path in paths if path.is_file()]


def _state_path_for(packet_dir: str, state_path: str) -> Path:
    if state_path:
        return Path(state_path)
    base = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
    return base / _DEFAULT_STATE_FILE


def _extract_session_ids(text: str) -> list[str]:
    candidates = re.findall(r"\b\d{6,}\b", text or "")
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        if candidate not in seen:
            result.append(candidate)
            seen.add(candidate)
    return result


def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
    for name in ("JULES_DISPATCH_INDEX.md", "jules_launch_commands.ps1"):
        path = output_dir / name
        if path.is_file():
            path.unlink()


def _dispatch_index(
    selected: list[JulesTask],
    packet_files: list[str],
    source_label: str,
    source_hash: str,
    repo_path: str,
) -> str:
    lines = [
        "# Jules Dispatch Index",
        "",
        f"- generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        f"- source: {source_label}",
        f"- source_sha256: {source_hash}",
        f"- repo_path: {repo_path or '(use current repository)'}",
        f"- selected_count: {len(selected)}",
        "",
        "| id | status | type | file | issue | packet |",
        "|---|---|---|---|---|---|",
    ]
    for task, packet in zip(selected, packet_files):
        lines.append(
            "| {id} | {status} | {task_type} | {file} | {issue} | {packet} |".format(
                id=task.get("id", ""),
                status=task.get("status", ""),
                task_type=task.get("task_type", ""),
                file=str(task.get("file", "")).replace("|", "\\|"),
                issue=str(task.get("issue", "")).replace("|", "\\|"),
                packet=packet.replace("|", "\\|"),
            )
        )
    lines.extend([
        "",
        "Launch is explicit only. Review `jules_launch_commands.ps1` before running it.",
        "",
    ])
    return "\n".join(lines)


def _launch_script(commands: list[str]) -> str:
    lines = [
        "# Jules launch commands generated by /jules/dispatch.",
        "# Review before running. This script starts remote Jules sessions.",
        "",
        "Set-StrictMode -Version Latest",
        "$ErrorActionPreference = 'Stop'",
        "",
    ]
    for command in commands:
        lines.append(command)
    lines.append("")
    return "\n".join(lines)


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
