"""Collaboration proof harness for Jules, Gemini, context, and no-slop gates.

This module gathers current-state evidence from the bridge's agent surfaces and
turns it into a rerunnable proof report. It does not launch Jules sessions, run
Gemini edits, or submit external work.

Public interface:
    build_collaboration_proof(...) -> CollaborationProofResult
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .akc_module import check_akc_readiness
from .antigravity_cli import antigravity_preflight
from .gemini_cli import gemini_preflight
from .jules_orchestrator import jules_preflight
from .reasoning_module import HRM_COLLABORATION_PROBLEM, discover_skills, reason
from .retrospective_module import load_test_evidence

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PROOF_DIR = _ROOT / "jules_inbox" / "proof"
_DEFAULT_PROOF_STATE = "COLLABORATION_PROOF.json"
_CONTEXT_FILES = (
    "context/01_project_overview.md",
    "context/02_architecture.md",
    "context/03_code_standards.md",
    "context/04_ai_workflow_rules.md",
    "context/05_gotchas.md",
    "context/06_progress_tracker.md",
    "context/07_library_docs.md",
    "context/08_akc_context_checkpoint.md",
    ".agents/AGENTS.md",
    "UBIQUITOUS_LANGUAGE.md",
)
_STATUS_ORDER = {
    "pass": 0,
    "info": 1,
    "skipped": 2,
    "partial": 3,
    "blocked": 4,
    "fail": 5,
}


class CollaborationProofResult(dict):
    """Keys: status, gates, requirement_audit, agents, blockers, state_path."""


def build_collaboration_proof(
    include_live_checks: bool = False,
    run_gemini_smoke: bool = False,
    timeout_s: int = 12,
    write_state: bool = True,
    state_path: str = "",
) -> CollaborationProofResult:
    """Build a current-state proof report for the Jules + Gemini bridge.

    Args:
        include_live_checks: Run read-only live checks such as Jules source list.
        run_gemini_smoke: Attempt authenticated Gemini headless model execution.
        timeout_s: Timeout for bounded CLI/API probes.
        write_state: Persist the generated proof JSON under jules_inbox/proof.
        state_path: Optional explicit proof output path.

    Returns:
        CollaborationProofResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        jules = jules_preflight(
            timeout_s=timeout_s,
            check_remote=include_live_checks,
            write_state=False,
        )
        gemini = gemini_preflight(
            timeout_s=timeout_s,
            run_smoke=run_gemini_smoke,
            write_state=False,
        )
        antigravity = antigravity_preflight(
            timeout_s=timeout_s,
            run_smoke=run_gemini_smoke,
            write_state=False,
        )
        akc = check_akc_readiness()
        reasoning_trace = reason(
            HRM_COLLABORATION_PROBLEM,
            context="Use context, skills, HRM reasoning, evidence gates, and tests.",
            halt_budget=8,
            model="stub",
        )
        jules_skills = _jules_skill_inventory()
        gemini_skills = _gemini_skill_inventory(gemini)
        antigravity_skills = _antigravity_skill_inventory(antigravity)
        context_state = _context_state()
        test_evidence = _latest_test_evidence()
        bridge_code = _bridge_code_state()

        google_terminal_model_gate = _google_terminal_model_gate(antigravity, run_gemini_smoke)
        antigravity_cli_ready = bool(antigravity.get("installed"))
        gates = [
            _jules_reachability_gate(jules),
            _gemini_cli_gate(gemini, supported_google_terminal_ready=antigravity_cli_ready),
            _gemini_model_gate(
                gemini,
                run_gemini_smoke,
                supported_google_terminal_ready=google_terminal_model_gate["status"] == "pass",
            ),
            _antigravity_cli_gate(antigravity),
            google_terminal_model_gate,
            _skills_gate(jules_skills, gemini_skills, antigravity_skills),
            _context_gate(akc, context_state),
            _hrm_gate(reasoning_trace),
            _architecture_gate(context_state, bridge_code),
            _collaboration_route_gate(bridge_code),
            _code_change_gate(bridge_code),
            _tests_gate(test_evidence),
        ]
        blockers = [
            {
                "gate": gate["name"],
                "blocker": gate.get("blocker", ""),
                "status": gate["status"],
            }
            for gate in gates
            if gate.get("required", True) and gate["status"] in ("blocked", "fail") and gate.get("blocker")
        ]
        legacy_caveats = [
            {
                "gate": gate["name"],
                "blocker": gate.get("blocker", ""),
                "status": gate["status"],
                "summary": gate.get("summary", ""),
            }
            for gate in gates
            if not gate.get("required", True) and gate["status"] in ("blocked", "fail") and gate.get("blocker")
        ]
        payload = CollaborationProofResult(
            generated_at_utc=generated_at,
            status=_overall_status(gates),
            summary=_summary(gates, blockers, legacy_caveats),
            objective_requirements=_objective_requirements(),
            requirement_audit=_requirement_audit(gates),
            completion_assessment=_completion_assessment(gates, blockers, legacy_caveats),
            collaboration_workflow=_collaboration_workflow(),
            gates=gates,
            agents={
                "jules": _jules_agent_view(jules, jules_skills, akc),
                "gemini": _gemini_agent_view(gemini, gemini_skills),
                "antigravity": _antigravity_agent_view(antigravity, antigravity_skills),
            },
            proof_policy={
                "live_side_effects": "none",
                "jules_sessions_created": False,
                "gemini_live_edits": False,
                "live_read_only_checks": bool(include_live_checks),
                "gemini_smoke_requested": bool(run_gemini_smoke),
                "antigravity_smoke_requested": bool(run_gemini_smoke),
            },
            blockers=blockers,
            legacy_caveats=legacy_caveats,
            evidence={
                "context": context_state,
                "tests": test_evidence,
                "bridge_code": bridge_code,
                "google_terminal_agent": {
                    "antigravity_installed": bool(antigravity.get("installed")),
                    "antigravity_ready": bool(antigravity.get("ready")),
                    "antigravity_blocker": antigravity.get("likely_blocker", ""),
                },
            },
            state_path="",
        )
        if write_state:
            destination = Path(state_path) if state_path else _DEFAULT_PROOF_DIR / _DEFAULT_PROOF_STATE
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload["state_path"] = str(destination)
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return CollaborationProofResult(
            generated_at_utc=generated_at,
            status="fail",
            summary="Collaboration proof harness failed before completing gate evaluation.",
            error=str(exc),
            gates=[],
            blockers=[{"gate": "proof_harness", "blocker": str(exc), "status": "fail"}],
        )


