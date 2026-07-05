"""Antigravity CLI orchestration for the Jules Bridge.

This module hides Google Antigravity CLI command resolution, bounded preflight
checks, plugin/model discovery, and dry-run-first prompt execution.

Public interface:
    antigravity_preflight(...) -> AntigravityPreflightResult
    run_antigravity_prompt(...) -> AntigravityPromptResult
    antigravity_status_snapshot(...) -> AntigravityStatusResult
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUTPUT_DIR = _ROOT / "jules_inbox" / "gemini"
_DEFAULT_PREFLIGHT_STATE = "ANTIGRAVITY_PREFLIGHT.json"
_DEFAULT_PROMPT_STATE = "ANTIGRAVITY_PROMPT_STATE.json"
_TEXT_LIMIT = 12000


class AntigravityPreflightResult(dict):
    """Keys: ready, version, candidate_commands, capabilities, smoke, error."""


class AntigravityPromptResult(dict):
    """Keys: status, dry_run, stdout, stderr, exit_code, elapsed_ms, error."""


class AntigravityStatusResult(dict):
    """Keys: installed, ready, version, state_path, state_age_s, error."""


def antigravity_preflight(
    agy_command: str = "agy",
    timeout_s: int = 8,
    run_smoke: bool = False,
    smoke_prompt: str = "Reply with ANTIGRAVITY_BRIDGE_READY only.",
    model: str = "",
    cwd: str = "",
    write_state: bool = True,
    state_path: str = "",
) -> AntigravityPreflightResult:
    """Diagnose Antigravity CLI readiness without modifying the workspace.

    Args:
        agy_command: CLI executable name/path.
        timeout_s: Timeout for bounded CLI probes.
        run_smoke: If true, run a minimal noninteractive prompt.
        smoke_prompt: Prompt for the optional live smoke check.
        model: Optional model passed through to the CLI.
        cwd: Optional working directory for the smoke check.
        write_state: Persist `ANTIGRAVITY_PREFLIGHT.json`.
        state_path: Explicit preflight state path.

    Returns:
        AntigravityPreflightResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        candidates = _candidate_antigravity_commands(agy_command)
        preferred = _preferred_antigravity_candidate(candidates, agy_command)
        preferred_argv = _candidate_argv(preferred)
        version = _run_cli_command([*preferred_argv, "--version"], timeout_s=timeout_s)
        help_result = _run_cli_command([*preferred_argv, "--help"], timeout_s=timeout_s)
        models = _run_cli_command([*preferred_argv, "models"], timeout_s=timeout_s)
        plugins = _run_cli_command([*preferred_argv, "plugin", "list"], timeout_s=timeout_s)
        capabilities = {
            "headless_mode": "-p/--print",
            "plugin_management": "plugin list/install/uninstall/enable/disable",
            "subcommands": _parse_subcommands(help_result.get("stderr", "") or help_result.get("stdout", "")),
            "models": models,
            "plugin_list": plugins,
        }

        smoke: dict[str, Any] = {
            "status": "skipped",
            "note": "Set run_smoke=true to verify noninteractive model execution.",
        }
        if run_smoke:
            smoke = dict(run_antigravity_prompt(
                prompt=smoke_prompt,
                cwd=cwd,
                model=model,
                timeout_s=timeout_s,
                agy_command=agy_command,
                dry_run=False,
                write_state=False,
            ))

        version_ok = version.get("exit_code") == 0 and not version.get("timed_out")
        smoke_ok = not run_smoke or smoke.get("status") == "ok"
        likely_blocker = _preflight_blocker(version, smoke if run_smoke else None)
        payload = AntigravityPreflightResult(
            generated_at_utc=generated_at,
            ready=bool(version_ok and smoke_ok),
            installed=bool(version_ok),
            likely_blocker=likely_blocker,
            agy_command=agy_command,
            resolved_antigravity_command=_display_argv(preferred_argv),
            preferred_antigravity_command=_display_argv(preferred_argv),
            candidate_commands=candidates,
            version=version,
            capabilities=capabilities,
            auth_indicators=_auth_indicators(),
            smoke=smoke,
            state_path="",
            note=(
                "Antigravity is Google's supported terminal-agent CLI successor "
                "for individual Gemini CLI users; model execution is only checked "
                "when run_smoke=true."
            ),
        )
        if write_state:
            destination = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PREFLIGHT_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return AntigravityPreflightResult(
            generated_at_utc=generated_at,
            ready=False,
            installed=False,
            likely_blocker="preflight_error",
            error=str(exc),
        )


