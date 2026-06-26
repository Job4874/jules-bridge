"""Jules Bridge modules package — deep module interfaces for the bridge API.

Each sub-module hides its implementation complexity behind a typed interface.
bridge.py imports from here and does nothing but HTTP routing.
"""

from .fs_service import FSResult, ListEntry, read, write, tail, grep, list_dir
from .shell_executor import (
    ShellResult,
    ShellNotAvailableError,
    UnsupportedShellError,
    execute,
    available_shells,
)
from .ui_automation import ScreenshotResult, ClickResult, screenshot, click, type_text
from .inbox_service import InboxMessage, inbox_read, inbox_write
from .oracle_session import (
    OracleStatus,
    BuildDeployResult,
    HandoverIndex,
    oracle_status,
    oracle_build_deploy,
    codex_handover_index,
)

__all__ = [
    # fs_service
    "FSResult",
    "ListEntry",
    "read",
    "write",
    "tail",
    "grep",
    "list_dir",
    # shell_executor
    "ShellResult",
    "ShellNotAvailableError",
    "UnsupportedShellError",
    "execute",
    "available_shells",
    # ui_automation
    "ScreenshotResult",
    "ClickResult",
    "screenshot",
    "click",
    "type_text",
    # inbox_service
    "InboxMessage",
    "inbox_read",
    "inbox_write",
    # oracle_session
    "OracleStatus",
    "BuildDeployResult",
    "HandoverIndex",
    "oracle_status",
    "oracle_build_deploy",
    "codex_handover_index",
]
