"""Jules task dispatch orchestration.

This module turns pasted Jules review/task dumps into deterministic worker
packets and can launch those packets through the Jules CLI when explicitly
called with dry_run=False.

Public interface:
    parse_task_dump(content) -> list[JulesTask]
    build_dispatch(...) -> JulesDispatchResult
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import jules_api


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


class JulesPreflightResult(dict):
    """Jules CLI installation, auth, and remote-readiness diagnostic."""


class JulesPullResult(dict):
    """Result of pulling one remote Jules session."""


class JulesCotResult(dict):
    """Completion-of-task ledger for prepared Jules packets."""


class JulesCycleResult(dict):
    """End-to-end Jules dispatch, launch, pull, and COT cycle result."""


class JulesWatchResult(dict):
    """Bounded Jules polling, pull, and completion-of-task watch result."""


class JulesFleetResult(dict):
    """One Jules worker-fleet scaling cycle result."""


class JulesFleetWatchResult(dict):
    """Bounded Jules fleet scaling, polling, pull, and COT watch result."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "jules_inbox" / "jules_dispatch"
_DEFAULT_STATE_FILE = "JULES_LAUNCH_STATE.json"
_DEFAULT_PULL_DIR = "JULES_REMOTE_PULLS"
_DEFAULT_COT_DIR = "JULES_COT_REPORTS"
_DEFAULT_COT_LEDGER = "JULES_COT_LEDGER.md"
_DEFAULT_CYCLE_STATE = "JULES_CYCLE_STATE.json"
_DEFAULT_PREFLIGHT_STATE = "JULES_PREFLIGHT.json"
_DEFAULT_WATCH_STATE = "JULES_WATCH_STATE.json"
_DEFAULT_FLEET_STATE = "JULES_FLEET_STATE.json"
_DEFAULT_FLEET_WATCH_STATE = "JULES_FLEET_WATCH_STATE.json"
_STALE_UNKNOWN_REMOTE_SECONDS = 10 * 60
_DEFAULT_INCLUDED_STATUSES = ("failed", "needs_review", "ready_for_review", "unknown")
_DEFAULT_ANTIGRAVITY_PROMPT_DIR = (
    r"C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover"
    r"\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS"
)
_ANTIGRAVITY_LINE_RE = re.compile(
    r"^(?P<status>[^|]+)\|\s*Antigravity offload:\s*(?P<prompt>[^|]+?)\s*\|\s*repo=(?P<repo>.+?)\s*$",
    re.IGNORECASE,
)
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
_COMPLETED_COT_STATUSES = {"completed_reported", "pulled_output_reported"}


# ---------------------------------------------------------------------------
# Public interface
_session_list_cache = {}
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
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
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
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return [JulesTask(error=f"antigravity parse failed: {exc}", status="error")]


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
        if _is_antigravity_queue(loaded_content):
            tasks = parse_antigravity_queue(loaded_content, source_name=source_label)
        else:
            tasks = parse_task_dump(loaded_content, source_name=source_label)
        tasks = [task for task in tasks if not task.get("error")]
        status_counts = _count_statuses(tasks)
        selected = _select_tasks(tasks, statuses, max_instances)
        packets = [
            _packet_text(
                task,
                repo_path=str(task.get("repo_path") or repo_path),
                instance_index=index + 1,
            )
            for index, task in enumerate(selected)
        ]
        commands = [
            _launch_command(
                packet_path=None,
                task=task,
                repo_path=str(task.get("repo_path") or repo_path),
            )
            for task in selected
        ]

        packet_files: list[str] = []
        if write_packets:
            packet_files, commands = _write_dispatch_files(
                selected=selected,
                packets=packets,
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
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
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
    skip_launched: bool = False,
    force_packet_files: Iterable[str] | None = None,
    preserve_existing_session_ids: bool = False,
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
        skip_launched: Do not relaunch packets already marked launched in state.
        force_packet_files: Explicit packet paths to relaunch even if state says launched.
        preserve_existing_session_ids: Keep older tracked session ids for a packet
            when launching another speculative instance.

    Returns:
        JulesLaunchResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        all_packets = _resolve_packet_files(packet_dir=packet_dir, packet_files=packet_files)
        destination = _state_path_for(
            packet_dir=packet_dir,
            state_path=state_path,
            packet_files=all_packets,
        )
        previous_state = _read_json_file(destination) if write_state or skip_launched else {}
        skipped_launched = _already_launched_packet_keys(previous_state) if skip_launched else set()
        force_keys = {str(Path(path)).lower() for path in force_packet_files or [] if str(path).strip()}
        if force_keys:
            packets = [packet for packet in all_packets if str(packet).lower() in force_keys]
        else:
            packets = [
                packet
                for packet in all_packets
                if str(packet).lower() not in skipped_launched
            ]
        if limit < 0:
            packets = []
        elif limit > 0:
            packets = packets[:limit]
        results = []
        resolved_jules_command = _resolve_cli_command(jules_command)
        use_rest_api = jules_api.is_rest_api_enabled()
        for packet in packets:
            command = ["JULES_REST_API", "sessions.create"] if use_rest_api else [resolved_jules_command, "new"]
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
                if use_rest_api:
                    api_result = jules_api.create_session(
                        prompt=packet_text,
                        title=packet.stem,
                        starting_branch=os.environ.get("JULES_STARTING_BRANCH", ""),
                        timeout_s=timeout_s,
                    )
                    session_ids = list(api_result.get("session_ids", []))
                    result.update(
                        status="launched" if api_result.get("status") == "ok" and session_ids else "failed",
                        exit_code=0 if api_result.get("status") == "ok" and session_ids else 1,
                        stdout=json.dumps(api_result.get("session", {}), ensure_ascii=True),
                        stderr=api_result.get("error", ""),
                        timed_out=False,
                        session_ids=session_ids,
                        rest_api=True,
                        api_result=dict(api_result),
                    )
                else:
                    try:
                        completed = _run_cli_command(
                            command,
                            timeout_s=timeout_s,
                            cwd=repo_path or None,
                            input_text=packet_text,
                        )
                        timed_out = bool(completed.get("timed_out"))
                        exit_code = completed.get("exit_code")
                        combined = f"{completed.get('stdout', '')}\n{completed.get('stderr', '')}"
                        session_ids = _extract_session_ids(combined)
                        result.update(
                            status=(
                                "timeout"
                                if timed_out
                                else "launched" if _launch_succeeded(exit_code, combined, session_ids) else "failed"
                            ),
                            exit_code=exit_code,
                            stdout=completed.get("stdout", ""),
                            stderr=completed.get("stderr", ""),
                            timed_out=timed_out,
                            session_ids=session_ids,
                        )
                    except subprocess.TimeoutExpired as exc:
                        result.update(
                            status="timeout",
                            timed_out=True,
                            stdout=_coerce_text(exc.stdout),
                            stderr=_coerce_text(exc.stderr),
                        )
                    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
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
            resolved_jules_command=resolved_jules_command,
            rest_api=use_rest_api,
            repo_path=repo_path,
            results=results,
            attempt_results=[dict(item) for item in results],
            state_path="",
            attempted_count=len(packets),
            skipped_launched_count=(
                sum(1 for packet in all_packets if str(packet).lower() in skipped_launched)
                if skip_launched and not force_keys
                else 0
            ),
            force_packet_count=len(force_keys),
            preserve_existing_session_ids=preserve_existing_session_ids,
            note=(
                "Dry run only; no remote Jules sessions were started."
                if dry_run
                else "Live launch attempted through the Jules CLI."
            ),
        )
        if write_state:
            merged_results = _merge_launch_results(
                previous_state.get("results", []),
                results,
                all_packets,
                preserve_existing_session_ids=preserve_existing_session_ids,
            )
            payload["results"] = merged_results
            payload["selected_count"] = len(merged_results)
            payload["launched_count"] = sum(1 for item in merged_results if item.get("status") == "launched")
            payload["timeout_count"] = sum(1 for item in merged_results if item.get("timed_out"))
            payload["tracked_count"] = len(merged_results)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            payload["state_path"] = str(destination)
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesLaunchResult(
            error=str(exc),
            generated_at_utc=generated_at,
            dry_run=dry_run,
            selected_count=0,
            launched_count=0,
            timeout_count=0,
            results=[],
        )
_session_list_cache = {}


