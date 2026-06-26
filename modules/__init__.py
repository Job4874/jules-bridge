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
from .jules_orchestrator import (
    JulesTask,
    JulesDispatchResult,
    JulesLaunchResult,
    JulesRemoteResult,
    parse_task_dump,
    build_dispatch,
    launch_packets,
    list_remote_sessions,
)
from .oracle_session import (
    OracleStatus,
    BuildDeployResult,
    HandoverIndex,
    oracle_status,
    oracle_build_deploy,
    codex_handover_index,
)
from .reasoning_module import (
    HLevelPlan,
    LLevelAction,
    HaltDecision,
    ReasoningTrace,
    reason,
    plan_only,
    execute_step,
)
from .retrospective_module import (
    LogPattern,
    TestEvidence,
    DoomLoop,
    RetrospectiveReport,
    analyze_session,
    record_test_evidence,
    load_test_evidence,
    load_memory,
    prune_memory,
)
from .akc_module import (
    AKCContext,
    AKCCheckpoint,
    AKCReadiness,
    build_akc_context,
    load_akc_checkpoint,
    check_akc_readiness,
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
    # jules_orchestrator
    "JulesTask",
    "JulesDispatchResult",
    "JulesLaunchResult",
    "JulesRemoteResult",
    "parse_task_dump",
    "build_dispatch",
    "launch_packets",
    "list_remote_sessions",
    # oracle_session
    "OracleStatus",
    "BuildDeployResult",
    "HandoverIndex",
    "oracle_status",
    "oracle_build_deploy",
    "codex_handover_index",
    # reasoning_module
    "HLevelPlan",
    "LLevelAction",
    "HaltDecision",
    "ReasoningTrace",
    "reason",
    "plan_only",
    "execute_step",
    # retrospective_module
    "LogPattern",
    "TestEvidence",
    "DoomLoop",
    "RetrospectiveReport",
    "analyze_session",
    "record_test_evidence",
    "load_test_evidence",
    "load_memory",
    "prune_memory",
    # akc_module
    "AKCContext",
    "AKCCheckpoint",
    "AKCReadiness",
    "build_akc_context",
    "load_akc_checkpoint",
    "check_akc_readiness",
]
