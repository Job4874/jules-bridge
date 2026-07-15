"""Gemini CLI orchestration for the Jules Bridge.

This module hides Gemini CLI command resolution, bounded preflight checks, and
headless prompt execution behind a small typed interface.

Public interface:
    gemini_preflight(...) -> GeminiPreflightResult
    run_gemini_prompt(...) -> GeminiPromptResult
    gemini_status_snapshot(...) -> GeminiStatusResult
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
_DEFAULT_PREFLIGHT_STATE = "GEMINI_PREFLIGHT.json"
_DEFAULT_PROMPT_STATE = "GEMINI_PROMPT_STATE.json"
_ALLOWED_APPROVAL_MODES = {"default", "auto_edit", "yolo", "plan"}
_ALLOWED_OUTPUT_FORMATS = {"text", "json", "stream-json"}
_TEXT_LIMIT = 12000


class GeminiPreflightResult(dict):
    """Keys: ready, version, candidate_commands, capabilities, smoke, error."""


class GeminiPromptResult(dict):
    """Keys: status, dry_run, stdout, stderr, exit_code, elapsed_ms, error."""


class GeminiStatusResult(dict):
    """Keys: installed, ready, version, state_path, state_age_s, error."""


def gemini_preflight(
    gemini_command: str = "gemini",
    timeout_s: int = 8,
    run_smoke: bool = False,
    smoke_prompt: str = "Reply with GEMINI_BRIDGE_READY only.",
    model: str = "",
    cwd: str = "",
    write_state: bool = True,
    state_path: str = "",
) -> GeminiPreflightResult:
    """Diagnose Gemini CLI readiness without modifying the workspace.

    Args:
        gemini_command: CLI executable name/path.
        timeout_s: Timeout for bounded CLI probes.
        run_smoke: If true, run a minimal headless prompt in plan mode.
        smoke_prompt: Prompt for the optional live smoke check.
        model: Optional Gemini model passed through to the CLI.
        cwd: Optional working directory for the smoke check.
        write_state: Persist `GEMINI_PREFLIGHT.json`.
        state_path: Explicit preflight state path.

    Returns:
        GeminiPreflightResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        candidates = _candidate_gemini_commands(gemini_command)
        preferred = _preferred_gemini_candidate(candidates, gemini_command)
        preferred_argv = _candidate_argv(preferred)
        version = _run_cli_command([*preferred_argv, "--version"], timeout_s=timeout_s)
        capabilities = {
            "headless_mode": "-p/--prompt",
            "approval_modes": sorted(_ALLOWED_APPROVAL_MODES),
            "output_formats": sorted(_ALLOWED_OUTPUT_FORMATS),
            "mcp": _run_cli_command([*preferred_argv, "mcp", "list"], timeout_s=timeout_s),
            "extensions": _run_cli_command([*preferred_argv, "extensions", "list"], timeout_s=timeout_s),
            "skills": _run_cli_command([*preferred_argv, "skills", "list", "--all"], timeout_s=timeout_s),
        }

        smoke: dict[str, Any] = {
            "status": "skipped",
            "note": "Set run_smoke=true to verify authenticated headless model execution.",
        }
        if run_smoke:
            smoke = dict(run_gemini_prompt(
                prompt=smoke_prompt,
                cwd=cwd,
                model=model,
                approval_mode="plan",
                output_format="text",
                timeout_s=timeout_s,
                gemini_command=gemini_command,
                dry_run=False,
                trust_workspace=True,
                write_state=False,
            ))

        version_ok = version.get("exit_code") == 0 and not version.get("timed_out")
        smoke_ok = not run_smoke or smoke.get("status") == "ok"
        likely_blocker = _preflight_blocker(version, smoke if run_smoke else None)
        payload = GeminiPreflightResult(
            generated_at_utc=generated_at,
            ready=bool(version_ok and smoke_ok),
            installed=bool(version_ok),
            likely_blocker=likely_blocker,
            gemini_command=gemini_command,
            resolved_gemini_command=_display_argv(preferred_argv),
            preferred_gemini_command=_display_argv(preferred_argv),
            candidate_commands=candidates,
            version=version,
            capabilities=capabilities,
            auth_indicators=_auth_indicators(),
            smoke=smoke,
            state_path="",
            note=(
                "Preflight checks install/headless capability. Authenticated model "
                "execution is only checked when run_smoke=true."
            ),
        )
        if write_state:
            destination = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PREFLIGHT_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return GeminiPreflightResult(
            generated_at_utc=generated_at,
            ready=False,
            installed=False,
            likely_blocker="preflight_error",
            error=str(exc),
        )