def list_remote_sessions(
    jules_command: str = "jules",
    timeout_s: int = 30,
    dry_run: bool = True,
    bypass_cache: bool = False,
) -> JulesRemoteResult:
    """List remote Jules sessions with a timeout.

    Args:
        jules_command: CLI executable name/path.
        timeout_s: CLI timeout.
        dry_run: If true, do not invoke the CLI.
        bypass_cache: If true, bypass the in-memory session-list cache.

    Returns:
        JulesRemoteResult. Never raises.
    """
    cache_ttl = int(os.environ.get('JULES_SESSION_CACHE_TTL_S', '30'))
    now = time.time()
    use_rest_api = jules_api.is_rest_api_enabled()
    cache_key = f"rest:{jules_api._config()['base_url']}" if use_rest_api else jules_command

    if not dry_run and not bypass_cache and cache_key in _session_list_cache and cache_ttl > 0:
        ts, cached_res = _session_list_cache[cache_key]
        if now - ts < cache_ttl:
            cached_res['cache_hit'] = True
            return cached_res

    if not dry_run and use_rest_api:
        api_result = jules_api.list_sessions(
            page_size=50,
            timeout_s=timeout_s,
        )
        result = JulesRemoteResult(
            dry_run=False,
            command=["JULES_REST_API", "sessions.list"],
            status="ok" if api_result.get("status") == "ok" else "failed",
            exit_code=0 if api_result.get("status") == "ok" else 1,
            stdout=api_result.get("stdout", ""),
            stderr=api_result.get("error", ""),
            timed_out=False,
            session_ids=api_result.get("session_ids", []),
            jules_command=jules_command,
            resolved_jules_command="JULES_REST_API",
            rest_api=True,
            api_result=dict(api_result),
            cache_hit=False,
        )
        if result.get("status") == "ok":
            _session_list_cache[cache_key] = (now, result)
        return result

    resolved_jules_command = _resolve_cli_command(jules_command)
    command = [resolved_jules_command, "remote", "list", "--session"]
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
            jules_command=jules_command,
            resolved_jules_command=resolved_jules_command,
        )
    try:
        completed = _run_cli_command(
            command,
            timeout_s=timeout_s,
        )
        combined = f"{completed.get('stdout', '')}\n{completed.get('stderr', '')}"
        timed_out = bool(completed.get("timed_out"))
        exit_code = completed.get("exit_code")
        result = JulesRemoteResult(
            dry_run=False,
            command=command,
            status="timeout" if timed_out else "ok" if exit_code == 0 else "failed",
            exit_code=exit_code,
            stdout=completed.get("stdout", ""),
            stderr=completed.get("stderr", ""),
            timed_out=timed_out,
            session_ids=_extract_session_ids(combined),
            jules_command=jules_command,
            resolved_jules_command=resolved_jules_command,
            cache_hit=False,
        )
        if not timed_out and exit_code == 0:
            _session_list_cache[cache_key] = (now, result)
        return result
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
            jules_command=jules_command,
            resolved_jules_command=resolved_jules_command,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesRemoteResult(
            dry_run=False,
            command=command,
            status="error",
            exit_code=None,
            stdout="",
            stderr=str(exc),
            timed_out=False,
            session_ids=[],
            jules_command=jules_command,
            resolved_jules_command=resolved_jules_command,
        )


def jules_preflight(
    jules_command: str = "jules",
    timeout_s: int = 8,
    check_remote: bool = True,
    write_state: bool = True,
    state_path: str = "",
) -> JulesPreflightResult:
    """Diagnose Jules CLI readiness without launching or logging in.

    Args:
        jules_command: CLI executable name/path.
        timeout_s: Timeout for bounded CLI probes.
        check_remote: If true, run `remote list --session`.
        write_state: Persist `JULES_PREFLIGHT.json`.
        state_path: Explicit preflight state path.

    Returns:
        JulesPreflightResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        if jules_api.is_rest_api_requested():
            rest_result = jules_api.jules_api_preflight(
                check_sources=check_remote,
                timeout_s=timeout_s,
            )
            payload = JulesPreflightResult(
                generated_at_utc=generated_at,
                ready=bool(rest_result.get("ready")),
                likely_blocker=rest_result.get("likely_blocker", ""),
                jules_command=jules_command,
                resolved_jules_command="JULES_REST_API",
                preferred_jules_command="JULES_REST_API",
                candidate_commands=[],
                version={
                    "status": "skipped",
                    "note": "JULES_USE_REST_API=1; CLI version probe skipped.",
                },
                remote=dict(rest_result),
                auth_indicators={
                    "api_key_present": bool(rest_result.get("api_key_present")),
                    "source": rest_result.get("source", ""),
                    "base_url": rest_result.get("base_url", ""),
                },
                login_command=[],
                rest_api=True,
                state_path="",
                note=(
                    "REST preflight is diagnostic only; it lists configured "
                    "sources and does not create sessions."
                ),
            )
            if write_state:
                destination = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PREFLIGHT_STATE
                destination.parent.mkdir(parents=True, exist_ok=True)
                payload["state_path"] = str(destination)
                destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return payload

        resolved = _resolve_cli_command(jules_command)
        candidates = _candidate_jules_commands(jules_command)
        preferred = (
            _preferred_jules_command(candidates, resolved)
            if ((jules_command or "").strip() or "jules").lower() == "jules"
            else resolved
        )
        auth_indicators = _auth_indicators()
        version_result = _run_cli_command(
            [preferred, "version"],
            timeout_s=timeout_s,
        )
        remote_result = JulesRemoteResult(
            dry_run=True,
            status="skipped",
            session_ids=[],
            note="Remote check skipped.",
        )
        if check_remote:
            remote_result = list_remote_sessions(
                jules_command=preferred,
                timeout_s=timeout_s,
                dry_run=False,
            )
        ready = (
            version_result.get("exit_code") == 0
            and (not check_remote or remote_result.get("status") == "ok")
        )
        likely_blocker = _preflight_blocker(version_result, remote_result, auth_indicators, check_remote)
        payload = JulesPreflightResult(
            generated_at_utc=generated_at,
            ready=ready,
            likely_blocker=likely_blocker,
            jules_command=jules_command,
            resolved_jules_command=resolved,
            preferred_jules_command=preferred,
            candidate_commands=candidates,
            version=dict(version_result),
            remote=dict(remote_result),
            auth_indicators=auth_indicators,
            login_command=[preferred, "login", "--no-launch-browser"],
            state_path="",
            note=(
                "Preflight is diagnostic only; it does not run `jules login`, "
                "`jules new`, or `jules remote pull`."
            ),
        )
        if write_state:
            destination = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PREFLIGHT_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesPreflightResult(
            error=str(exc),
            generated_at_utc=generated_at,
            ready=False,
            likely_blocker="preflight_error",
            jules_command=jules_command,
            candidate_commands=[],
            version={},
            remote={},
            auth_indicators={},
            state_path="",
        )


def pull_remote_session(
    session_id: str,
    repo_path: str = "",
    output_dir: str = "",
    dry_run: bool = True,
    timeout_s: int = 120,
    jules_command: str = "jules",
    write_result: bool = True,
) -> JulesPullResult:
    """Pull one remote Jules session with `jules remote pull --session`.

    Args:
        session_id: Jules remote session id.
        repo_path: Working directory for the pull command.
        output_dir: Directory for persisted pull JSON. Defaults under dispatch dir.
        dry_run: If true, never invokes the Jules CLI.
        timeout_s: CLI timeout.
        jules_command: CLI executable name/path.
        write_result: Persist the pull result JSON.

    Returns:
        JulesPullResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    clean_session_id = str(session_id or "").strip()
    try:
        if not clean_session_id:
            return JulesPullResult(
                error="session_id is required",
                generated_at_utc=generated_at,
                dry_run=dry_run,
                session_id=clean_session_id,
                status="error",
                results=[],
            )
        if jules_api.is_rest_api_enabled():
            payload = JulesPullResult(
                generated_at_utc=generated_at,
                dry_run=dry_run,
                session_id=clean_session_id,
                command=["JULES_REST_API", "sessions.get", clean_session_id],
                jules_command=jules_command,
                resolved_jules_command="JULES_REST_API",
                repo_path=repo_path,
                status="dry_run" if dry_run else "pending",
                exit_code=None,
                stdout="",
                stderr="",
                timed_out=False,
                session_ids=[clean_session_id],
                output_path="",
                rest_api=True,
                note=(
                    "Dry run only; REST session snapshot was not fetched."
                    if dry_run
                    else "Live REST session snapshot fetched from Jules API."
                ),
            )
            if not dry_run:
                api_result = jules_api.get_session(
                    clean_session_id,
                    timeout_s=timeout_s,
                )
                completed = bool(api_result.get("completed"))
                completion_note = (
                    "Completion report\nREST session output reported."
                    if completed
                    else "REST session snapshot has no outputs yet."
                )
                payload.update(
                    status="pulled" if api_result.get("status") == "ok" else "failed",
                    exit_code=0 if api_result.get("status") == "ok" else 1,
                    stdout=api_result.get("stdout", ""),
                    stderr=api_result.get("error", ""),
                    session_ids=_merge_unique([clean_session_id], api_result.get("session_ids", [])),
                    api_result=dict(api_result),
                    note=completion_note,
                )
            if write_result:
                destination_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR / _DEFAULT_PULL_DIR
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / f"jules_pull_{_safe_filename(clean_session_id)}.json"
                payload["output_path"] = str(destination)
                destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return payload

        resolved_jules_command = _resolve_cli_command(jules_command)
        command = [resolved_jules_command, "remote", "pull", "--session", clean_session_id]
        payload = JulesPullResult(
            generated_at_utc=generated_at,
            dry_run=dry_run,
            session_id=clean_session_id,
            command=command,
            jules_command=jules_command,
            resolved_jules_command=resolved_jules_command,
            repo_path=repo_path,
            status="dry_run" if dry_run else "pending",
            exit_code=None,
            stdout="",
            stderr="",
            timed_out=False,
            session_ids=[clean_session_id],
            output_path="",
            note=(
                "Dry run only; remote Jules session was not pulled."
                if dry_run
                else "Live pull attempted through the Jules CLI."
            ),
        )
        if not dry_run:
            completed = _run_cli_command(
                command,
                timeout_s=timeout_s,
                cwd=repo_path or None,
            )
            combined = f"{completed.get('stdout', '')}\n{completed.get('stderr', '')}"
            timed_out = bool(completed.get("timed_out"))
            exit_code = completed.get("exit_code")
            payload.update(
                status="timeout" if timed_out else "pulled" if exit_code == 0 else "failed",
                exit_code=exit_code,
                stdout=completed.get("stdout", ""),
                stderr=completed.get("stderr", ""),
                timed_out=timed_out,
                session_ids=_merge_unique([clean_session_id], _extract_session_ids(combined)),
            )
        if write_result:
            destination_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR / _DEFAULT_PULL_DIR
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / f"jules_pull_{_safe_filename(clean_session_id)}.json"
            payload["output_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesPullResult(
            error=str(exc),
            generated_at_utc=generated_at,
            dry_run=dry_run,
            session_id=clean_session_id,
            status="error",
            exit_code=None,
            stdout="",
            stderr=str(exc),
            timed_out=False,
            session_ids=[clean_session_id] if clean_session_id else [],
            output_path="",
        )


