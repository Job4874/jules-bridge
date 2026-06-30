"""Shell executor deep module — powershell / cmd / bash routing.

Simple typed interface hiding shell discovery, arg construction,
subprocess management, and output coercion.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import hashlib
import logging
from typing import Optional

LOGGER = logging.getLogger("jules_bridge")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SUPPORTED_SHELLS = ("powershell", "cmd", "bash")

_BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
)

# In-memory cache for shell results: { hash(cmd+cwd+shell): (timestamp, ShellResult) }
_shell_result_cache = {}

_UNIX_SHELL_PATTERNS = (
    re.compile(r"\|\s*head\b"),
    re.compile(r"\|\s*tail\b"),
    re.compile(r"\|\s*grep\b"),
    re.compile(r"\|\s*awk\b"),
    re.compile(r"\|\s*sed\b"),
    re.compile(r"\bls\s+-[a-zA-Z]"),
    re.compile(r"/tmp/"),
    re.compile(r"\$\("),
    re.compile(r"\bhead\s+-n\b"),
    re.compile(r"\btail\s+-n\b"),
)

# ---------------------------------------------------------------------------
# Typed return contract
# ---------------------------------------------------------------------------

class ShellResult(dict):
    """Result of a shell execution.

    Keys always present:
      exit_code (int): process return code (also aliased as 'code')
      stdout (str): standard output text
      stderr (str): standard error text
      shell (str): resolved shell name used ('powershell', 'cmd', 'bash')
    """


class ShellNotAvailableError(ValueError):
    """Raised when a requested shell is not installed or configured."""


class UnsupportedShellError(ValueError):
    """Raised when an unknown shell selector is provided."""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _looks_like_unix_command(command: str) -> bool:
    """Return True when the command string uses common Unix shell idioms."""
    return any(pattern.search(command) for pattern in _UNIX_SHELL_PATTERNS)


def _resolve_shell_for_command(command: str, shell: str) -> tuple[str, bool]:
    """Pick the effective shell, auto-routing Unix syntax to Git Bash when needed."""
    requested = (shell or "powershell").strip().lower()
    normalized = requested
    if requested in ("ps", "windows-powershell"):
        normalized = "powershell"

    if normalized != "powershell" or not _looks_like_unix_command(command):
        return normalized, False

    try:
        _discover_bash()
    except ShellNotAvailableError as exc:
        raise ShellNotAvailableError(
            "Command uses Unix shell syntax (pipes, head, /tmp/, etc.) but Git Bash "
            "is not installed on this host. Install Git for Windows or set "
            "JULES_BASH_PATH, then retry with \"shell\": \"bash\". "
            f"Original error: {exc}"
        ) from exc
    return "bash", True


def _discover_bash() -> str:
    """Locate the bash executable, raising ShellNotAvailableError if missing."""
    configured = os.environ.get("JULES_BASH_PATH", "").strip()
    if configured:
        if os.path.exists(configured):
            return configured
        raise ShellNotAvailableError(
            f"JULES_BASH_PATH is set but not found: {configured}"
        )

    for candidate in _BASH_CANDIDATES:
        if os.path.exists(candidate):
            return candidate

    for executable in ("bash.exe", "bash"):
        found = shutil.which(executable)
        if found:
            return found

    raise ShellNotAvailableError(
        "bash shell is not installed or configured on this host. "
        f"Supported shells: {list(_SUPPORTED_SHELLS)}"
    )


def _build_args(shell_name: str, command: str) -> tuple[str, list[str]]:
    """Return (resolved_shell_name, subprocess_args_list).

    Raises:
        UnsupportedShellError: for unknown selector.
        ShellNotAvailableError: if bash is requested but not found.
        ValueError: if wsl/linux is requested (explicitly disabled).
    """
    shell_name = (shell_name or "powershell").strip().lower()

    if shell_name in ("ps", "powershell", "windows-powershell"):
        return "powershell", [
            "powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command
        ]
    if shell_name == "cmd":
        return "cmd", ["cmd.exe", "/d", "/s", "/c", command]
    if shell_name == "bash":
        return "bash", [_discover_bash(), "-lc", command]
    if shell_name in ("wsl", "linux"):
        raise ValueError(
            "WSL is not enabled for /shell because this host has no installed "
            f"WSL distribution. Supported shells: {list(_SUPPORTED_SHELLS)}"
        )
    raise UnsupportedShellError(
        f"Unsupported shell selector: {shell_name!r}. "
        f"Supported shells: {list(_SUPPORTED_SHELLS)}"
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def spawn(
    command: str,
    shell: str = "cmd",
    cwd: Optional[str] = None,
) -> ShellResult:
    """Launch a command without waiting for completion.

    Intended for operator workflows that open apps or detach background jobs.
    """
    resolved_shell, args = _build_args(shell, command)
    effective_cwd = cwd or os.getcwd()
    proc = subprocess.Popen(
        args,
        cwd=effective_cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return ShellResult(
        exit_code=0,
        code=0,
        stdout="",
        stderr="",
        shell=resolved_shell,
        pid=proc.pid,
        spawned=True,
    )


def execute(
    command: str,
    shell: str = "powershell",
    cwd: Optional[str] = None,
    timeout: int = 30,
    stdin: Optional[str] = None,
    bypass_cache: bool = False,
) -> ShellResult:
    """Execute a command in the specified shell.

    Args:
        command: Command string to run.
        shell: Shell selector — 'powershell' (default), 'cmd', or 'bash'.
        cwd: Working directory. Defaults to current directory.
        timeout: Seconds before raising subprocess.TimeoutExpired.
        stdin: Optional text to pipe to stdin.

    Returns:
        ShellResult with exit_code, stdout, stderr, shell.

    Raises:
        UnsupportedShellError: unknown shell selector.
        ShellNotAvailableError: bash requested but not installed.
        ValueError: wsl/linux shell requested.
        subprocess.TimeoutExpired: if command exceeds timeout.
    """
    effective_cwd = cwd or os.getcwd()
    resolved_shell, shell_auto_selected = _resolve_shell_for_command(command, shell)
    cache_ttl = 0 if bypass_cache else int(os.environ.get("SHELL_CACHE_TTL_S", "0"))

    # Cache key: hash(command + cwd + shell)
    cache_key = hashlib.sha256(
        f"{command}{effective_cwd}{resolved_shell}".encode()
    ).hexdigest()

    now = time.time()
    if cache_key in _shell_result_cache and cache_ttl > 0:
        ts, cached_res = _shell_result_cache[cache_key]
        if now - ts < cache_ttl:
            cached = ShellResult(cached_res)
            cached["cache_hit"] = True
            return cached

    resolved_shell, args = _build_args(resolved_shell, command)

    start_time = time.time()
    try:
        res = subprocess.run(
            args,
            cwd=effective_cwd,
            capture_output=True,
            text=True,
            input=stdin,
            timeout=timeout,
            check=False,
        )
        duration = time.time() - start_time
        if duration > 5.0:
            LOGGER.warning("Slow shell call (>5s): %s (duration: %.2fs)", command[:50], duration)

        result = ShellResult(
            exit_code=res.returncode,
            code=res.returncode,          # legacy alias
            stdout=_coerce_text(res.stdout),
            stderr=_coerce_text(res.stderr),
            shell=resolved_shell,
            cache_hit=False,
        )
        if shell_auto_selected:
            result["shell_auto_selected"] = True
            result["requested_shell"] = (shell or "powershell").strip().lower()

        # Update cache
        if cache_ttl > 0:
            _shell_result_cache[cache_key] = (now, result)
        return result

    except subprocess.TimeoutExpired:
        LOGGER.warning("Shell call timed out: %s", command[:50])
        raise


def available_shells() -> list[str]:
    """Return list of shell names available on this host.

    Always includes 'powershell' and 'cmd'. Includes 'bash' only if
    a Git Bash installation is found.
    """
    shells = ["powershell", "cmd"]
    try:
        _discover_bash()
        shells.append("bash")
    except ShellNotAvailableError:
        pass
    return shells
