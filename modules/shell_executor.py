"""Shell executor deep module — powershell / cmd / bash routing.

Simple typed interface hiding shell discovery, arg construction,
subprocess management, and output coercion.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SUPPORTED_SHELLS = ("powershell", "cmd", "bash")

_BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
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
    resolved_shell, args = _build_args(shell, command)
    effective_cwd = cwd or os.getcwd()

    res = subprocess.run(
        args,
        cwd=effective_cwd,
        capture_output=True,
        text=True,
        input=stdin,
        timeout=timeout,
        check=False,
    )

    return ShellResult(
        exit_code=res.returncode,
        code=res.returncode,          # legacy alias
        stdout=_coerce_text(res.stdout),
        stderr=_coerce_text(res.stderr),
        shell=resolved_shell,
    )


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
