from __future__ import annotations
from .models import *
from .utils import *
from .parser import *
from .cli import *
from .dispatch import *
from .reporting import *
import logging
import time

LOGGER = logging.getLogger('jules_bridge.jules.orchestrator')

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
        dispatch_result = None
        if content or source_path:
            dispatch_result = build_dispatch(
                content=content,
                source_path=source_path,
                max_instances=max_instances,
                include_statuses=include_statuses,
                write_packets=write_packets,
                output_dir=str(base_dir),
                repo_path=repo_path,
            )
        else:
            packets = _resolve_packet_files(packet_dir=str(base_dir))
            dispatch_result = JulesDispatchResult(
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

        blockers = []
        if dispatch_result.get("error"):
            blockers.append(f"Dispatch failed: {dispatch_result.get('error')}")

        sessions_result = JulesRemoteResult(
            dry_run=True,
            status="skipped",
            session_ids=[],
            note="Remote session check skipped.",
        )
        if check_remote:
            sessions_result = list_remote_sessions(
                jules_command=jules_command,
                timeout_s=timeout_s,
                dry_run=dry_run,
            )

        remote_ready = (not check_remote) or dry_run or sessions_result.get("status") == "ok"
        if check_remote and not dry_run and require_remote_ready and not remote_ready:
            blockers.append(
                "Remote Jules session listing did not return ok; live launch/pull stayed disabled."
            )

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

        pull_results = []
        pull_ids = []
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
                    pull_remote_session(
                        session_id=session_id,
                        repo_path=repo_path,
                        output_dir=str(base_dir / _DEFAULT_PULL_DIR),
                        dry_run=pull_dry_run,
                        timeout_s=timeout_s,
                        jules_command=jules_command,
                        write_result=True,
                    )
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
            pull_results=[dict(result) for result in pull_results],
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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
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
        if content or source_path:
            dispatch_result = build_dispatch(
                content=content,
                source_path=source_path,
                max_instances=max_instances,
                include_statuses=include_statuses,
                write_packets=True,
                output_dir=str(base_dir),
                repo_path=repo_path,
            )
        else:
            packets = _resolve_packet_files(packet_dir=str(base_dir))
            dispatch_result = JulesDispatchResult(
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
        stale_unknown_packet_files = _stale_unknown_remote_packet_files(
            existing_launch_state,
            remote_status_rows,
        )
        plan_awaiting_packet_files = _plan_awaiting_remote_packet_files(
            existing_launch_state,
            remote_status_rows,
        )
        retry_packet_files = _merge_unique(failed_packet_files, stale_unknown_packet_files)
        retry_packet_files = _merge_unique(retry_packet_files, plan_awaiting_packet_files)

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
        cot_result = build_cot_ledger(packet_dir=str(base_dir), write_ledger=True)
        if cot_result.get("error"):
            blockers.append(f"COT ledger failed: {cot_result.get('error')}")

        launched_this_cycle = sum(
            1
            for item in launch_result.get("attempt_results", []) or []
            if item.get("status") == "launched"
        )
        all_complete = bool(cot_result.get("all_complete"))
        status = "complete" if all_complete else "blocked" if blockers else "scaled" if launched_this_cycle else "pending"
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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
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