def build_cot_ledger(
    packet_dir: str = "",
    launch_state_path: str = "",
    report_dir: str = "",
    output_path: str = "",
    write_ledger: bool = True,
) -> JulesCotResult:
    """Build a completion-of-task ledger from Jules launch/pull artifacts.

    Args:
        packet_dir: Directory containing packets and launch state.
        launch_state_path: Explicit `JULES_LAUNCH_STATE.json` path.
        report_dir: Directory containing completion reports or pull JSON files.
        output_path: Markdown ledger destination.
        write_ledger: Persist markdown and JSON ledger artifacts.

    Returns:
        JulesCotResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        base_dir = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
        state_path = Path(launch_state_path) if launch_state_path else base_dir / _DEFAULT_STATE_FILE
        state = _read_json_file(state_path)
        rows = _cot_rows_from_state(state, base_dir)
        if not rows:
            return JulesCotResult(
                error="no launch state or packet files found",
                generated_at_utc=generated_at,
                packet_dir=str(base_dir),
                launch_state_path=str(state_path),
                selected_count=0,
                rows=[],
            )
        reports = _collect_cot_reports(base_dir=base_dir, report_dir=report_dir)
        for row in rows:
            matches = _matching_reports(row, reports)
            row["report_files"] = [match["path"] for match in matches]
            row["cot_status"] = _classify_cot_status(row, matches)
        status_counts = _count_row_statuses(rows)
        completed_count = sum(status_counts.get(status, 0) for status in _COMPLETED_COT_STATUSES)
        blocked_count = sum(count for status, count in status_counts.items() if "blocked" in status)
        pending_count = len(rows) - completed_count - blocked_count
        payload = JulesCotResult(
            generated_at_utc=generated_at,
            packet_dir=str(base_dir),
            launch_state_path=str(state_path),
            report_dir=str(Path(report_dir)) if report_dir else "",
            selected_count=len(rows),
            completed_count=completed_count,
            blocked_count=blocked_count,
            pending_count=max(0, pending_count),
            all_complete=len(rows) > 0 and completed_count == len(rows),
            status_counts=status_counts,
            rows=rows,
            ledger_path="",
            ledger_json_path="",
            note="COT means completion-of-task evidence summaries, not private chain-of-thought.",
        )
        if write_ledger:
            ledger_path = Path(output_path) if output_path else base_dir / _DEFAULT_COT_LEDGER
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            payload["ledger_path"] = str(ledger_path)
            payload["ledger_json_path"] = str(ledger_path.with_suffix(".json"))
            ledger_path.write_text(_cot_ledger_markdown(payload), encoding="utf-8")
            ledger_path.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesCotResult(
            error=str(exc),
            generated_at_utc=generated_at,
            packet_dir=str(Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR),
            selected_count=0,
            rows=[],
        )



def _cycle_dispatch(
    content: str,
    source_path: str,
    max_instances: int,
    include_statuses: str | Iterable[str] | None,
    write_packets: bool,
    base_dir: Path,
    repo_path: str,
    generated_at: str,
) -> JulesDispatchResult:
    if content or source_path:
        return build_dispatch(
            content=content,
            source_path=source_path,
            max_instances=max_instances,
            include_statuses=include_statuses,
            write_packets=write_packets,
            output_dir=str(base_dir),
            repo_path=repo_path,
        )
    packets = _resolve_packet_files(packet_dir=str(base_dir))
    return JulesDispatchResult(
        source="existing_packets",
        generated_at_utc=generated_at,
        task_count=0,
        selected_count=len(packets),
        status_counts={},
        include_statuses=list(_status_filter(include_statuses)),
        max_instances=max_instances,
        write_packets=False,
        output_dir=str(base_dir),
        repo_path=repo_path,
        selected_tasks=[],
        packet_files=[str(packet) for packet in packets],
        launch_commands=[],
        note="No task dump supplied; using existing packet files.",
    )


def _cycle_check_remote(
    check_remote: bool,
    jules_command: str,
    timeout_s: int,
    dry_run: bool,
) -> JulesRemoteResult:
    if check_remote:
        return list_remote_sessions(
            jules_command=jules_command,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )
    return JulesRemoteResult(
        dry_run=True,
        status="skipped",
        session_ids=[],
        note="Remote session check skipped.",
    )


def _cycle_launch(
    base_dir: Path,
    repo_path: str,
    launch: bool,
    launch_limit: int,
    dry_run: bool,
    blockers: list[str],
    require_remote_ready: bool,
    remote_ready: bool,
    timeout_s: int,
    jules_command: str,
    content: str,
    source_path: str,
) -> tuple[dict, JulesLaunchResult, bool]:
    launch_dry_run = dry_run or not launch or bool(blockers) or (require_remote_ready and not remote_ready)
    launch_state_path = base_dir / _DEFAULT_STATE_FILE
    existing_launch_state = _read_json_file(launch_state_path)
    has_existing_launch_state = bool(existing_launch_state.get("results"))
    write_launch_state = launch or bool(content or source_path) or not has_existing_launch_state
    launch_result = launch_packets(
        packet_dir=str(base_dir),
        repo_path=repo_path,
        limit=launch_limit,
        dry_run=launch_dry_run,
        timeout_s=timeout_s,
        jules_command=jules_command,
        write_state=write_launch_state,
        skip_launched=launch,
    )
    return existing_launch_state, launch_result, launch_dry_run


def _cycle_pull(
    base_dir: Path,
    repo_path: str,
    pull: bool,
    session_ids: Iterable[str] | None,
    existing_launch_state: dict,
    launch_result: JulesLaunchResult,
    sessions_result: JulesRemoteResult,
    dry_run: bool,
    require_remote_ready: bool,
    remote_ready: bool,
    timeout_s: int,
    jules_command: str,
) -> list[dict]:
    pull_results = []
    if pull:
        existing_ids = _cycle_session_ids(session_ids=None, launch_result=existing_launch_state)
        candidate_pull_ids = _cycle_session_ids(
            session_ids=session_ids or existing_ids,
            launch_result=launch_result,
        )
        pull_ids = (
            _completed_session_ids(candidate_pull_ids, str(sessions_result.get("stdout", "")))
            if sessions_result.get("status") == "ok"
            else candidate_pull_ids
        )
        already_pulled = _successful_pull_session_ids(base_dir)
        pull_ids = [session_id for session_id in pull_ids if session_id not in already_pulled]
        pull_dry_run = dry_run or (require_remote_ready and not remote_ready)
        for session_id in pull_ids:
            pull_results.append(
                dict(pull_remote_session(
                    session_id=session_id,
                    repo_path=repo_path,
                    output_dir=str(base_dir / _DEFAULT_PULL_DIR),
                    dry_run=pull_dry_run,
                    timeout_s=timeout_s,
                    jules_command=jules_command,
                    write_result=True,
                ))
            )
    return pull_results


def run_jules_cycle(
    content: str = "",
    source_path: str = "",
    packet_dir: str = "",
    repo_path: str = "",
    max_instances: int = 4,
    include_statuses: str | Iterable[str] | None = None,
    write_packets: bool = True,
    launch: bool = False,
    launch_limit: int = 0,
    pull: bool = False,
    session_ids: Iterable[str] | None = None,
    dry_run: bool = True,
    check_remote: bool = True,
    require_remote_ready: bool = True,
    timeout_s: int = 120,
    jules_command: str = "jules",
    write_state: bool = True,
    cycle_state_path: str = "",
) -> JulesCycleResult:
    """Run one safe Jules communication cycle.

    The cycle can dispatch a task dump, refresh launch state, check remote
    readiness, optionally launch packets, optionally pull session results, and
    always refresh the completion-of-task ledger.

    Returns:
        JulesCycleResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    base_dir = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
    try:
        dispatch_result = _cycle_dispatch(
            content=content,
            source_path=source_path,
            max_instances=max_instances,
            include_statuses=include_statuses,
            write_packets=write_packets,
            base_dir=base_dir,
            repo_path=repo_path,
            generated_at=generated_at,
        )

        blockers = []
        if dispatch_result.get("error"):
            blockers.append(f"Dispatch failed: {dispatch_result.get('error')}")

        sessions_result = _cycle_check_remote(
            check_remote=check_remote,
            jules_command=jules_command,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )

        remote_ready = (not check_remote) or dry_run or sessions_result.get("status") == "ok"
        if check_remote and not dry_run and require_remote_ready and not remote_ready:
            blockers.append(
                "Remote Jules session listing did not return ok; live launch/pull stayed disabled."
            )

        existing_launch_state, launch_result, launch_dry_run = _cycle_launch(
            base_dir=base_dir,
            repo_path=repo_path,
            launch=launch,
            launch_limit=launch_limit,
            dry_run=dry_run,
            blockers=blockers,
            require_remote_ready=require_remote_ready,
            remote_ready=remote_ready,
            timeout_s=timeout_s,
            jules_command=jules_command,
            content=content,
            source_path=source_path,
        )

        pull_results = _cycle_pull(
            base_dir=base_dir,
            repo_path=repo_path,
            pull=pull,
            session_ids=session_ids,
            existing_launch_state=existing_launch_state,
            launch_result=launch_result,
            sessions_result=sessions_result,
            dry_run=dry_run,
            require_remote_ready=require_remote_ready,
            remote_ready=remote_ready,
            timeout_s=timeout_s,
            jules_command=jules_command,
        )

        cot_result = build_cot_ledger(packet_dir=str(base_dir), write_ledger=True)
        if cot_result.get("error"):
            blockers.append(f"COT ledger failed: {cot_result.get('error')}")
        all_complete = bool(cot_result.get("all_complete"))
        status = "complete" if all_complete else "blocked" if blockers else "pending"

        payload = JulesCycleResult(
            generated_at_utc=generated_at,
            status=status,
            dry_run=dry_run,
            packet_dir=str(base_dir),
            repo_path=repo_path,
            launch_requested=launch,
            launch_dry_run=launch_dry_run,
            pull_requested=pull,
            check_remote=check_remote,
            require_remote_ready=require_remote_ready,
            blockers=blockers,
            dispatch=dict(dispatch_result),
            sessions=dict(sessions_result),
            launch_result=dict(launch_result),
            pull_results=pull_results,
            cot=dict(cot_result),
            cycle_state_path="",
            note="COT means completion-of-task evidence summaries, not private chain-of-thought.",
        )

        if write_state:
            destination = Path(cycle_state_path) if cycle_state_path else base_dir / _DEFAULT_CYCLE_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["cycle_state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesCycleResult(
            error=str(exc),
            generated_at_utc=generated_at,
            status="error",
            dry_run=dry_run,
            packet_dir=str(base_dir),
            blockers=[str(exc)],
            dispatch={},
            sessions={},
            launch_result={},
            pull_results=[],
            cot={},
        )



