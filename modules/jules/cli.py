from __future__ import annotations
from .models import *
from .utils import *
import logging
import shutil
import subprocess
import time

LOGGER = logging.getLogger('jules_bridge.jules.cli')

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
        return JulesRemoteResult(
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
            jules_command=jules_command,
            resolved_jules_command=resolved_jules_command,
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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
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
    raw = (command or "").strip() or "jules"
    resolved = shutil.which(raw) or raw
    _append_candidate(candidates, "requested", raw, resolved)
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        _append_candidate(
            candidates,
            "npm_bin_exe",
            str(Path(appdata) / "npm" / "bin" / "jules.exe"),
            str(Path(appdata) / "npm" / "bin" / "jules.exe"),
        )
        _append_candidate(
            candidates,
            "npm_cmd",
            str(Path(appdata) / "npm" / "jules.cmd"),
            str(Path(appdata) / "npm" / "jules.cmd"),
        )
    temp_dir = os.environ.get("TEMP") or os.environ.get("TMP") or ""
    if temp_dir:
        _append_candidate(
            candidates,
            "temp_exe",
            str(Path(temp_dir) / "jules_tmp" / "jules.exe"),
            str(Path(temp_dir) / "jules_tmp" / "jules.exe"),
        )
    return candidates


def _append_candidate(candidates: list[dict], label: str, requested: str, resolved: str) -> None:
    key = str(resolved).lower()
    if any(item.get("resolved", "").lower() == key for item in candidates):
        return
    candidates.append({
        "label": label,
        "requested": requested,
        "resolved": resolved,
        "exists": Path(resolved).exists() if resolved else False,
    })


def _preferred_jules_command(candidates: list[dict], fallback: str) -> str:
    for label in ("npm_bin_exe", "temp_exe", "requested", "npm_cmd"):
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
    except Exception:
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
    except Exception as exc:  # noqa: BLE001
        _terminate_process_tree(process)
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }


def _cli_output_has_error(output: str) -> bool:
    return re.search(r"(?im)^\s*(error|fatal):", output or "") is not None



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
