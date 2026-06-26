"""Task router deep module — classify task packets and route to the right worker.

Simple typed interface hiding classification rules.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class RouteResult(dict):
    """Result of a task routing decision.

    Keys always present:
      target (str): worker or destination for the task
      task_type (str): normalized task type
    """


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def dispatch(task_packet: dict) -> RouteResult:
    """Classify a task packet and return its routing target.

    Args:
        task_packet: dict containing at least a "type" key.

    Returns:
        RouteResult with target and task_type.
    """
    task_type = str(task_packet.get("type", "")).strip()

    if task_type == "Code/Dev":
        target = "Cursor/Jules"
    elif task_type == "Compute/Scale":
        target = "Azure/Local VM"
    elif task_type == "Routine/UI":
        target = "human_mimic_driver"
    else:
        target = "UNROUTED"

    return RouteResult(target=target, task_type=task_type or "UNROUTED")