def run_antigravity_prompt(
    prompt: str,
    cwd: str = "",
    model: str = "",
    timeout_s: int = 120,
    agy_command: str = "agy",
    dry_run: bool = True,
    write_state: bool = True,
    state_path: str = "",
) -> AntigravityPromptResult:
    """Run one Antigravity CLI prompt, defaulting to dry-run.

    Args:
        prompt: Headless prompt passed to `agy -p`.
        cwd: Optional working directory.
        model: Optional model string passed to `--model`.
        timeout_s: Bounded subprocess timeout.
        agy_command: CLI executable name/path.
        dry_run: If true, return a command preview only.
        write_state: Persist the last prompt result.
        state_path: Explicit prompt state path.

    Returns:
        AntigravityPromptResult. Never raises.
    """
    started = datetime.now(timezone.utc)
    try:
        clean_prompt = prompt or ""
        if not clean_prompt.strip():
            return AntigravityPromptResult(status="error", error="prompt is required", dry_run=dry_run)

        candidates = _candidate_antigravity_commands(agy_command)
        preferred = _preferred_antigravity_candidate(candidates, agy_command)
        timeout = max(1, int(timeout_s or 1))
        argv = [
            *_candidate_argv(preferred),
            "-p",
            clean_prompt,
            "--print-timeout",
            f"{timeout}s",
        ]
        if model or os.environ.get("ANTIGRAVITY_MODEL"):
            argv.extend(["--model", (model or os.environ.get("ANTIGRAVITY_MODEL", "")).strip()])

        command_preview = _redacted_prompt_argv(argv, clean_prompt)
        resolved_cwd = _resolved_cwd(cwd)
        if dry_run:
            return AntigravityPromptResult(
                status="dry_run",
                dry_run=True,
                command_preview=command_preview,
                cwd=str(resolved_cwd),
                model=(model or os.environ.get("ANTIGRAVITY_MODEL", "")).strip(),
                note="Set dry_run=false to invoke Antigravity CLI.",
            )

        result = _run_cli_command(argv, timeout_s=timeout, cwd=str(resolved_cwd))
        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
        status = _prompt_status(result)
        payload = AntigravityPromptResult(
            status=status,
            dry_run=False,
            command_preview=command_preview,
            cwd=str(resolved_cwd),
            model=(model or os.environ.get("ANTIGRAVITY_MODEL", "")).strip(),
            exit_code=result.get("exit_code"),
            timed_out=result.get("timed_out", False),
            stdout=_bounded_text(result.get("stdout", "")),
            stderr=_bounded_text(result.get("stderr", "")),
            elapsed_ms=elapsed_ms,
            likely_blocker=_prompt_blocker(result),
            state_path="",
        )
        if write_state:
            destination = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PROMPT_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return AntigravityPromptResult(status="error", error=str(exc), dry_run=dry_run)


def antigravity_status_snapshot(state_path: str = "") -> AntigravityStatusResult:
    """Return compact Antigravity CLI status for dashboard use without spawning CLI."""
    try:
        candidates = _candidate_antigravity_commands("agy")
        preferred = _preferred_antigravity_candidate(candidates, "agy")
        state_file = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PREFLIGHT_STATE
        state = _read_json_file(state_file)
        state_age_s = None
        if state_file.exists():
            state_age_s = round(datetime.now(timezone.utc).timestamp() - state_file.stat().st_mtime)
        version = state.get("version", {}) if isinstance(state, dict) else {}
        stdout = version.get("stdout", "") if isinstance(version, dict) else ""
        models = state.get("capabilities", {}).get("models", {}) if isinstance(state, dict) else {}
        model_lines = _nonempty_lines(models.get("stdout", "") if isinstance(models, dict) else "")
        return AntigravityStatusResult(
            installed=bool(preferred.get("exists")),
            ready=bool(state.get("ready", False)) if isinstance(state, dict) else False,
            version=(stdout or "").strip(),
            state_path=str(state_file) if state_file.exists() else "",
            state_age_s=state_age_s,
            preferred_antigravity_command=_display_argv(_candidate_argv(preferred)),
            headless_mode="-p/--print",
            model_count=len(model_lines),
            last_blocker=state.get("likely_blocker", "") if isinstance(state, dict) else "",
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return AntigravityStatusResult(installed=False, ready=False, error=str(exc))


def _candidate_antigravity_commands(command: str) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    raw = (command or "").strip() or "agy"
    resolved = shutil.which(raw) or raw
    _append_candidate(candidates, seen, "requested", raw, resolved)

    for env_key in ("ANTIGRAVITY_CLI_PATH", "AGY_CLI_PATH"):
        explicit = os.environ.get(env_key, "").strip()
        if explicit:
            _append_candidate(candidates, seen, env_key.lower(), explicit, explicit)

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        _append_candidate(
            candidates,
            seen,
            "localappdata_agy",
            str(Path(localappdata) / "agy" / "bin" / "agy.exe"),
            str(Path(localappdata) / "agy" / "bin" / "agy.exe"),
        )
    home = Path.home()
    _append_candidate(
        candidates,
        seen,
        "home_agy",
        str(home / ".antigravity" / "bin" / "agy.exe"),
        str(home / ".antigravity" / "bin" / "agy.exe"),
    )
    for name in ("agy", "antigravity"):
        found = shutil.which(name)
        if found:
            _append_candidate(candidates, seen, f"path_{name}", name, found)
    return candidates


def _append_candidate(candidates: list[dict], seen: set[str], label: str, requested: str, resolved: str) -> None:
    key = str(resolved).lower()
    if key in seen:
        return
    seen.add(key)
    candidates.append({
        "label": label,
        "requested": requested,
        "resolved": resolved,
        "exists": bool(Path(resolved).exists() or shutil.which(resolved)),
    })


def _preferred_antigravity_candidate(candidates: list[dict], fallback_command: str) -> dict:
    for label in ("antigravity_cli_path", "agy_cli_path", "localappdata_agy", "path_agy", "requested", "home_agy"):
        for candidate in candidates:
            if candidate.get("label") == label and candidate.get("exists"):
                return candidate
    for candidate in candidates:
        if candidate.get("exists"):
            return candidate
    resolved = shutil.which((fallback_command or "").strip() or "agy") or ((fallback_command or "").strip() or "agy")
    return {
        "label": "fallback",
        "requested": fallback_command or "agy",
        "resolved": resolved,
        "exists": bool(shutil.which(resolved) or Path(resolved).exists()),
    }


def _candidate_argv(candidate: dict) -> list[str]:
    resolved = str(candidate.get("resolved", "")).strip() or "agy"
    if Path(resolved).suffix.lower() == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", resolved]
    return [resolved]


def _auth_indicators() -> dict:
    home = Path.home()
    raw_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "agy",
        Path(os.environ.get("LOCALAPPDATA", "")) / "antigravity",
        home / ".gemini" / "antigravity-cli",
        home / ".gemini" / "antigravity-ide",
    ]
    entries = []
    for path in raw_paths:
        if not str(path):
            continue
        exists = path.exists()
        entries.append({
            "path": str(path),
            "exists": exists,
            "item_count": _safe_child_count(path) if exists else 0,
        })
    return {
        "known_config_paths": entries,
        "any_known_config_path_exists": any(item["exists"] for item in entries),
    }


