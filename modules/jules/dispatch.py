from __future__ import annotations
from .models import *
from .utils import *
from .parser import *
from .cli import *
import logging
import shutil

LOGGER = logging.getLogger('jules_bridge.jules.dispatch')

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
        for packet in packets:
            command = [resolved_jules_command, "new"]
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
            resolved_jules_command=resolved_jules_command,
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
        "- Do not stop at a plan or ask for plan approval; plan briefly in the report and proceed unless a hard blocker prevents work.",
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
    except Exception:
        return []
    return ordered


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