def run_jules_watch(
    packet_dir: str = "",
    repo_path: str = "",
    max_wait_s: int = 300,
    poll_interval_s: int = 30,
    timeout_s: int = 120,
    jules_command: str = "jules",
    dry_run: bool = True,
    require_remote_ready: bool = True,
    write_state: bool = True,
    watch_state_path: str = "",
) -> JulesWatchResult:
    """Watch launched Jules sessions, pull completed results, and refresh COT.

    The watcher is bounded by max_wait_s. It does not approve Jules plans because
    the current Jules CLI exposes no plan-approval command; it reports awaiting
    plan/user states as attention-required session rows.

    Returns:
        JulesWatchResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    base_dir = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
    max_wait = max(0, int(max_wait_s or 0))
    poll_interval = max(1, int(poll_interval_s or 1))
    deadline = time.monotonic() + max_wait
    iterations: list[dict] = []
    final_cycle: dict = {}
    latest_status_rows: list[dict] = []
    status = "pending"
    stop_reason = ""
    try:
        while True:
            cycle = run_jules_cycle(
                packet_dir=str(base_dir),
                repo_path=repo_path,
                launch=False,
                pull=True,
                dry_run=dry_run,
                check_remote=True,
                require_remote_ready=require_remote_ready,
                timeout_s=timeout_s,
                jules_command=jules_command,
                write_state=True,
            )
            final_cycle = dict(cycle)
            tracked_ids = _cycle_session_ids(
                session_ids=None,
                launch_result=_read_json_file(base_dir / _DEFAULT_STATE_FILE),
            )
            latest_status_rows = _session_status_rows(
                tracked_ids,
                str(cycle.get("sessions", {}).get("stdout", "")),
            )
            cot = cycle.get("cot", {}) if isinstance(cycle, dict) else {}
            iteration = {
                "iteration": len(iterations) + 1,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "cycle_status": cycle.get("status"),
                "pull_count": len(cycle.get("pull_results", []) or []),
                "pulled_sessions": [
                    str(item.get("session_id", ""))
                    for item in cycle.get("pull_results", []) or []
                    if isinstance(item, dict)
                ],
                "cot_completed": cot.get("completed_count", 0),
                "cot_pending": cot.get("pending_count", 0),
                "cot_status_counts": cot.get("status_counts", {}),
                "remote_status_counts": _count_remote_statuses(latest_status_rows),
            }
            iterations.append(iteration)

            if cycle.get("status") == "complete" or cot.get("all_complete"):
                status = "complete"
                stop_reason = "cot_complete"
                break
            if cycle.get("blockers"):
                status = "blocked"
                stop_reason = "cycle_blocker"
                break
            if dry_run:
                status = "dry_run"
                stop_reason = "dry_run"
                break
            if time.monotonic() >= deadline:
                status = _watch_terminal_status(latest_status_rows)
                stop_reason = "max_wait_elapsed"
                break
            sleep_s = min(poll_interval, max(0.0, deadline - time.monotonic()))
            if sleep_s <= 0:
                continue
            time.sleep(sleep_s)

        payload = JulesWatchResult(
            generated_at_utc=generated_at,
            status=status,
            stop_reason=stop_reason,
            dry_run=dry_run,
            packet_dir=str(base_dir),
            repo_path=repo_path,
            max_wait_s=max_wait,
            poll_interval_s=poll_interval,
            timeout_s=timeout_s,
            jules_command=jules_command,
            require_remote_ready=require_remote_ready,
            iterations=iterations,
            latest_remote_statuses=latest_status_rows,
            final_cycle=final_cycle,
            watch_state_path="",
            note=(
                "COT means completion-of-task evidence summaries. Awaiting plan/user "
                "states require operator action because the Jules CLI exposes no plan approval command."
            ),
        )
        if write_state:
            destination = Path(watch_state_path) if watch_state_path else base_dir / _DEFAULT_WATCH_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["watch_state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesWatchResult(
            error=str(exc),
            generated_at_utc=generated_at,
            status="error",
            stop_reason="watch_error",
            dry_run=dry_run,
            packet_dir=str(base_dir),
            iterations=iterations,
            latest_remote_statuses=latest_status_rows,
            final_cycle=final_cycle,
            watch_state_path="",
        )


def run_jules_fleet(
    content: str = "",
    source_path: str = "",
    packet_dir: str = "",
    repo_path: str = "",
    max_instances: int = 12,
    max_concurrent: int = 6,
    launch_batch_size: int = 2,
    include_statuses: str | Iterable[str] | None = None,
    dry_run: bool = True,
    timeout_s: int = 120,
    jules_command: str = "jules",
    require_remote_ready: bool = True,
    write_state: bool = True,
    fleet_state_path: str = "",
) -> JulesFleetResult:
    """Run one fleet-maintenance cycle for Jules workers.

    The fleet cycle prepares a larger queue, pulls completed launched sessions,
    computes remote capacity, and launches the next unlaunched packets up to the
    configured max_concurrent cap.

    Returns:
        JulesFleetResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    base_dir = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
    blockers: list[str] = []
    try:
        dispatch_result = _fleet_dispatch(
            content=content,
            source_path=source_path,
            base_dir=base_dir,
            repo_path=repo_path,
            max_instances=max_instances,
            include_statuses=include_statuses,
            generated_at=generated_at,
        )
        if dispatch_result.get("error"):
            blockers.append(f"Dispatch failed: {dispatch_result.get('error')}")

        sessions_result = list_remote_sessions(
            jules_command=jules_command,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )
        remote_ready = dry_run or sessions_result.get("status") == "ok"
        if not dry_run and require_remote_ready and not remote_ready:
            blockers.append("Remote Jules session listing did not return ok; fleet launch/pull stayed disabled.")

        launch_state_path = base_dir / _DEFAULT_STATE_FILE
        existing_launch_state = _read_json_file(launch_state_path)
        tracked_ids = _cycle_session_ids(session_ids=None, launch_result=existing_launch_state)
        remote_status_rows = _session_status_rows(tracked_ids, str(sessions_result.get("stdout", "")))
        active_count = _active_remote_session_count(remote_status_rows)

        failed_packet_files = _failed_remote_packet_files(existing_launch_state, remote_status_rows)
        stale_unknown_packet_files = _stale_unknown_remote_packet_files(existing_launch_state, remote_status_rows)
        plan_awaiting_packet_files = _plan_awaiting_remote_packet_files(existing_launch_state, remote_status_rows)
        retry_packet_files = _merge_unique(failed_packet_files, stale_unknown_packet_files)
        retry_packet_files = _merge_unique(retry_packet_files, plan_awaiting_packet_files)

        completed_ids, already_pulled, pull_results = _fleet_pull_sessions(
            sessions_result=sessions_result,
            tracked_ids=tracked_ids,
            base_dir=base_dir,
            dry_run=dry_run,
            remote_ready=remote_ready,
            repo_path=repo_path,
            timeout_s=timeout_s,
            jules_command=jules_command,
        )

        capacity, launch_limit, launch_dry_run, relaunch_limit, launch_result = _fleet_launch(
            active_count=active_count,
            max_concurrent=max_concurrent,
            launch_batch_size=launch_batch_size,
            blockers=blockers,
            dry_run=dry_run,
            retry_packet_files=retry_packet_files,
            base_dir=base_dir,
            repo_path=repo_path,
            timeout_s=timeout_s,
            jules_command=jules_command,
        )

        cot_result = build_cot_ledger(packet_dir=str(base_dir), write_ledger=True)
        if cot_result.get("error"):
            blockers.append(f"COT ledger failed: {cot_result.get('error')}")

        launched_this_cycle = sum(
            1
            for item in launch_result.get("attempt_results", []) or []
            if item.get("status") == "launched"
        )
        all_complete = bool(cot_result.get("all_complete"))
        status = (
            "complete" if all_complete
            else "blocked" if blockers
            else "scaled" if launched_this_cycle
            else "pending"
        )
        payload = JulesFleetResult(
            generated_at_utc=generated_at,
            status=status,
            dry_run=dry_run,
            packet_dir=str(base_dir),
            repo_path=repo_path,
            max_instances=max_instances,
            max_concurrent=max_concurrent,
            launch_batch_size=launch_batch_size,
            timeout_s=timeout_s,
            jules_command=jules_command,
            require_remote_ready=require_remote_ready,
            blockers=blockers,
            dispatch=dict(dispatch_result),
            sessions=dict(sessions_result),
            remote_statuses=remote_status_rows,
            remote_status_counts=_count_remote_statuses(remote_status_rows),
            active_remote_count=active_count,
            completed_remote_session_ids=completed_ids,
            already_pulled_session_ids=sorted(already_pulled),
            failed_remote_packet_files=failed_packet_files,
            stale_unknown_remote_packet_files=stale_unknown_packet_files,
            plan_awaiting_remote_packet_files=plan_awaiting_packet_files,
            retry_remote_packet_files=retry_packet_files,
            relaunch_failed_limit=relaunch_limit,
            available_launch_capacity=capacity,
            requested_launch_limit=launch_limit,
            launch_dry_run=launch_dry_run,
            launch_result=dict(launch_result),
            pull_results=[dict(result) for result in pull_results],
            cot=dict(cot_result),
            fleet_state_path="",
            note=(
                "Fleet cycle scales only within max_concurrent and only launches packets "
                "not already marked launched in JULES_LAUNCH_STATE.json."
            ),
        )
        if write_state:
            destination = Path(fleet_state_path) if fleet_state_path else base_dir / _DEFAULT_FLEET_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["fleet_state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesFleetResult(
            error=str(exc),
            generated_at_utc=generated_at,
            status="error",
            dry_run=dry_run,
            packet_dir=str(base_dir),
            blockers=blockers + [str(exc)],
            dispatch={},
            sessions={},
            remote_statuses=[],
            launch_result={},
            pull_results=[],
            cot={},
            fleet_state_path="",
        )