def run_gemini_prompt(
    prompt: str,
    cwd: str = "",
    model: str = "",
    approval_mode: str = "plan",
    output_format: str = "text",
    timeout_s: int = 120,
    gemini_command: str = "gemini",
    dry_run: bool = True,
    trust_workspace: bool = True,
    write_state: bool = True,
    state_path: str = "",
) -> GeminiPromptResult:
    """Run one Gemini CLI headless prompt, defaulting to dry-run and plan mode.

    Args:
        prompt: Headless prompt passed to `gemini -p`.
        cwd: Optional working directory.
        model: Optional model string passed to `--model`.
        approval_mode: Gemini approval mode. Defaults to read-only `plan`.
        output_format: text, json, or stream-json.
        timeout_s: Bounded subprocess timeout.
        gemini_command: CLI executable name/path.
        dry_run: If true, return a command preview only.
        trust_workspace: Pass `--skip-trust` so headless mode does not prompt.
        write_state: Persist the last prompt result.
        state_path: Explicit prompt state path.

    Returns:
        GeminiPromptResult. Never raises.
    """
    started = datetime.now(timezone.utc)
    try:
        clean_prompt = prompt or ""
        if not clean_prompt.strip():
            return GeminiPromptResult(status="error", error="prompt is required", dry_run=dry_run)
        clean_approval = (approval_mode or "plan").strip()
        if clean_approval not in _ALLOWED_APPROVAL_MODES:
            return GeminiPromptResult(
                status="error",
                error=f"approval_mode must be one of {sorted(_ALLOWED_APPROVAL_MODES)}",
                dry_run=dry_run,
            )
        clean_output = (output_format or "text").strip()
        if clean_output not in _ALLOWED_OUTPUT_FORMATS:
            return GeminiPromptResult(
                status="error",
                error=f"output_format must be one of {sorted(_ALLOWED_OUTPUT_FORMATS)}",
                dry_run=dry_run,
            )

        candidates = _candidate_gemini_commands(gemini_command)
        preferred = _preferred_gemini_candidate(candidates, gemini_command)
        argv = [
            *_candidate_argv(preferred),
            "-p",
            clean_prompt,
            "--approval-mode",
            clean_approval,
            "--output-format",
            clean_output,
        ]
        if model or os.environ.get("GEMINI_MODEL"):
            argv.extend(["--model", (model or os.environ.get("GEMINI_MODEL", "")).strip()])
        if trust_workspace:
            argv.append("--skip-trust")

        command_preview = _redacted_prompt_argv(argv, clean_prompt)
        resolved_cwd = _resolved_cwd(cwd)
        if dry_run:
            return GeminiPromptResult(
                status="dry_run",
                dry_run=True,
                command_preview=command_preview,
                cwd=str(resolved_cwd),
                approval_mode=clean_approval,
                output_format=clean_output,
                model=(model or os.environ.get("GEMINI_MODEL", "")).strip(),
                note="Set dry_run=false to invoke Gemini CLI.",
            )

        # Build a clean environment: strip invalid/placeholder API keys so the
        # CLI falls back to Google OAuth (your Google account login). Only strip
        # if the key is clearly a placeholder or not set.
        _clean_env = os.environ.copy()
        for _key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            _val = _clean_env.get(_key, "")
            # Remove if blank, starts with 'your' (placeholder), or is a known placeholder value
            _is_placeholder = (
                not _val
                or _val.lower().startswith("your")
                or _val.lower() in ("none", "placeholder", "changeme", "your-api-key")
            )
            if _is_placeholder:
                _clean_env.pop(_key, None)

        result = _run_cli_command(argv, timeout_s=timeout_s, cwd=str(resolved_cwd), env=_clean_env)
        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
        status = _prompt_status(result)
        payload = GeminiPromptResult(
            status=status,
            dry_run=False,
            command_preview=command_preview,
            cwd=str(resolved_cwd),
            approval_mode=clean_approval,
            output_format=clean_output,
            model=(model or os.environ.get("GEMINI_MODEL", "")).strip(),
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
        return GeminiPromptResult(status="error", error=str(exc), dry_run=dry_run)


def gemini_status_snapshot(state_path: str = "") -> GeminiStatusResult:
    """Return compact Gemini CLI status for dashboard use without spawning CLI."""
    try:
        candidates = _candidate_gemini_commands("gemini")
        preferred = _preferred_gemini_candidate(candidates, "gemini")
        state_file = Path(state_path) if state_path else _DEFAULT_OUTPUT_DIR / _DEFAULT_PREFLIGHT_STATE
        state = _read_json_file(state_file)
        state_age_s = None
        if state_file.exists():
            state_age_s = round(datetime.now(timezone.utc).timestamp() - state_file.stat().st_mtime)
        version = state.get("version", {}) if isinstance(state, dict) else {}
        stdout = version.get("stdout", "") if isinstance(version, dict) else ""
        return GeminiStatusResult(
            installed=bool(preferred.get("exists")),
            ready=bool(state.get("ready", False)) if isinstance(state, dict) else False,
            version=(stdout or "").strip(),
            state_path=str(state_file) if state_file.exists() else "",
            state_age_s=state_age_s,
            preferred_gemini_command=_display_argv(_candidate_argv(preferred)),
            headless_mode="-p/--prompt",
            last_blocker=state.get("likely_blocker", "") if isinstance(state, dict) else "",
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return GeminiStatusResult(installed=False, ready=False, error=str(exc))


def _candidate_gemini_commands(command: str) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    raw = (command or "").strip() or "gemini"
    resolved = shutil.which(raw) or raw
    _append_candidate(candidates, seen, "requested", raw, resolved)

    explicit = os.environ.get("GEMINI_CLI_PATH", "").strip()
    if explicit:
        _append_candidate(candidates, seen, "env_cli", explicit, explicit)

    for npm_prefix in _npm_prefix_candidates():
        _append_candidate(
            candidates,
            seen,
            "npm_bundle_js",
            str(npm_prefix / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"),
            str(npm_prefix / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"),
        )
        _append_candidate(candidates, seen, "npm_cmd", str(npm_prefix / "gemini.cmd"), str(npm_prefix / "gemini.cmd"))
        _append_candidate(candidates, seen, "npm_script", str(npm_prefix / "gemini"), str(npm_prefix / "gemini"))

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        npm_dir = Path(appdata) / "npm"
        _append_candidate(
            candidates,
            seen,
            "npm_bundle_js",
            str(npm_dir / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"),
            str(npm_dir / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"),
        )
        _append_candidate(candidates, seen, "npm_cmd", str(npm_dir / "gemini.cmd"), str(npm_dir / "gemini.cmd"))

    return candidates


def _npm_prefix_candidates() -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for raw in (
        os.environ.get("npm_config_prefix", ""),
        str(Path.home() / ".npm-packages"),
        str(Path(os.environ.get("USERPROFILE", "")) / ".npm-packages") if os.environ.get("USERPROFILE") else "",
        str(Path(os.environ.get("APPDATA", "")) / "npm") if os.environ.get("APPDATA") else "",
        # hermes/node — non-standard npm prefix used on this machine
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "node") if os.environ.get("LOCALAPPDATA") else "",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "npm") if os.environ.get("LOCALAPPDATA") else "",
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


def _append_candidate(candidates: list[dict], seen: set[str], label: str, requested: str, resolved: str) -> None:
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


def _preferred_gemini_candidate(candidates: list[dict], fallback_command: str) -> dict:
    for label in ("env_cli", "npm_bundle_js", "npm_cmd", "requested", "npm_script"):
        for candidate in candidates:
            if candidate.get("label") == label and candidate.get("exists"):
                return candidate
    resolved = shutil.which((fallback_command or "").strip() or "gemini") or ((fallback_command or "").strip() or "gemini")
    return {
        "label": "fallback",
        "requested": fallback_command or "gemini",
        "resolved": resolved,
        "exists": bool(shutil.which(resolved) or Path(resolved).exists()),
    }


def _candidate_argv(candidate: dict) -> list[str]:
    resolved = str(candidate.get("resolved", "")).strip() or "gemini"
    suffix = Path(resolved).suffix.lower()
    if suffix == ".js":
        node = shutil.which("node") or "node"
        return [node, resolved]
    if suffix == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", resolved]
    return [resolved]


def _auth_indicators() -> dict:
    home = Path.home()
    raw_paths = [
        home / ".gemini",
        home / ".config" / "gemini",
        Path(os.environ.get("APPDATA", "")) / "gemini",
        Path(os.environ.get("LOCALAPPDATA", "")) / "gemini",
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
        "gemini_api_key_present": bool(os.environ.get("GEMINI_API_KEY")),
        "google_api_key_present": bool(os.environ.get("GOOGLE_API_KEY")),
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


def _run_cli_command(command: list[str], timeout_s: int, cwd: str | None = None, env: dict | None = None) -> dict:
    timeout = max(1, int(timeout_s or 1))
    started = datetime.now(timezone.utc)
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,  # None = inherit everything; dict = use sanitized copy
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
    if "trust" in combined:
        return "workspace_trust_required"
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


def _display_argv(argv: list[str]) -> str:
    return " ".join(argv)


def _redacted_prompt_argv(argv: list[str], prompt: str) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for index, item in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if item in ("-p", "--prompt") and index + 1 < len(argv):
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
