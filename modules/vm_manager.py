"""VM manager deep module — compute scaling and secondary VM boot.

Simple typed interface hiding psutil probing, Azure CLI invocation,
and the dry-run / allow_vm_boot guard semantics.
"""

from __future__ import annotations

import subprocess

# Lazy import guard — psutil is only imported at call time so test
# environments can mock it cleanly.
def _psutil():
    import psutil as _ps  # noqa: PLC0415
    return _ps


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class VMBootResult(dict):
    """Result of a secondary VM boot attempt.

    Keys always present:
      status (str): human-readable outcome
    Optional keys:
      memory_percent (float): observed local memory pressure
      command (list[str]): Azure CLI command that was executed or simulated
      error (str): failure reason
    """


class VMBootError(Exception):
    """Raised when a live VM boot is attempted without allow_vm_boot=True."""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_local_memory_percent() -> float:
    """Return current local memory usage as a percentage."""
    return float(_psutil().virtual_memory().percent)


def boot_secondary_vm(
    dry_run: bool = True,
    allow_vm_boot: bool = False,
    vm_name: str = "OracleV5",
    resource_group: str = "QuantowerGroup",
) -> VMBootResult:
    """Boot the secondary Azure VM if local memory pressure exceeds 85%.

    Args:
        dry_run: If True, simulate the action without invoking Azure CLI.
        allow_vm_boot: Runtime flag that must be True for any live VM boot.
        vm_name: Name of the Azure VM to start.
        resource_group: Azure resource group containing the VM.

    Returns:
        VMBootResult describing the outcome.

    Raises:
        VMBootError: if live boot is requested but allow_vm_boot is False.
    """
    memory_percent = get_local_memory_percent()
    command = [
        "az",
        "vm",
        "start",
        "--name",
        vm_name,
        "--resource-group",
        resource_group,
    ]

    if memory_percent <= 85.0:
        return VMBootResult(
            status="no_action",
            memory_percent=memory_percent,
            message=f"Memory at {memory_percent}%, no action needed.",
        )

    if dry_run:
        return VMBootResult(
            status="dry_run",
            memory_percent=memory_percent,
            command=command,
            message=f"DRY_RUN: Would execute {' '.join(command)}",
        )

    if not allow_vm_boot:
        raise VMBootError("VM Boot attempted but allow_vm_boot=False")

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return VMBootResult(
            status="executed",
            memory_percent=memory_percent,
            command=command,
            message=f"EXECUTED: {' '.join(command)}",
        )
    except subprocess.CalledProcessError as exc:
        return VMBootResult(
            status="failed",
            memory_percent=memory_percent,
            command=command,
            error=str(exc),
            stderr=exc.stderr,
        )
    except FileNotFoundError as exc:
        return VMBootResult(
            status="failed",
            memory_percent=memory_percent,
            command=command,
            error=f"Azure CLI not found: {exc}",
        )