def _safe_child_count(path: Path) -> int:
    try:
        if path.is_dir():
            return len(list(path.iterdir()))
        return 1
    except Exception:  # pylint: disable=broad-exception-caught
        return 0


def _run_cli_command(command: list[str], timeout_s: int, cwd: str | None = None) -> dict:
    timeout = max(1, int(timeout_s or 1))
    started = datetime.now(timezone.utc)
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
            return {
                "exit_code": process.returncode,
                "stdout": _bounded_text(stdout or ""),
                "stderr": _bounded_text(stderr or ""),
                "timed_out": False,
                "elapsed_ms": elapsed_ms,
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
            elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
            return {
                "exit_code": None,
                "stdout": _bounded_text(stdout),
                "stderr": _bounded_text(stderr),
                "timed_out": True,
                "elapsed_ms": elapsed_ms,
            }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
            "elapsed_ms": round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2),
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


def _resolved_cwd(cwd: str) -> Path:
    if not cwd:
        return _ROOT
    path = Path(cwd)
    if path.is_dir():
        return path
    return _ROOT


def _prompt_status(result: dict) -> str:
    if result.get("timed_out"):
        return "timeout"
    if result.get("exit_code") == 0:
        return "ok"
    return "failed"


def _prompt_blocker(result: dict) -> str:
    if result.get("timed_out"):
        return "timeout"
    combined = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    if "auth" in combined or "login" in combined or "api key" in combined or "credential" in combined:
        return "auth_required"
    if result.get("exit_code") not in (0, None):
        return "cli_failed"
    return ""


def _preflight_blocker(version: dict, smoke: dict | None) -> str:
    if version.get("timed_out"):
        return "version_timeout"
    if version.get("exit_code") != 0:
        return "version_failed"
    if smoke and smoke.get("status") != "ok":
        return smoke.get("likely_blocker") or "smoke_failed"
    return ""


def _parse_subcommands(text: str) -> list[str]:
    found: list[str] = []
    in_section = False
    for line in (text or "").splitlines():
        if line.strip() == "Available subcommands:":
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("  "):
            found.append(line.strip().split()[0])
        elif found:
            break
    return found


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _display_argv(argv: list[str]) -> str:
    return " ".join(argv)


def _redacted_prompt_argv(argv: list[str], prompt: str) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for index, item in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if item in ("-p", "--prompt", "--print") and index + 1 < len(argv):
            redacted.extend([item, f"[prompt:{len(prompt)} chars]"])
            skip_next = True
            continue
        redacted.append(item)
    return redacted


def _bounded_text(text: str, limit: int = _TEXT_LIMIT) -> str:
    clean = text or ""
    if len(clean) <= limit:
        return clean
    return clean[-limit:]


def _read_json_file(path: Path) -> dict:
    try:
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:  # pylint: disable=broad-exception-caught
        return {}


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