def run_jules_fleet_watch(
    content: str = "",
    source_path: str = "",
    packet_dir: str = "",
    repo_path: str = "",
    max_instances: int = 12,
    max_concurrent: int = 6,
    launch_batch_size: int = 2,
    include_statuses: str | Iterable[str] | None = None,
    max_wait_s: int = 900,
    poll_interval_s: int = 30,
    timeout_s: int = 120,
    jules_command: str = "jules",
    dry_run: bool = True,
    require_remote_ready: bool = True,
    write_state: bool = True,
    fleet_watch_state_path: str = "",
) -> JulesFleetWatchResult:
    """Run bounded self-maintenance for a Jules worker fleet.

    Each loop pulls completed sessions, refreshes COT, and launches unlaunched
    packets into capacity opened by completed/failed tracked sessions.

    Returns:
        JulesFleetWatchResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    base_dir = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
    max_wait = max(0, int(max_wait_s or 0))
    poll_interval = max(1, int(poll_interval_s or 1))
    deadline = time.monotonic() + max_wait
    iterations: list[dict] = []
    final_fleet: dict = {}
    status = "pending"
    stop_reason = ""
    try:
        while True:
            first_iteration = not iterations
            fleet = run_jules_fleet(
                content=content if first_iteration else "",
                source_path=source_path if first_iteration else "",
                packet_dir=str(base_dir),
                repo_path=repo_path,
                max_instances=max_instances,
                max_concurrent=max_concurrent,
                launch_batch_size=launch_batch_size,
                include_statuses=include_statuses,
                dry_run=dry_run,
                timeout_s=timeout_s,
                jules_command=jules_command,
                require_remote_ready=require_remote_ready,
                write_state=True,
            )
            final_fleet = dict(fleet)
            launch_result = fleet.get("launch_result", {}) if isinstance(fleet, dict) else {}
            attempt_results = launch_result.get("attempt_results", []) if isinstance(launch_result, dict) else []
            cot = fleet.get("cot", {}) if isinstance(fleet, dict) else {}
            iteration = {
                "iteration": len(iterations) + 1,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "fleet_status": fleet.get("status"),
                "pull_count": len(fleet.get("pull_results", []) or []),
                "pulled_sessions": [
                    str(item.get("session_id", ""))
                    for item in fleet.get("pull_results", []) or []
                    if isinstance(item, dict)
                ],
                "launch_attempt_count": len(attempt_results or []),
                "launched_sessions": _launched_session_ids(attempt_results),
                "active_remote_count": fleet.get("active_remote_count", 0),
                "available_launch_capacity": fleet.get("available_launch_capacity", 0),
                "requested_launch_limit": fleet.get("requested_launch_limit", 0),
                "remote_status_counts": fleet.get("remote_status_counts", {}),
                "cot_completed": cot.get("completed_count", 0),
                "cot_pending": cot.get("pending_count", 0),
                "cot_status_counts": cot.get("status_counts", {}),
            }
            iterations.append(iteration)

            if fleet.get("status") == "complete" or cot.get("all_complete"):
                status = "complete"
                stop_reason = "cot_complete"
                break
            if fleet.get("blockers"):
                status = "blocked"
                stop_reason = "fleet_blocker"
                break
            if dry_run:
                status = "dry_run"
                stop_reason = "dry_run"
                break
            if time.monotonic() >= deadline:
                status = _watch_terminal_status(fleet.get("remote_statuses", []) or [])
                stop_reason = "max_wait_elapsed"
                break
            sleep_s = min(poll_interval, max(0.0, deadline - time.monotonic()))
            if sleep_s <= 0:
                continue
            time.sleep(sleep_s)

        payload = JulesFleetWatchResult(
            generated_at_utc=generated_at,
            status=status,
            stop_reason=stop_reason,
            dry_run=dry_run,
            packet_dir=str(base_dir),
            repo_path=repo_path,
            max_instances=max_instances,
            max_concurrent=max_concurrent,
            launch_batch_size=launch_batch_size,
            max_wait_s=max_wait,
            poll_interval_s=poll_interval,
            timeout_s=timeout_s,
            jules_command=jules_command,
            require_remote_ready=require_remote_ready,
            iterations=iterations,
            final_fleet=final_fleet,
            fleet_watch_state_path="",
            note=(
                "Fleet watch repeatedly scales and pulls within max_concurrent until COT "
                "is complete or the bounded wait window ends."
            ),
        )
        if write_state:
            destination = (
                Path(fleet_watch_state_path)
                if fleet_watch_state_path
                else base_dir / _DEFAULT_FLEET_WATCH_STATE
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["fleet_watch_state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JulesFleetWatchResult(
            error=str(exc),
            generated_at_utc=generated_at,
            status="error",
            stop_reason="fleet_watch_error",
            dry_run=dry_run,
            packet_dir=str(base_dir),
            iterations=iterations,
            final_fleet=final_fleet,
            fleet_watch_state_path="",
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

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
    objective = (
        f"Execute this Antigravity Codex handover prompt: {title}"
        if task.get("task_type") == "antigravity"
        else f"Complete exactly this Jules card: {title}"
    )
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
        objective,
        "",
        "## Task Details",
        f"- File: {task.get('file', '') or '(not provided)'}",
        f"- Issue: {task.get('issue', '') or '(not provided)'}",
        f"- Language: {task.get('language', '') or '(not provided)'}",
        f"- Rationale: {task.get('rationale', '') or '(not provided)'}",
        "",
        "## Operating Rules",
        "- Work on one card only; do not opportunistically refactor unrelated code.",
        "- Do not stop at a plan or ask for plan approval; plan briefly in the report"
        " and proceed unless a hard blocker prevents work.",
        "- Preserve existing behavior unless the card explicitly asks for behavior change.",
        "- Run the narrowest relevant verification first, then the broader suite if practical.",
        "- Record concrete evidence: commands, test result summaries, hashes, screenshots, or PR links.",
        "- Do not reveal private chain-of-thought."
        " Use a concise rationale, decision log, and evidence checklist instead.",
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
    output_dir: Path,
    repo_path: str,
    source_label: str,
    source_hash: str,
) -> tuple[list[str], list[str]]:
    if not selected:
        return [], []
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_previous_dispatch(output_dir)
    packet_files: list[str] = []
    packet_commands: list[str] = []
    for task, packet in zip(selected, packets):
        filename = f"{task.get('id')}-{_slug(str(task.get('title', 'task')))}.md"
        path = output_dir / filename
        path.write_text(packet, encoding="utf-8")
        packet_files.append(str(path))
        packet_commands.append(
            _launch_command(str(path), task, str(task.get("repo_path") or repo_path))
        )

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
    for name in ("JULES_DISPATCH_INDEX.md", "jules_launch_commands.ps1"):
        path = output_dir / name
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
        paths = _packet_files_from_index(base) or sorted(base.glob("JT-*.md"))
    return [path for path in paths if path.is_file()]


def _packet_files_from_index(packet_dir: Path) -> list[Path]:
    index_path = packet_dir / "JULES_DISPATCH_INDEX.md"
    if not index_path.is_file():
        return []
    ordered: list[Path] = []
    seen: set[str] = set()
    try:
        for line in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("| JT-"):
                continue
            columns = [column.strip() for column in line.split("|")]
            if len(columns) < 7:
                continue
            packet = Path(columns[6])
            key = str(packet).lower()
            if key not in seen and packet.is_file():
                ordered.append(packet)
                seen.add(key)
    except Exception:  # pylint: disable=broad-exception-caught
        return []
    return ordered


def _state_path_for(
    packet_dir: str,
    state_path: str,
    packet_files: Iterable[Path] | None = None,
) -> Path:
    if state_path:
        return Path(state_path)
    if packet_dir:
        base = Path(packet_dir)
    elif packet_files:
        first_packet = next(iter(packet_files), None)
        base = first_packet.parent if first_packet else _DEFAULT_OUTPUT_DIR
    else:
        base = _DEFAULT_OUTPUT_DIR
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


def _resolve_cli_command(command: str) -> str:
    candidate = (command or "").strip() or "jules"
    if candidate.lower() == "jules":
        candidates = _candidate_jules_commands(candidate)
        fallback = shutil.which(candidate) or candidate
        return _preferred_jules_command(candidates, fallback)
    return shutil.which(candidate) or candidate


def _candidate_jules_commands(command: str) -> list[dict]:
    candidates = []
    seen = set()
    raw = (command or "").strip() or "jules"
    resolved = shutil.which(raw) or raw
    _append_candidate(candidates, seen, "requested", raw, resolved)
    explicit = os.environ.get("JULES_CLI_PATH", "").strip()
    if explicit:
        _append_candidate(candidates, seen, "env_cli", explicit, explicit)
    for npm_prefix in _npm_prefix_candidates():
        _append_candidate(
            candidates,
            seen,
            "npm_bin_exe",
            str(npm_prefix / "bin" / "jules.exe"),
            str(npm_prefix / "bin" / "jules.exe"),
        )
        _append_candidate(
            candidates,
            seen,
            "npm_prefix_cmd",
            str(npm_prefix / "jules.cmd"),
            str(npm_prefix / "jules.cmd"),
        )
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        _append_candidate(
            candidates,
            seen,
            "npm_bin_exe",
            str(Path(appdata) / "npm" / "bin" / "jules.exe"),
            str(Path(appdata) / "npm" / "bin" / "jules.exe"),
        )
        _append_candidate(
            candidates,
            seen,
            "npm_cmd",
            str(Path(appdata) / "npm" / "jules.cmd"),
            str(Path(appdata) / "npm" / "jules.cmd"),
        )
    temp_dir = os.environ.get("TEMP") or os.environ.get("TMP") or ""
    if temp_dir:
        _append_candidate(
            candidates,
            seen,
            "temp_exe",
            str(Path(temp_dir) / "jules_tmp" / "jules.exe"),
            str(Path(temp_dir) / "jules_tmp" / "jules.exe"),
        )
    return candidates


def _npm_prefix_candidates() -> list[Path]:
    candidates = []
    seen = set()
    for raw in (
        os.environ.get("npm_config_prefix", ""),
        str(Path.home() / ".npm-packages"),
        str(Path(os.environ.get("USERPROFILE", "")) / ".npm-packages") if os.environ.get("USERPROFILE") else "",
    ):
        if not raw:
            continue
        path = Path(raw)
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(path)
    return candidates


def _append_candidate(candidates: list[dict], seen: set, label: str, requested: str, resolved: str) -> None:
    key = str(resolved).lower()
    if key in seen:
        return
    seen.add(key)
    candidates.append({
        "label": label,
        "requested": requested,
        "resolved": resolved,
        "exists": Path(resolved).exists() if resolved else False,
    })


def _preferred_jules_command(candidates: list[dict], fallback: str) -> str:
    for label in ("env_cli", "npm_bin_exe", "temp_exe", "requested", "npm_cmd", "npm_prefix_cmd"):
        for candidate in candidates:
            if candidate.get("label") == label and candidate.get("exists"):
                return str(candidate.get("resolved"))
    return fallback


def _auth_indicators() -> dict:
    home = Path.home()
    paths = [
        Path(os.environ.get("APPDATA", "")) / "jules",
        Path(os.environ.get("LOCALAPPDATA", "")) / "jules",
        home / ".config" / "jules",
        home / ".jules_auth",
    ]
    entries = []
    for path in paths:
        if not str(path):
            continue
        exists = path.exists()
        entries.append({
            "path": str(path),
            "exists": exists,
            "item_count": _safe_child_count(path) if exists else 0,
        })
    return {
        "known_auth_paths": entries,
        "any_known_auth_path_exists": any(item["exists"] for item in entries),
    }


def _safe_child_count(path: Path) -> int:
    try:
        if path.is_dir():
            return len(list(path.iterdir()))
        return 1
    except Exception:  # pylint: disable=broad-exception-caught
        return 0


def _preflight_blocker(
    version_result: dict,
    remote_result: dict,
    auth_indicators: dict,
    check_remote: bool,
) -> str:
    if version_result.get("timed_out"):
        return "version_timeout"
    if version_result.get("exit_code") != 0:
        return "version_failed"
    if not check_remote:
        return ""
    if remote_result.get("status") == "ok":
        return ""
    if remote_result.get("timed_out") and not auth_indicators.get("any_known_auth_path_exists"):
        return "remote_timeout_possible_auth_required"
    if remote_result.get("timed_out"):
        return "remote_timeout"
    if remote_result.get("status") in ("failed", "error"):
        return f"remote_{remote_result.get('status')}"
    return "remote_not_ready"


def _run_cli_command(
    command: list[str],
    timeout_s: int,
    cwd: str | None = None,
    input_text: str | None = None,
) -> dict:
    timeout = max(1, int(timeout_s or 1))
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout)
        return {
            "exit_code": process.returncode,
            "stdout": stdout or "",
            "stderr": stderr or "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        stdout = _coerce_text(getattr(exc, "stdout", None) or getattr(exc, "output", None))
        stderr = _coerce_text(getattr(exc, "stderr", None))
        try:
            recovered_stdout, recovered_stderr = process.communicate(timeout=5)
            stdout += _coerce_text(recovered_stdout)
            stderr += _coerce_text(recovered_stderr)
        except Exception as cleanup_exc:  # noqa: BLE001
            stderr = (stderr + "\n" + f"cleanup_after_timeout_failed: {cleanup_exc}").strip()
        return {
            "exit_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": True,
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        _terminate_process_tree(process)
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                check=False,
            )
            return
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    try:
        process.kill()
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _read_json_file(path: Path) -> dict:
    try:
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:  # pylint: disable=broad-exception-caught
        return {}


def _launch_succeeded(exit_code, output: str, session_ids: Iterable[str]) -> bool:
    if exit_code != 0:
        return False
    if _cli_output_has_error(output):
        return False
    return any(str(value).strip() for value in session_ids or [])


def _stored_launch_succeeded(item: dict) -> bool:
    if item.get("status") != "launched":
        return False
    output = f"{item.get('stdout', '')}\n{item.get('stderr', '')}"
    return _launch_succeeded(item.get("exit_code"), output, item.get("session_ids", []))


def _cli_output_has_error(output: str) -> bool:
    return re.search(r"(?im)^\s*(error|fatal):", output or "") is not None


def _already_launched_packet_keys(state: dict) -> set[str]:
    keys: set[str] = set()
    for item in state.get("results", []) if isinstance(state, dict) else []:
        if not isinstance(item, dict):
            continue
        if not _stored_launch_succeeded(item):
            continue
        packet = str(item.get("packet", ""))
        if packet:
            keys.add(packet.lower())
    return keys


def _merge_launch_results(
    previous_results: Iterable[dict],
    current_results: Iterable[dict],
    all_packets: Iterable[Path],
    preserve_existing_session_ids: bool = False,
) -> list[dict]:
    previous_by_packet = _results_by_packet(previous_results)
    current_by_packet = _results_by_packet(current_results)
    merged: list[dict] = []
    seen: set[str] = set()
    for packet in all_packets:
        packet_text = str(packet)
        key = packet_text.lower()
        item = current_by_packet.get(key) or previous_by_packet.get(key)
        if preserve_existing_session_ids and key in current_by_packet and key in previous_by_packet:
            item = _merge_launch_session_ids(current_by_packet[key], previous_by_packet[key])
        if item is None:
            item = _not_launched_result(packet_text)
        merged.append(dict(item))
        seen.add(key)
    for key, item in current_by_packet.items():
        if key not in seen:
            merged.append(dict(item))
            seen.add(key)
    return merged


def _merge_launch_session_ids(current: dict, previous: dict) -> dict:
    merged = dict(current)
    merged["session_ids"] = _merge_unique(
        [str(value) for value in current.get("session_ids", []) if str(value).strip()],
        [str(value) for value in previous.get("session_ids", []) if str(value).strip()],
    )
    return merged


def _results_by_packet(results: Iterable[dict]) -> dict[str, dict]:
    by_packet: dict[str, dict] = {}
    for item in results or []:
        if not isinstance(item, dict):
            continue
        packet = str(item.get("packet", ""))
        if packet:
            by_packet[packet.lower()] = dict(item)
    return by_packet


def _not_launched_result(packet: str) -> dict:
    return {
        "packet": packet,
        "command": [],
        "repo_path": "",
        "status": "not_launched",
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "session_ids": [],
    }


def _cot_rows_from_state(state: dict, base_dir: Path) -> list[dict]:
    rows: list[dict] = []
    state_results = state.get("results") if isinstance(state, dict) else []
    if isinstance(state_results, list) and state_results:
        for item in state_results:
            if not isinstance(item, dict):
                continue
            packet = str(item.get("packet", ""))
            rows.append({
                "packet": packet,
                "packet_id": _packet_id_from_path(packet),
                "launch_status": item.get("status", "unknown"),
                "session_ids": [str(value) for value in item.get("session_ids", [])],
                "timed_out": bool(item.get("timed_out")),
                "exit_code": item.get("exit_code"),
                "cot_status": "unknown",
                "report_files": [],
            })
    if rows:
        return rows
    return [
        {
            "packet": str(packet),
            "packet_id": _packet_id_from_path(str(packet)),
            "launch_status": "not_launched",
            "session_ids": [],
            "timed_out": False,
            "exit_code": None,
            "cot_status": "not_launched",
            "report_files": [],
        }
        for packet in _resolve_packet_files(packet_dir=str(base_dir))
    ]


def _packet_id_from_path(path: str) -> str:
    name = Path(path).name
    match = re.search(r"(JT-\d{3}-[A-Za-z0-9]+)", name)
    if match:
        return match.group(1)
    match = re.search(r"(JT-\d{3})", name)
    return match.group(1) if match else ""


def _collect_cot_reports(base_dir: Path, report_dir: str = "") -> list[dict]:
    roots = []
    if report_dir:
        roots.append(Path(report_dir))
    else:
        roots.extend([base_dir / _DEFAULT_COT_DIR, base_dir / _DEFAULT_PULL_DIR])
    reports: list[dict] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(list(root.glob("*.md")) + list(root.glob("*.json"))):
            content = _read_report_content(path)
            searchable = f"{path.name}\n{content}"
            reports.append({
                "path": str(path),
                "content": content,
                "session_ids": _extract_session_ids(searchable),
                "packet_ids": _extract_packet_ids(searchable),
            })
    return reports


def _read_report_content(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() != ".json":
        return raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    parts = [
        f"status: {payload.get('status', '')}",
        f"exit_code: {payload.get('exit_code', '')}",
        str(payload.get("stdout", "")),
        str(payload.get("stderr", "")),
        str(payload.get("note", "")),
        " ".join(str(value) for value in payload.get("session_ids", []) or []),
    ]
    return "\n".join(part for part in parts if part)


def _extract_packet_ids(text: str) -> list[str]:
    candidates = re.findall(r"\bJT-\d{3}(?:-[A-Za-z0-9]+)?\b", text or "")
    return _merge_unique([], candidates)


def _matching_reports(row: dict, reports: list[dict]) -> list[dict]:
    packet_id = str(row.get("packet_id", ""))
    session_ids = {str(value) for value in row.get("session_ids", []) if str(value)}
    matches: list[dict] = []
    for report in reports:
        report_packet_ids = set(report.get("packet_ids", []))
        report_session_ids = set(report.get("session_ids", []))
        if packet_id and packet_id in report_packet_ids:
            matches.append(report)
            continue
        if session_ids and session_ids.intersection(report_session_ids):
            matches.append(report)
    return matches


def _classify_cot_status(row: dict, reports: list[dict]) -> str:
    combined = "\n".join(report.get("content", "") for report in reports)
    if reports:
        if _looks_blocked(combined):
            return "blocked_reported"
        if _looks_complete(combined):
            return "completed_reported"
        if _looks_pulled_output(combined):
            return "pulled_output_reported"
        return "report_found_needs_review"
    launch_status = str(row.get("launch_status") or "unknown")
    if launch_status in ("dry_run", "not_launched"):
        return "not_launched"
    if launch_status in ("timeout", "failed", "error"):
        return f"launch_{launch_status}"
    if row.get("session_ids"):
        return "launched_pending_cot"
    if launch_status == "launched":
        return "launched_missing_session_id"
    return "pending_launch"


def _looks_complete(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "completion report" in lower
        or ("what changed" in lower and "verification" in lower)
        or ("files touched" in lower and "verification performed" in lower)
    )


def _looks_blocked(text: str) -> bool:
    lower = (text or "").lower()
    return "blocked" in lower and ("next action" in lower or "blocker" in lower)


def _looks_pulled_output(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "status: pulled" in lower
        and "exit_code: 0" in lower
        and "diff --git " in lower
        and "--- a/" in lower
        and "+++ b/" in lower
    )


def _count_row_statuses(rows: Iterable[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("cot_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _cot_ledger_markdown(payload: JulesCotResult) -> str:
    lines = [
        "# Jules COT Ledger",
        "",
        f"- generated_at_utc: {payload.get('generated_at_utc', '')}",
        f"- packet_dir: {payload.get('packet_dir', '')}",
        f"- launch_state_path: {payload.get('launch_state_path', '')}",
        f"- selected_count: {payload.get('selected_count', 0)}",
        f"- completed_count: {payload.get('completed_count', 0)}",
        f"- blocked_count: {payload.get('blocked_count', 0)}",
        f"- pending_count: {payload.get('pending_count', 0)}",
        f"- all_complete: {payload.get('all_complete', False)}",
        "",
        "| packet_id | launch_status | session_ids | cot_status | reports |",
        "|---|---|---|---|---|",
    ]
    for row in payload.get("rows", []):
        reports = "<br>".join(Path(path).name for path in row.get("report_files", []))
        lines.append(
            "| {packet_id} | {launch_status} | {session_ids} | {cot_status} | {reports} |".format(
                packet_id=row.get("packet_id", ""),
                launch_status=row.get("launch_status", ""),
                session_ids=", ".join(row.get("session_ids", [])),
                cot_status=row.get("cot_status", ""),
                reports=reports,
            )
        )
    lines.extend([
        "",
        "COT means completion-of-task evidence summaries, not private chain-of-thought.",
        "",
    ])
    return "\n".join(lines)


def _cycle_session_ids(
    session_ids: Iterable[str] | None,
    launch_result: JulesLaunchResult,
) -> list[str]:
    collected = [str(value) for value in session_ids or [] if str(value).strip()]
    for item in launch_result.get("results", []) if isinstance(launch_result, dict) else []:
        if not isinstance(item, dict):
            continue
        collected.extend(str(value) for value in item.get("session_ids", []) if str(value).strip())
    return _merge_unique([], collected)


def _launched_session_ids(results: Iterable[dict]) -> list[str]:
    collected: list[str] = []
    for item in results or []:
        if not isinstance(item, dict) or item.get("status") != "launched":
            continue
        collected.extend(str(value) for value in item.get("session_ids", []) if str(value).strip())
    return _merge_unique([], collected)


def _failed_remote_packet_files(state: dict, remote_status_rows: Iterable[dict]) -> list[str]:
    failed_ids = {
        str(row.get("session_id", ""))
        for row in remote_status_rows or []
        if row.get("remote_status") == "Failed" and str(row.get("session_id", "")).strip()
    }
    if not failed_ids:
        return []
    packet_files: list[str] = []
    for item in state.get("results", []) if isinstance(state, dict) else []:
        if not isinstance(item, dict):
            continue
        session_ids = {str(value) for value in item.get("session_ids", []) if str(value).strip()}
        packet = str(item.get("packet", ""))
        if packet and session_ids.intersection(failed_ids):
            packet_files.append(packet)
    return packet_files


def _stale_unknown_remote_packet_files(state: dict, remote_status_rows: Iterable[dict]) -> list[str]:
    stale_ids = {
        str(row.get("session_id", ""))
        for row in remote_status_rows or []
        if row.get("stale_unknown") and str(row.get("session_id", "")).strip()
    }
    if not stale_ids:
        return []
    packet_files: list[str] = []
    for item in state.get("results", []) if isinstance(state, dict) else []:
        if not isinstance(item, dict):
            continue
        session_ids = {str(value) for value in item.get("session_ids", []) if str(value).strip()}
        packet = str(item.get("packet", ""))
        if packet and session_ids.intersection(stale_ids):
            packet_files.append(packet)
    return packet_files


def _plan_awaiting_remote_packet_files(state: dict, remote_status_rows: Iterable[dict]) -> list[str]:
    awaiting_ids = {
        str(row.get("session_id", ""))
        for row in remote_status_rows or []
        if row.get("remote_status") == "Awaiting Plan" and str(row.get("session_id", "")).strip()
    }
    if not awaiting_ids:
        return []
    packet_files: list[str] = []
    for item in state.get("results", []) if isinstance(state, dict) else []:
        if not isinstance(item, dict):
            continue
        session_ids = {str(value) for value in item.get("session_ids", []) if str(value).strip()}
        packet = str(item.get("packet", ""))
        if packet and session_ids.intersection(awaiting_ids):
            packet_files.append(packet)
    return packet_files


def _successful_pull_session_ids(base_dir: Path) -> set[str]:
    pull_dir = base_dir / _DEFAULT_PULL_DIR
    if not pull_dir.is_dir():
        return set()
    session_ids: set[str] = set()
    for path in pull_dir.glob("jules_pull_*.json"):
        payload = _read_json_file(path)
        if not payload:
            continue
        if payload.get("status") != "pulled" or payload.get("exit_code") != 0 or payload.get("timed_out"):
            continue
        if str(payload.get("session_id", "")).strip():
            session_ids.add(str(payload.get("session_id", "")).strip())
        match = re.search(r"jules_pull_(\d+)\.json$", path.name)
        if match:
            session_ids.add(match.group(1))
    return session_ids


def _completed_session_ids(session_ids: Iterable[str], remote_stdout: str) -> list[str]:
    completed: list[str] = []
    lines = (remote_stdout or "").splitlines()
    for session_id in session_ids:
        clean_id = str(session_id).strip()
        if not clean_id:
            continue
        for line in lines:
            if clean_id in line and "Completed" in line:
                completed.append(clean_id)
                break
    return _merge_unique([], completed)


def _session_status_rows(session_ids: Iterable[str], remote_stdout: str) -> list[dict]:
    lines = (remote_stdout or "").splitlines()
    rows: list[dict] = []
    for session_id in session_ids:
        clean_id = str(session_id).strip()
        if not clean_id:
            continue
        line = next((item for item in lines if clean_id in item), "")
        remote_status = _remote_status_from_line(line)
        last_active_s = _remote_last_active_seconds(line)
        rows.append({
            "session_id": clean_id,
            "remote_status": remote_status,
            "last_active_s": last_active_s,
            "stale_unknown": (
                remote_status == "unknown"
                and last_active_s is not None
                and last_active_s >= _STALE_UNKNOWN_REMOTE_SECONDS
            ),
            "line": line,
        })
    return rows


def _remote_status_from_line(line: str) -> str:
    text = line or ""
    for status in (
        "Completed",
        "Failed",
        "In Progress",
        "Planning",
        "Awaiting Plan",
        "Awaiting User",
        "Awaiting",
    ):
        if status in text:
            return status
    return "unknown" if text else "missing"


def _remote_last_active_seconds(line: str) -> int | None:
    match = re.search(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?\s+ago", line or "")
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    if hours == minutes == seconds == 0:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _count_remote_statuses(rows: Iterable[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("remote_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _active_remote_session_count(rows: Iterable[dict]) -> int:
    inactive = {"Completed", "Failed", "Awaiting Plan", "missing"}
    count = 0
    for row in rows:
        if row.get("stale_unknown"):
            continue
        status = str(row.get("remote_status") or "unknown")
        if status not in inactive:
            count += 1
    return count


def _watch_terminal_status(rows: Iterable[dict]) -> str:
    counts = _count_remote_statuses(rows)
    if counts.get("Failed", 0):
        return "failed"
    attention = sum(count for status, count in counts.items() if status.startswith("Awaiting"))
    if attention:
        return "attention_required"
    return "pending"


def _merge_unique(prefix: Iterable[str], values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in list(prefix) + list(values):
        text = str(value)
        if text and text not in seen:
            merged.append(text)
            seen.add(text)
    return merged


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value or "session").strip("-") or "session"


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


def _fleet_dispatch(
    content: str,
    source_path: str,
    base_dir: Path,
    repo_path: str,
    max_instances: int,
    include_statuses: str | Iterable[str] | None,
    generated_at: str,
) -> JulesDispatchResult:
    if content or source_path:
        return build_dispatch(
            content=content,
            source_path=source_path,
            max_instances=max_instances,
            include_statuses=include_statuses,
            write_packets=True,
            output_dir=str(base_dir),
            repo_path=repo_path,
        )
    packets = _resolve_packet_files(packet_dir=str(base_dir))
    return JulesDispatchResult(
        source="existing_packets",
        generated_at_utc=generated_at,
        task_count=0,
        selected_count=len(packets),
        status_counts={},
        include_statuses=list(_status_filter(include_statuses)),
        max_instances=max_instances,
        write_packets=False,
        output_dir=str(base_dir),
        repo_path=repo_path,
        selected_tasks=[],
        packet_files=[str(packet) for packet in packets],
        launch_commands=[],
        note="No task dump supplied; using existing packet files.",
    )


def _fleet_pull_sessions(
    sessions_result: dict,
    tracked_ids: list[str],
    base_dir: Path,
    dry_run: bool,
    remote_ready: bool,
    repo_path: str,
    timeout_s: int,
    jules_command: str,
) -> tuple[list[str], set[str], list[dict]]:
    completed_ids = (
        _completed_session_ids(tracked_ids, str(sessions_result.get("stdout", "")))
        if sessions_result.get("status") == "ok"
        else []
    )
    already_pulled = _successful_pull_session_ids(base_dir)
    pull_ids = [session_id for session_id in completed_ids if session_id not in already_pulled]
    pull_results = []
    if not dry_run and remote_ready:
        for session_id in pull_ids:
            pull_results.append(
                pull_remote_session(
                    session_id=session_id,
                    repo_path=repo_path,
                    output_dir=str(base_dir / _DEFAULT_PULL_DIR),
                    dry_run=False,
                    timeout_s=timeout_s,
                    jules_command=jules_command,
                    write_result=True,
                )
            )
    return completed_ids, already_pulled, pull_results


def _fleet_launch(
    active_count: int,
    max_concurrent: int,
    launch_batch_size: int,
    blockers: list[str],
    dry_run: bool,
    retry_packet_files: list[str],
    base_dir: Path,
    repo_path: str,
    timeout_s: int,
    jules_command: str,
) -> tuple[int, int, bool, int, JulesLaunchResult]:
    capacity = max(0, int(max_concurrent or 0) - active_count)
    launch_limit = min(max(0, int(launch_batch_size or 0)), capacity)
    launch_dry_run = dry_run or bool(blockers) or launch_limit <= 0
    relaunch_limit = min(len(retry_packet_files), launch_limit)
    remaining_launch_limit = max(0, launch_limit - relaunch_limit)

    relaunch_result = JulesLaunchResult(results=[], attempt_results=[], attempted_count=0)
    if relaunch_limit > 0:
        relaunch_result = launch_packets(
            packet_dir=str(base_dir),
            repo_path=repo_path,
            limit=relaunch_limit,
            dry_run=launch_dry_run,
            timeout_s=timeout_s,
            jules_command=jules_command,
            write_state=True,
            skip_launched=False,
            force_packet_files=retry_packet_files[:relaunch_limit],
        )
    launch_result = launch_packets(
        packet_dir=str(base_dir),
        repo_path=repo_path,
        limit=remaining_launch_limit if remaining_launch_limit > 0 else -1,
        dry_run=launch_dry_run,
        timeout_s=timeout_s,
        jules_command=jules_command,
        write_state=True,
        skip_launched=True,
    )
    if relaunch_result.get("attempt_results"):
        combined_attempts = list(relaunch_result.get("attempt_results", []) or []) + list(
            launch_result.get("attempt_results", []) or []
        )
        launch_result["attempt_results"] = combined_attempts
        launch_result["attempted_count"] = len(combined_attempts)

    return capacity, launch_limit, launch_dry_run, relaunch_limit, launch_result
