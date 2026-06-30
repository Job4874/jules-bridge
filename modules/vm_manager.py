"""VM manager deep module -- resource pressure and guarded VM boot.

This module hides host metric collection, allowlisted script resolution, and
dry-run-first VM boot execution behind small typed contracts.

Public interface:
    detect_resource_pressure(...) -> ResourcePressureResult
    boot_secondary_vm(...) -> VMBootResult
    check_and_scale_compute(...) -> str
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_CPU_THRESHOLD = 90.0
_DEFAULT_MEMORY_THRESHOLD = 90.0
_VM_SCRIPT_DIR_ENV = "JULES_VM_SCRIPT_DIR"
_ALLOWED_SCRIPT_EXTENSIONS = {".ps1", ".cmd", ".bat"}


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class ResourcePressureResult(dict):
    """Result of host resource pressure detection.

    Keys always present:
      status (str): ok, maxed_out, or error
      cpu_percent (float | None): CPU utilization percentage
      memory_percent (float | None): memory utilization percentage
      maxed_out (bool): whether any threshold was crossed
      reasons (list[str]): threshold-crossing reasons
      error (str | None): sanitized failure detail
    """


class VMBootResult(dict):
    """Result of a guarded secondary-VM boot request.

    Keys always present:
      status (str): dry_run, blocked, started, or error
      selected_script (str): resolved allowlisted script path, or empty
      started (bool): whether process launch was attempted and started
      dry_run (bool): whether execution was intentionally skipped
      error (str | None): sanitized failure detail
    Optional:
      pid (int): started process id
    """


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _as_percent(value: float | int | str | None, field_name: str) -> float | None:
    if value is None:
        return None
    try:
        percent = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number between 0 and 100") from exc
    if percent < 0 or percent > 100:
        raise ValueError(f"{field_name} must be a number between 0 and 100")
    return percent


def _threshold_value(thresholds: dict | None, key: str, default: float) -> float:
    if not thresholds or thresholds.get(key) is None:
        return default
    value = _as_percent(thresholds.get(key), key)
    if value is None:
        return default
    return value


def _read_host_metrics() -> tuple[float | None, float | None, str | None]:
    """Read Windows CPU and memory pressure using built-in PowerShell/CIM."""
    command = (
        "$cpu = (Get-CimInstance Win32_Processor | "
        "Measure-Object -Property LoadPercentage -Average).Average; "
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "$mem = (($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / "
        "$os.TotalVisibleMemorySize) * 100; "
        "[pscustomobject]@{"
        "cpu_percent=[math]::Round($cpu,2);"
        "memory_percent=[math]::Round($mem,2)"
        "} | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return None, None, "host metric reader failed"
        payload = json.loads(result.stdout)
        return (
            _as_percent(payload.get("cpu_percent"), "cpu_percent"),
            _as_percent(payload.get("memory_percent"), "memory_percent"),
            None,
        )
    except Exception:
        return None, None, "host metric reader failed"


def _resolve_script(script_name: str) -> Path:
    if not isinstance(script_name, str) or not script_name.strip():
        raise ValueError("script_name is required")

    clean_name = script_name.strip()
    if clean_name != os.path.basename(clean_name) or "/" in clean_name or "\\" in clean_name:
        raise ValueError("script_name must be a simple file name from the VM script directory")

    script_dir_raw = os.environ.get(_VM_SCRIPT_DIR_ENV, "").strip()
    if not script_dir_raw:
        raise ValueError(f"{_VM_SCRIPT_DIR_ENV} is required")

    script_dir = Path(script_dir_raw).expanduser().resolve()
    if not script_dir.is_dir():
        raise ValueError(f"{_VM_SCRIPT_DIR_ENV} must point to an existing directory")

    selected = (script_dir / clean_name).resolve()
    try:
        selected.relative_to(script_dir)
    except ValueError as exc:
        raise ValueError("script_name must resolve inside the VM script directory") from exc

    if selected.suffix.lower() not in _ALLOWED_SCRIPT_EXTENSIONS:
        allowed = ", ".join(sorted(_ALLOWED_SCRIPT_EXTENSIONS))
        raise ValueError(f"script_name must end with one of: {allowed}")
    if not selected.is_file():
        raise ValueError("selected VM script was not found")
    return selected


def _build_script_args(script_path: Path) -> list[str]:
    suffix = script_path.suffix.lower()
    if suffix == ".ps1":
        return [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ]
    return ["cmd.exe", "/d", "/c", str(script_path)]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def detect_resource_pressure(
    cpu_percent: float | None = None,
    memory_percent: float | None = None,
    thresholds: dict | None = None,
) -> ResourcePressureResult:
    """Detect whether host CPU or memory pressure crosses configured thresholds.

    Args:
        cpu_percent: Optional injected CPU percentage for tests or callers.
        memory_percent: Optional injected memory percentage for tests or callers.
        thresholds: Optional keys ``cpu_percent`` and ``memory_percent``.

    Returns:
        ResourcePressureResult. This function never raises.
    """
    try:
        cpu = _as_percent(cpu_percent, "cpu_percent")
        memory = _as_percent(memory_percent, "memory_percent")
        metric_error = None

        if cpu is None or memory is None:
            host_cpu, host_memory, metric_error = _read_host_metrics()
            if cpu is None:
                cpu = host_cpu
            if memory is None:
                memory = host_memory

        if cpu is None or memory is None:
            return ResourcePressureResult(
                status="error",
                cpu_percent=cpu,
                memory_percent=memory,
                maxed_out=False,
                reasons=[],
                error=metric_error or "cpu_percent and memory_percent are required",
            )

        cpu_threshold = _threshold_value(
            thresholds,
            "cpu_percent",
            _DEFAULT_CPU_THRESHOLD,
        )
        memory_threshold = _threshold_value(
            thresholds,
            "memory_percent",
            _DEFAULT_MEMORY_THRESHOLD,
        )

        reasons: list[str] = []
        if cpu >= cpu_threshold:
            reasons.append(f"cpu_percent {cpu:.1f} >= {cpu_threshold:.1f}")
        if memory >= memory_threshold:
            reasons.append(f"memory_percent {memory:.1f} >= {memory_threshold:.1f}")

        return ResourcePressureResult(
            status="maxed_out" if reasons else "ok",
            cpu_percent=cpu,
            memory_percent=memory,
            maxed_out=bool(reasons),
            reasons=reasons,
            error=None,
        )
    except Exception as exc:
        return ResourcePressureResult(
            status="error",
            cpu_percent=None,
            memory_percent=None,
            maxed_out=False,
            reasons=[],
            error=str(exc),
        )


def boot_secondary_vm(
    script_name: str,
    allow_vm_boot: bool = False,
    dry_run: bool = True,
) -> VMBootResult:
    """Select and optionally launch an allowlisted VM boot script.

    Args:
        script_name: File name under ``JULES_VM_SCRIPT_DIR``.
        allow_vm_boot: Runtime gate required for real process launch.
        dry_run: Defaults True. When true, validates only and does not launch.

    Returns:
        VMBootResult. This function never raises.
    """
    try:
        script_path = _resolve_script(script_name)
        selected_script = str(script_path)

        if dry_run:
            return VMBootResult(
                status="dry_run",
                selected_script=selected_script,
                started=False,
                dry_run=True,
                error=None,
            )

        if not allow_vm_boot:
            return VMBootResult(
                status="blocked",
                selected_script=selected_script,
                started=False,
                dry_run=False,
                error="allow_vm_boot must be true for real VM boot",
            )

        process = subprocess.Popen(
            _build_script_args(script_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return VMBootResult(
            status="started",
            selected_script=selected_script,
            started=True,
            dry_run=False,
            pid=process.pid,
            error=None,
        )
    except Exception as exc:
        return VMBootResult(
            status="error",
            selected_script="",
            started=False,
            dry_run=dry_run,
            error=str(exc),
        )


def check_and_scale_compute(
    dry_run: bool = True,
    allow_vm_boot: bool = False,
    script_name: str = "Start-SecondaryVM.ps1",
) -> str:
    """Compatibility wrapper for the daemon loop.

    Checks local resource pressure and starts the configured secondary VM boot
    script only when pressure crosses thresholds and live execution is allowed.
    """
    pressure = detect_resource_pressure()
    memory = pressure.get("memory_percent")
    if pressure.get("status") != "maxed_out":
        if memory is None:
            return f"No scaling action needed: {pressure.get('error') or 'resource pressure unknown'}"
        return f"Memory at {float(memory):.1f}%, no action needed."

    boot = boot_secondary_vm(
        script_name=script_name,
        allow_vm_boot=allow_vm_boot,
        dry_run=dry_run,
    )
    if boot.get("status") == "started":
        return f"EXECUTED: {boot.get('selected_script')}"
    if boot.get("status") == "dry_run":
        return f"DRY_RUN: {boot.get('selected_script')}"
    return f"BLOCKED: {boot.get('error') or boot.get('status')}"
