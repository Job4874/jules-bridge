"""App launcher module for explicit, approved local workflows.

Public interface:
    launch_browser_to_url(url, allow_launch=False) -> LaunchResult
"""

from __future__ import annotations

import logging
import subprocess
from urllib.parse import urlparse

LOGGER = logging.getLogger("jules_bridge.app_launcher")

_EDGE_CMD = "msedge"


# ---------------------------------------------------------------------------
# Typed return contract
# ---------------------------------------------------------------------------

class LaunchResult(dict):
    """Result of an explicit application launch.

    Keys always present:
      status (str): success, blocked, or error
      app_name (str): logical application identifier
      started (bool): whether the process was spawned
      error (str | None): sanitized failure detail
    """


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _validate_http_url(url: str) -> str | None:
    """Return an error message when *url* is not an http(s) target."""
    trimmed = (url or "").strip()
    if not trimmed:
        return "url is required"

    parsed = urlparse(trimmed)
    if parsed.scheme not in ("http", "https"):
        return "Invalid target protocol"
    if not parsed.netloc:
        return "Invalid target URL"
    if any(char in trimmed for char in ("\r", "\n", "\0")):
        return "Invalid target URL"
    return None


def _build_edge_launch_command(url: str) -> list[str]:
    """Build a cmd.exe argv list that opens Edge without shell injection."""
    return ["cmd.exe", "/d", "/s", "/c", "start", "", _EDGE_CMD, url]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def launch_browser_to_url(url: str, allow_launch: bool = False) -> LaunchResult:
    """Explicitly launch Microsoft Edge to a verified http(s) URL."""
    if not allow_launch:
        return LaunchResult(
            status="blocked",
            app_name=_EDGE_CMD,
            started=False,
            error="Runtime authorization flag allow_launch must be True",
        )

    validation_error = _validate_http_url(url)
    if validation_error:
        return LaunchResult(
            status="error",
            app_name=_EDGE_CMD,
            started=False,
            error=validation_error,
        )

    try:
        subprocess.Popen(  # noqa: S603 — explicit argv, no shell=True
            _build_edge_launch_command(url.strip()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        LOGGER.error("Failed to launch browser: %s", exc)
        return LaunchResult(
            status="error",
            app_name=_EDGE_CMD,
            started=False,
            error="Internal process launch failure",
        )

    return LaunchResult(
        status="success",
        app_name=_EDGE_CMD,
        started=True,
        error=None,
    )