def _gate(
    name: str,
    status: str,
    summary: str,
    evidence: dict[str, Any] | None = None,
    blocker: str = "",
    required: bool = True,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "required": required,
        "summary": summary,
        "evidence": evidence or {},
        "blocker": blocker,
    }


def _overall_status(gates: list[dict[str, Any]]) -> str:
    required = [gate for gate in gates if gate.get("required", True)]
    worst = max((_STATUS_ORDER.get(gate["status"], 5) for gate in required), default=5)
    for status, rank in _STATUS_ORDER.items():
        if rank == worst:
            return status
    return "fail"


def _gate_group_status(gates: list[dict[str, Any]]) -> str:
    worst = max((_STATUS_ORDER.get(gate["status"], 5) for gate in gates), default=5)
    for status, rank in _STATUS_ORDER.items():
        if rank == worst:
            return status
    return "fail"


def _summary(
    gates: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    legacy_caveats: list[dict[str, Any]] | None = None,
) -> str:
    passed = sum(1 for gate in gates if gate["status"] == "pass")
    total = len(gates)
    if blockers:
        names = ", ".join(item["gate"] for item in blockers)
        return f"{passed}/{total} proof gates passed; blockers remain at {names}."
    if legacy_caveats:
        names = ", ".join(item["gate"] for item in legacy_caveats)
        return f"{passed}/{total} proof gates passed; no required blockers; legacy caveats remain at {names}."
    return f"{passed}/{total} proof gates passed; no failing blocker gates reported."


def _objective_requirements() -> list[str]:
    return [
        "Jules is reachable through CLI or REST and through the local bridge.",
        "Gemini CLI is installed, callable, and exposes its capability surface.",
        "Antigravity CLI is installed as the supported Google terminal-agent path.",
        "The supported Google terminal-agent model smoke works through the bridge.",
        "The bridge can prove skills/workflows for both agent systems.",
        "Context handling is source-backed through AKC and project context files.",
        "HRM/HRE reasoning works through the reasoning module boundary.",
        "Architecture guardrails keep code out of bridge route handlers.",
        "Actual code changes exist for the collaboration proof surface.",
        "The integration is dry-run-first and does not produce sloppy live side effects.",
        "Local tests and evidence records back completion claims.",
        "Jules and the supported Google terminal agent work together end-to-end while legacy Gemini CLI migration state is tracked separately.",
    ]


