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
from .ui_automation import (
    ScreenshotResult,
    ClickResult,
    screenshot,
    click,
    type_text,
    SecretAccessError,
    get_secret,
    detect_ui_state,
)
from .browser_agent import init_browser, verify_quantower_login
from .vm_manager import VMBootResult, VMBootError, get_local_memory_percent, boot_secondary_vm
from .router import RouteResult, dispatch
from .inbox_service import InboxMessage, inbox_read, inbox_write
from .jules_orchestrator import (
    JulesTask,
    JulesDispatchResult,
    JulesLaunchResult,
    JulesRemoteResult,
    JulesPreflightResult,
    JulesPullResult,
    JulesCotResult,
    JulesCycleResult,
    JulesWatchResult,
    JulesFleetResult,
    JulesFleetWatchResult,
    parse_task_dump,
    build_dispatch,
    launch_packets,
    list_remote_sessions,
    jules_preflight,
    pull_remote_session,
    build_cot_ledger,
    run_jules_cycle,
    run_jules_watch,
    run_jules_fleet,
    run_jules_fleet_watch,
)
from .oracle_session import (
    OracleStatus,
    BuildDeployResult,
    HandoverIndex,
    HostPathIndex,
    ReplayRestartResult,
    oracle_status,
    oracle_build_deploy,
    codex_handover_index,
    hard_index_host_paths,
    oracle_restart_replay,
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
from .context_orchestrator import (
    ContextSource,
    ContextCapsule,
    ContextSubagent,
    ContextSubagentPlan,
    build_context_subagents,
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
    "SecretAccessError",
    "get_secret",
    "detect_ui_state",
    # browser_agent
    "init_browser",
    "verify_quantower_login",
    # vm_manager
    "VMBootResult",
    "VMBootError",
    "get_local_memory_percent",
    "boot_secondary_vm",
    # router
    "RouteResult",
    "dispatch",
    # inbox_service
    "InboxMessage",
    "inbox_read",
    "inbox_write",
    # jules_orchestrator
    "JulesTask",
    "JulesDispatchResult",
    "JulesLaunchResult",
    "JulesRemoteResult",
    "JulesPreflightResult",
    "JulesPullResult",
    "JulesCotResult",
    "JulesCycleResult",
    "JulesWatchResult",
    "JulesFleetResult",
    "JulesFleetWatchResult",
    "parse_task_dump",
    "build_dispatch",
    "launch_packets",
    "list_remote_sessions",
    "jules_preflight",
    "pull_remote_session",
    "build_cot_ledger",
    "run_jules_cycle",
    "run_jules_watch",
    "run_jules_fleet",
    "run_jules_fleet_watch",
    # oracle_session
    "OracleStatus",
    "BuildDeployResult",
    "HandoverIndex",
    "HostPathIndex",
    "ReplayRestartResult",
    "oracle_status",
    "oracle_build_deploy",
    "codex_handover_index",
    "hard_index_host_paths",
    "oracle_restart_replay",
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
    # context_orchestrator
    "ContextSource",
    "ContextCapsule",
    "ContextSubagent",
    "ContextSubagentPlan",
    "build_context_subagents",
]
