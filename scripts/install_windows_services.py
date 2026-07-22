"""Script to register UnifiedOperatorService and UnifiedOperatorWatchdog as Windows Services or Task Scheduler tasks."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_VENV_PYTHON = _ROOT / ".venv" / "Scripts" / "python.exe"
if not _VENV_PYTHON.exists():
    _VENV_PYTHON = Path(sys.executable)

_SERVICE_SCRIPT = _ROOT / "scripts" / "UnifiedOperatorService.py"
_WATCHDOG_SCRIPT = _ROOT / "scripts" / "UnifiedOperatorWatchdog.py"


def register_windows_service(service_name: str, display_name: str, script_path: Path) -> bool:
    """Attempt to register service via sc.exe or PowerShell New-Service."""
    bin_path = f'"{_VENV_PYTHON}" "{script_path}"'
    cmd = [
        "powershell",
        "-Command",
        f"if (Get-Service '{service_name}' -ErrorAction SilentlyContinue) {{ Set-Service '{service_name}' -StartupType Automatic }} else {{ New-Service -Name '{service_name}' -DisplayName '{display_name}' -BinaryPathName '{bin_path}' -StartupType Automatic }}",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[ServiceInstall] Successfully registered {service_name}")
            return True
        print(f"[ServiceInstall] PowerShell registration returned {res.returncode}: {res.stderr.strip() or res.stdout.strip()}")
    except Exception as e:
        print(f"[ServiceInstall] Error registering {service_name}: {e}")
    return False


def register_task_scheduler_fallback(task_name: str, script_path: Path) -> bool:
    """Fallback: Register Task Scheduler task for automatic startup on logon."""
    bin_path = str(_VENV_PYTHON)
    arg_str = str(script_path)
    cmd = [
        "schtasks.exe",
        "/Create",
        "/TN", task_name,
        "/TR", f'"{bin_path}" "{arg_str}"',
        "/SC", "ONLOGON",
        "/RL", "LIMITED",
        "/F",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[TaskScheduler] Successfully registered task {task_name}")
            return True
        print(f"[TaskScheduler] schtasks returned {res.returncode}: {res.stderr.strip()}")
    except Exception as e:
        print(f"[TaskScheduler] Error registering task {task_name}: {e}")
    return False


def main() -> None:
    print("[UnifiedOperatorInstaller] Registering services & startup tasks...")
    s1 = register_windows_service("UnifiedOperatorService", "UnifiedOperator Always-On Core Service", _SERVICE_SCRIPT)
    s2 = register_windows_service("UnifiedOperatorWatchdog", "UnifiedOperator Watchdog Monitor", _WATCHDOG_SCRIPT)

    if not s1:
        register_task_scheduler_fallback("UnifiedOperatorServiceTask", _SERVICE_SCRIPT)
    if not s2:
        register_task_scheduler_fallback("UnifiedOperatorWatchdogTask", _WATCHDOG_SCRIPT)


if __name__ == "__main__":
    main()