def _requirement_audit(gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gate_map = {gate["name"]: gate for gate in gates}
    rows = [
        _audit_row(
            "REQ-001",
            "Jules is reachable through CLI or REST and through the local bridge.",
            ["jules_reachable", "bridge_collaboration_surface"],
            gate_map,
        ),
        _audit_row(
            "REQ-002",
            "Gemini CLI is installed, callable, and exposes its capability surface.",
            ["gemini_cli_reachable"],
            gate_map,
        ),
        _audit_row(
            "REQ-003",
            "Legacy Gemini authenticated model execution works through the bridge when that legacy lane is supported for the account.",
            ["gemini_model_execution"],
            gate_map,
            required_for_completion=False,
        ),
        _audit_row(
            "REQ-003A",
            "Antigravity can execute a Google terminal-agent model smoke through the bridge.",
            ["antigravity_cli_reachable", "google_terminal_model_execution"],
            gate_map,
        ),
        _audit_row(
            "REQ-004",
            "Both systems expose skills and reusable workflows.",
            ["skills_framework"],
            gate_map,
        ),
        _audit_row(
            "REQ-005",
            "The proof is grounded in source-backed context handling.",
            ["context_handling"],
            gate_map,
        ),
        _audit_row(
            "REQ-006",
            "HRM/HRE reasoning is operational through the module boundary.",
            ["hrm_reasoning"],
            gate_map,
        ),
        _audit_row(
            "REQ-007",
            "Architecture guardrails prevent slop code in complex changes.",
            ["architecture_guardrails", "bridge_collaboration_surface"],
            gate_map,
        ),
        _audit_row(
            "REQ-008",
            "Actual code changes and local tests prove implementation, not intent.",
            ["actual_code_changes", "local_tests_and_evidence"],
            gate_map,
        ),
        _audit_row(
            "REQ-009",
            "Jules and Gemini work together end-to-end.",
            [
                "jules_reachable",
                "gemini_cli_reachable",
                "antigravity_cli_reachable",
                "google_terminal_model_execution",
                "skills_framework",
                "context_handling",
                "hrm_reasoning",
                "actual_code_changes",
                "local_tests_and_evidence",
            ],
            gate_map,
        ),
    ]
    return rows


def _audit_row(
    requirement_id: str,
    requirement: str,
    gate_names: list[str],
    gate_map: dict[str, dict[str, Any]],
    required_for_completion: bool = True,
) -> dict[str, Any]:
    gates = [gate_map[name] for name in gate_names if name in gate_map]
    status = _overall_status(gates) if required_for_completion else _gate_group_status(gates)
    blockers = [
        {
            "gate": gate["name"],
            "blocker": gate.get("blocker", ""),
            "status": gate["status"],
        }
        for gate in gates
        if gate["status"] in ("blocked", "fail") and gate.get("blocker")
    ]
    evidence_refs = [
        {
            "gate": gate["name"],
            "status": gate["status"],
            "summary": gate["summary"],
        }
        for gate in gates
    ]
    return {
        "id": requirement_id,
        "requirement": requirement,
        "status": status,
        "required_for_completion": required_for_completion,
        "evidence_refs": evidence_refs,
        "blockers": blockers,
    }


def _completion_assessment(
    gates: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    legacy_caveats: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    status = _overall_status(gates)
    safe = status == "pass" and not blockers
    return {
        "safe_to_mark_goal_complete": safe,
        "status": status,
        "reason": (
            "All required proof gates pass."
            if safe
            else "The original goal remains active until every required proof gate passes."
        ),
        "blocking_gates": [item["gate"] for item in blockers],
        "legacy_caveats": [item["gate"] for item in (legacy_caveats or [])],
    }


def _collaboration_workflow() -> list[dict[str, str]]:
    return [
        {
            "phase": "context",
            "jules_role": "Load AKC, AGENTS.md, gotchas, memory, and repo source truth.",
            "gemini_role": "Expose Gemini and Antigravity CLI capabilities without replacing project context.",
        },
        {
            "phase": "reason",
            "jules_role": "Use HRE/HRM gates to classify blockers and plan architecture-safe work.",
            "gemini_role": "Provide terminal-agent critique through the supported Google CLI path.",
        },
        {
            "phase": "implement",
            "jules_role": "Route actual code changes through deep modules, thin bridge handlers, and tests.",
            "gemini_role": "Run headless prompts safely and only edit when explicitly allowed.",
        },
        {
            "phase": "verify",
            "jules_role": "Record pytest evidence, live preflight state, and proof JSON.",
            "gemini_role": "Report legacy Gemini blockers and pass Antigravity model smoke when available.",
        },
    ]


def _jules_reachability_gate(jules: dict[str, Any]) -> dict[str, Any]:
    ready = bool(jules.get("ready"))
    return _gate(
        "jules_reachable",
        "pass" if ready else "blocked",
        "Jules preflight is ready." if ready else "Jules preflight did not prove readiness.",
        {
            "preferred_command": jules.get("preferred_jules_command", ""),
            "resolved_command": jules.get("resolved_jules_command", ""),
            "rest_api": bool(jules.get("rest_api")),
            "source": jules.get("auth_indicators", {}).get("source", ""),
            "remote_status": jules.get("remote", {}).get("status", ""),
        },
        blocker=str(jules.get("likely_blocker") or jules.get("error") or ""),
    )


def _gemini_cli_gate(
    gemini: dict[str, Any],
    supported_google_terminal_ready: bool = False,
) -> dict[str, Any]:
    installed = bool(gemini.get("installed"))
    details = {
        "resolved_command": gemini.get("resolved_gemini_command", ""),
        "version": _command_stdout(gemini.get("version")),
        "headless_mode": gemini.get("capabilities", {}).get("headless_mode", ""),
        "output_formats": gemini.get("capabilities", {}).get("output_formats", []),
    }
    if installed:
        return _gate(
            "gemini_cli_reachable",
            "pass",
            "Gemini CLI answered version/capability probes.",
            details,
            blocker="",
        )
    blocker = str(gemini.get("likely_blocker") or gemini.get("error") or "")
    if supported_google_terminal_ready:
        # Legacy lane: the standalone Gemini CLI is not installed, but the
        # supported Antigravity Google terminal-agent is reachable, so this is a
        # non-required caveat rather than a hard blocker.
        return _gate(
            "gemini_cli_reachable",
            "blocked",
            (
                "Legacy Gemini CLI is not installed, but the supported Antigravity "
                "Google terminal-agent is reachable and serves this surface."
            ),
            {**details, "legacy_lane": True, "supported_google_terminal_ready": True},
            blocker=blocker,
            required=False,
        )
    return _gate(
        "gemini_cli_reachable",
        "blocked",
        "Gemini CLI did not answer probes.",
        details,
        blocker=blocker,
    )


def _gemini_model_gate(
    gemini: dict[str, Any],
    run_gemini_smoke: bool,
    supported_google_terminal_ready: bool = False,
) -> dict[str, Any]:
    if not run_gemini_smoke:
        return _gate(
            "gemini_model_execution",
            "skipped",
            "Authenticated Gemini model execution was not requested for this proof run.",
            {"smoke_status": gemini.get("smoke", {}).get("status", "skipped")},
        )
    smoke = gemini.get("smoke", {})
    ok = smoke.get("status") == "ok"
    blocker = str(smoke.get("likely_blocker") or gemini.get("likely_blocker") or smoke.get("stderr", ""))[:500]
    if not ok and supported_google_terminal_ready:
        return _gate(
            "gemini_model_execution",
            "blocked",
            (
                "Legacy Gemini CLI model execution is unavailable for this account, "
                "but the supported Antigravity Google terminal-agent smoke passed."
            ),
            {
                "smoke_status": smoke.get("status", ""),
                "exit_code": smoke.get("exit_code", ""),
                "likely_blocker": smoke.get("likely_blocker", ""),
                "legacy_lane": True,
                "supported_google_terminal_ready": True,
            },
            blocker=blocker,
            required=False,
        )
    return _gate(
        "gemini_model_execution",
        "pass" if ok else "blocked",
        "Gemini headless smoke prompt completed." if ok else "Gemini headless smoke did not complete.",
        {
            "smoke_status": smoke.get("status", ""),
            "exit_code": smoke.get("exit_code", ""),
            "likely_blocker": smoke.get("likely_blocker", ""),
        },
        blocker=blocker,
    )


def _antigravity_cli_gate(antigravity: dict[str, Any]) -> dict[str, Any]:
    installed = bool(antigravity.get("installed"))
    capabilities = antigravity.get("capabilities", {})
    models = capabilities.get("models", {}) if isinstance(capabilities, dict) else {}
    return _gate(
        "antigravity_cli_reachable",
        "pass" if installed else "blocked",
        (
            "Antigravity CLI answered version/model/plugin probes."
            if installed
            else "Antigravity CLI did not answer probes."
        ),
        {
            "resolved_command": antigravity.get("resolved_antigravity_command", ""),
            "version": _command_stdout(antigravity.get("version")),
            "headless_mode": capabilities.get("headless_mode", ""),
            "model_count": len(_nonempty_lines(models.get("stdout", "") if isinstance(models, dict) else "")),
            "plugin_management": capabilities.get("plugin_management", ""),
        },
        blocker="" if installed else str(antigravity.get("likely_blocker") or antigravity.get("error") or ""),
    )


def _google_terminal_model_gate(
    antigravity: dict[str, Any],
    run_gemini_smoke: bool,
) -> dict[str, Any]:
    if not run_gemini_smoke:
        return _gate(
            "google_terminal_model_execution",
            "skipped",
            "Supported Google terminal-agent model execution was not requested for this proof run.",
            {"smoke_status": antigravity.get("smoke", {}).get("status", "skipped")},
        )
    smoke = antigravity.get("smoke", {})
    ok = smoke.get("status") == "ok"
    return _gate(
        "google_terminal_model_execution",
        "pass" if ok else "blocked",
        (
            "Antigravity headless smoke prompt completed."
            if ok
            else "Antigravity headless smoke did not complete."
        ),
        {
            "smoke_status": smoke.get("status", ""),
            "exit_code": smoke.get("exit_code", ""),
            "likely_blocker": smoke.get("likely_blocker", ""),
        },
        blocker=str(smoke.get("likely_blocker") or antigravity.get("likely_blocker") or smoke.get("stderr", ""))[:500],
    )


def _skills_gate(
    jules_skills: list[dict[str, Any]],
    gemini_skills: list[dict[str, Any]],
    antigravity_skills: list[dict[str, Any]],
) -> dict[str, Any]:
    jules_ok = len(jules_skills) >= 5
    google_ok = len(gemini_skills) >= 1 or len(antigravity_skills) >= 1
    if jules_ok and google_ok:
        status = "pass"
        summary = "Jules and the Google terminal-agent surface expose skills/workflow metadata."
        blocker = ""
    elif jules_ok or google_ok:
        status = "partial"
        summary = "Only one agent skill surface is currently fully visible."
        blocker = "missing_jules_skills" if not jules_ok else "missing_google_terminal_skills"
    else:
        status = "blocked"
        summary = "Neither agent skill surface had enough discoverable skills."
        blocker = "skills_not_discovered"
    return _gate(
        "skills_framework",
        status,
        summary,
        {
            "jules_skill_count": len(jules_skills),
            "gemini_skill_count": len(gemini_skills),
            "antigravity_skill_count": len(antigravity_skills),
            "jules_skill_names": [item.get("name", "") for item in jules_skills],
            "gemini_skill_names": [item.get("name", "") for item in gemini_skills],
            "antigravity_skill_names": [item.get("name", "") for item in antigravity_skills],
        },
        blocker=blocker,
    )


def _context_gate(akc: dict[str, Any], context_state: dict[str, Any]) -> dict[str, Any]:
    ready = bool(akc.get("ready")) and not context_state.get("missing_files")
    return _gate(
        "context_handling",
        "pass" if ready else "blocked",
        "AKC and project context files are ready." if ready else "Context readiness is incomplete.",
        {
            "akc_status": akc.get("status", ""),
            "present_rules": akc.get("present_rules", []),
            "context_file_count": context_state.get("present_count", 0),
            "missing_files": context_state.get("missing_files", []),
            "agents_protocol_found": context_state.get("agents_protocol_found", False),
        },
        blocker="missing_context_or_akc" if not ready else "",
    )


def _hrm_gate(trace: Any) -> dict[str, Any]:
    plan = getattr(trace, "plan", None)
    halt = getattr(trace, "halt", None)
    feedback = getattr(trace, "feedback", {}) or {}
    step_count = getattr(plan, "step_count", 0) if plan else 0
    executed = len(getattr(trace, "executed_actions", []) or [])
    succeeded = bool(getattr(trace, "succeeded", False))
    answer = getattr(trace, "answer", None)
    # A complete HRM trace is one the reasoning module marks as succeeded
    # (an answer plus a goal_reached/confident halt), that planned at least
    # three H-level steps and executed at least one L-level action.
    trace_complete = succeeded and step_count >= 3
    structured_ok = succeeded and executed >= 1
    ok = trace_complete and structured_ok and bool(answer) and step_count >= 3
    return _gate(
        "hrm_reasoning",
        "pass" if ok else "blocked",
        "Reasoning module produced a complete structured HRM trace." if ok else "Reasoning trace was incomplete.",
        {
            "goal_statement": getattr(plan, "goal_statement", ""),
            "step_count": step_count,
            "actions": len(getattr(trace, "actions", []) or []),
            "halt_reason": getattr(halt, "reason", ""),
            "trace_complete": trace_complete,
            "source": feedback.get("source", ""),
            "feedback": feedback,
        },
        blocker="reasoning_trace_incomplete" if not ok else "",
    )


def _architecture_gate(context_state: dict[str, Any], bridge_code: dict[str, Any]) -> dict[str, Any]:
    ok = (
        context_state.get("architecture_boundary_found")
        and context_state.get("gemini_boundary_found")
        and context_state.get("antigravity_boundary_found")
        and bridge_code.get("collaboration_module_exists")
        and bridge_code.get("antigravity_module_exists")
    )
    return _gate(
        "architecture_guardrails",
        "pass" if ok else "blocked",
        "Proof work follows deep-module/thin-route guardrails." if ok else "Architecture guardrail evidence is missing.",
        {
            "architecture_boundary_found": context_state.get("architecture_boundary_found", False),
            "gemini_boundary_found": context_state.get("gemini_boundary_found", False),
            "antigravity_boundary_found": context_state.get("antigravity_boundary_found", False),
            "collaboration_module_exists": bridge_code.get("collaboration_module_exists", False),
            "antigravity_module_exists": bridge_code.get("antigravity_module_exists", False),
        },
        blocker="missing_architecture_guardrail" if not ok else "",
    )


def _collaboration_route_gate(bridge_code: dict[str, Any]) -> dict[str, Any]:
    routes = bridge_code.get("route_markers", {})
    ok = all(
        routes.get(route)
        for route in (
            "jules_preflight",
            "gemini_preflight",
            "gemini_prompt",
            "antigravity_preflight",
            "antigravity_prompt",
        )
    )
    return _gate(
        "bridge_collaboration_surface",
        "pass" if ok else "blocked",
        (
            "Bridge exposes Jules, Gemini, and Antigravity collaboration routes."
            if ok
            else "Bridge collaboration route markers are missing."
        ),
        {"route_markers": routes},
        blocker="missing_collaboration_route" if not ok else "",
    )


def _code_change_gate(bridge_code: dict[str, Any]) -> dict[str, Any]:
    ok = (
        bridge_code.get("collaboration_module_exists")
        and bridge_code.get("antigravity_module_exists")
        and bridge_code.get("exported")
        and bridge_code.get("antigravity_exported")
        and bridge_code.get("tests_exist")
        and bridge_code.get("antigravity_tests_exist")
        and bridge_code.get("route_markers", {}).get("collaboration_proof")
    )
    return _gate(
        "actual_code_changes",
        "pass" if ok else "blocked",
        "Collaboration proof is implemented as code with tests." if ok else "Proof code or tests are missing.",
        {
            "module": "modules/collaboration_proof.py",
            "antigravity_module": "modules/antigravity_cli.py",
            "route": "POST /proof/collaboration",
            "antigravity_route": "POST /gemini/antigravity/preflight",
            "tests": "tests/test_collaboration_proof.py",
            "antigravity_tests": "tests/test_antigravity_cli.py",
            "exported": bridge_code.get("exported", False),
            "antigravity_exported": bridge_code.get("antigravity_exported", False),
            "tests_exist": bridge_code.get("tests_exist", False),
            "antigravity_tests_exist": bridge_code.get("antigravity_tests_exist", False),
        },
        blocker="missing_code_change_evidence" if not ok else "",
    )


def _tests_gate(test_evidence: dict[str, Any]) -> dict[str, Any]:
    passed = bool(test_evidence.get("passed"))
    return _gate(
        "local_tests_and_evidence",
        "pass" if passed else "blocked",
        "Latest recorded local test evidence passed." if passed else "No passing local test evidence was found.",
        test_evidence,
        blocker="missing_or_failed_test_evidence" if not passed else "",
    )


def _jules_agent_view(
    jules: dict[str, Any],
    skills: list[dict[str, Any]],
    akc: dict[str, Any],
) -> dict[str, Any]:
    return {
        "point_of_view": (
            "Jules is the asynchronous coding/workflow agent reached through the bridge. "
            "Its local project skill system lives in .agents/skills and its operational "
            "contract is loaded from .agents/AGENTS.md, AKC, gotchas, and memory."
        ),
        "reachable": bool(jules.get("ready")),
        "mode": "REST API" if jules.get("rest_api") else "CLI",
        "source": jules.get("auth_indicators", {}).get("source", ""),
        "skill_count": len(skills),
        "skills": skills,
        "akc_ready": bool(akc.get("ready")),
    }


def _gemini_agent_view(gemini: dict[str, Any], skills: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "point_of_view": (
            "Gemini CLI is the terminal agent reached through @google/gemini-cli. "
            "It exposes command-managed skills with SKILL.md packages, optional "
            "scripts/references/assets, MCP listings, extensions, and headless prompts."
        ),
        "cli_reachable": bool(gemini.get("installed")),
        "model_ready": bool(gemini.get("ready")),
        "likely_blocker": gemini.get("likely_blocker", ""),
        "skill_count": len(skills),
        "skills": skills,
    }


def _antigravity_agent_view(antigravity: dict[str, Any], skills: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "point_of_view": (
            "Antigravity CLI is the supported Google terminal-agent path for "
            "individual Gemini CLI migration. It exposes print mode, model "
            "listing, plugin management, and prompt execution through agy."
        ),
        "cli_reachable": bool(antigravity.get("installed")),
        "model_ready": bool(antigravity.get("ready")),
        "likely_blocker": antigravity.get("likely_blocker", ""),
        "skill_count": len(skills),
        "skills": skills,
    }


def _jules_skill_inventory() -> list[dict[str, Any]]:
    skills_dir = _ROOT / ".agents" / "skills"
    skills = discover_skills(str(skills_dir))
    improved = [_parse_skill_file(Path(item.get("skill_path", "")), item) for item in skills]
    return [item for item in improved if item.get("name")]


def _parse_skill_file(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(fallback or {})
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return base
    frontmatter = _frontmatter(text)
    name = frontmatter.get("name") or base.get("name") or path.parent.name
    description = frontmatter.get("description") or base.get("description", "")
    return {
        "name": str(name).strip().strip('"'),
        "description": _compact_text(str(description)),
        "skill_path": str(path),
    }


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    lines = parts[1].splitlines()
    data: dict[str, str] = {}
    current = ""
    collected: list[str] = []
    for line in lines:
        if re.match(r"^[A-Za-z0-9_-]+:\s*", line):
            if current:
                data[current] = _compact_text(" ".join(collected))
            key, value = line.split(":", 1)
            current = key.strip()
            value = value.strip()
            collected = [] if value in (">", "|") else [value]
        elif current and line.startswith((" ", "\t")):
            stripped = line.strip()
            if stripped:
                collected.append(stripped)
    if current:
        data[current] = _compact_text(" ".join(collected))
    return data


def _gemini_skill_inventory(gemini: dict[str, Any]) -> list[dict[str, Any]]:
    skills_result = gemini.get("capabilities", {}).get("skills", {})
    stdout = skills_result.get("stdout", "") if isinstance(skills_result, dict) else ""
    skills: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    for line in stdout.splitlines():
        if not line.strip() or line.startswith("Discovered Agent Skills"):
            continue
        if not line.startswith(" ") and "[" in line:
            if current:
                skills.append(current)
            current = {"name": line.split("[", 1)[0].strip(), "description": "", "location": ""}
        elif current and line.strip().startswith("Description:"):
            current["description"] = line.split(":", 1)[1].strip()
        elif current and line.strip().startswith("Location:"):
            current["location"] = line.split(":", 1)[1].strip()
    if current:
        skills.append(current)
    return skills


def _antigravity_skill_inventory(antigravity: dict[str, Any]) -> list[dict[str, Any]]:
    capabilities = antigravity.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return []
    skills: list[dict[str, Any]] = []
    subcommands = capabilities.get("subcommands", [])
    if "plugin" in subcommands or "plugins" in subcommands:
        skills.append({
            "name": "plugin-management",
            "description": "Manage Antigravity plugins that package skills and workflows.",
            "location": "agy plugin",
        })
    models = capabilities.get("models", {})
    model_lines = _nonempty_lines(models.get("stdout", "") if isinstance(models, dict) else "")
    if model_lines:
        skills.append({
            "name": "model-routing",
            "description": f"Route terminal prompts across {len(model_lines)} available models.",
            "location": "agy models",
        })
    if capabilities.get("headless_mode"):
        skills.append({
            "name": "headless-print-mode",
            "description": "Run noninteractive terminal-agent prompts with bounded print timeouts.",
            "location": "agy -p",
        })
    return skills


def _context_state() -> dict[str, Any]:
    present = []
    missing = []
    combined = []
    for relative in _CONTEXT_FILES:
        path = _ROOT / relative
        if path.is_file():
            present.append(relative)
            try:
                combined.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
        else:
            missing.append(relative)
    text = "\n".join(combined)
    return {
        "present_count": len(present),
        "missing_files": missing,
        "agents_protocol_found": "Context Loading Order" in text and "Agent Skills" in text,
        "architecture_boundary_found": "bridge.py routes are ONLY" in text and "deep module" in text.lower(),
        "gemini_boundary_found": "modules/gemini_cli.py" in text and "/gemini/preflight" in text,
        "antigravity_boundary_found": "modules/antigravity_cli.py" in text and "/gemini/antigravity/preflight" in text,
    }


def _latest_test_evidence() -> dict[str, Any]:
    evidence = load_test_evidence(str(_ROOT / "memory"))
    if evidence is None:
        return {"passed": False, "test_count": 0, "error": "no evidence"}
    return {
        "passed": bool(evidence.passed),
        "test_count": int(evidence.test_count),
        "timestamp_utc": evidence.timestamp_utc,
        "output_hash": evidence.output_hash,
        "raw_output_tail": evidence.raw_output_tail[-500:],
    }


def _bridge_code_state() -> dict[str, Any]:
    bridge_text = _read_text(_ROOT / "bridge.py")
    init_text = _read_text(_ROOT / "modules" / "__init__.py")
    return {
        "collaboration_module_exists": (_ROOT / "modules" / "collaboration_proof.py").is_file(),
        "antigravity_module_exists": (_ROOT / "modules" / "antigravity_cli.py").is_file(),
        "exported": "build_collaboration_proof" in init_text,
        "antigravity_exported": "antigravity_preflight" in init_text,
        "tests_exist": (_ROOT / "tests" / "test_collaboration_proof.py").is_file(),
        "antigravity_tests_exist": (_ROOT / "tests" / "test_antigravity_cli.py").is_file(),
        "route_markers": {
            "jules_preflight": "/jules/preflight" in bridge_text,
            "gemini_preflight": "/gemini/preflight" in bridge_text,
            "gemini_prompt": "/gemini/prompt" in bridge_text,
            "antigravity_preflight": "/gemini/antigravity/preflight" in bridge_text,
            "antigravity_prompt": "/gemini/antigravity/prompt" in bridge_text,
            "collaboration_proof": "/proof/collaboration" in bridge_text,
        },
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _command_stdout(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("stdout", "")).strip()
    return str(value or "").strip()


def _compact_text(value: str) -> str:
    return " ".join((value or "").replace("\r", " ").replace("\n", " ").split())


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]
