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
    spawn,
    available_shells,
)
from .ui_automation import (
    ScreenshotResult,
    ClickResult,
    SecretResult,
    UIDetectionResult,
    screenshot,
    click,
    type_text,
    get_secret,
    detect_ui_state,
)
from .inbox_service import InboxMessage, inbox_read, inbox_write
from .mesh_registry import get_mesh_status, register_local_node
from .human_mimic_driver import (
    HumanMimicResult,
    drive_quantower_login,
)
from .vm_manager import (
    ResourcePressureResult,
    VMBootResult,
    detect_resource_pressure,
    boot_secondary_vm,
    check_and_scale_compute,
)
from .windows_secret_provider import (
    WindowsSecretProvider,
    build_windows_secret_provider,
)
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
from .jules_api import (
    JulesApiResult,
    is_rest_api_enabled,
    is_rest_api_requested,
    jules_api_preflight as rest_api_preflight,
    list_sources as jules_api_list_sources,
    list_sessions as jules_api_list_sessions,
    create_session as jules_api_create_session,
    get_session as jules_api_get_session,
    list_activities as jules_api_list_activities,
    send_message as jules_api_send_message,
    approve_plan as jules_api_approve_plan,
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
    MEMORY_DOMAINS,
    LogPattern,
    TestEvidence,
    EvidenceStaleness,
    DoomLoop,
    RetrospectiveReport,
    analyze_session,
    record_test_evidence,
    load_test_evidence,
    load_memory,
    prune_memory,
    check_test_evidence_staleness,
    is_evidence_hard_gate_enabled,
    validate_memory_domain,
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
from .repo_context_guard import (
    RepoContextGuardResult,
    build_repo_context_guard,
)
from .app_launcher import LaunchResult, launch_browser_to_url
from .chat_service import ChatHealthResult, ChatResult, test_chat_providers, chat

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
    "spawn",
    "available_shells",
    # ui_automation
    "ScreenshotResult",
    "ClickResult",
    "SecretResult",
    "UIDetectionResult",
    "screenshot",
    "click",
    "type_text",
    "get_secret",
    "detect_ui_state",
    # human_mimic_driver
    "HumanMimicResult",
    "drive_quantower_login",
    # vm_manager
    "ResourcePressureResult",
    "VMBootResult",
    "detect_resource_pressure",
    "boot_secondary_vm",
    "check_and_scale_compute",
    # windows_secret_provider
    "WindowsSecretProvider",
    "build_windows_secret_provider",
    # inbox_service
    "InboxMessage",
    "inbox_read",
    "inbox_write",
    # mesh_registry
    "get_mesh_status",
    "register_local_node",
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
    # jules_api
    "JulesApiResult",
    "is_rest_api_enabled",
    "is_rest_api_requested",
    "rest_api_preflight",
    "jules_api_list_sources",
    "jules_api_list_sessions",
    "jules_api_create_session",
    "jules_api_get_session",
    "jules_api_list_activities",
    "jules_api_send_message",
    "jules_api_approve_plan",
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
    "MEMORY_DOMAINS",
    "LogPattern",
    "TestEvidence",
    "EvidenceStaleness",
    "DoomLoop",
    "RetrospectiveReport",
    "analyze_session",
    "record_test_evidence",
    "load_test_evidence",
    "load_memory",
    "prune_memory",
    "check_test_evidence_staleness",
    "is_evidence_hard_gate_enabled",
    "validate_memory_domain",
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
    # repo_context_guard
    "RepoContextGuardResult",
    "build_repo_context_guard",
    # app_launcher
    "LaunchResult",
    "launch_browser_to_url",
    # chat_service
    "ChatHealthResult",
    "ChatResult",
    "test_chat_providers",
    "chat",
]
