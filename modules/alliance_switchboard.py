"""Role switchboard for Jules plus the supported Google terminal agent.

This module turns a broad complex-codebase objective into a dry-run-first
alliance plan. It does not launch Jules sessions, run agent prompts, or edit the
workspace. Optional live checks are bounded preflight probes only.

Public interface:
    build_alliance_switchboard(...) -> AllianceSwitchboardResult
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .akc_module import check_akc_readiness
from .antigravity_cli import antigravity_preflight, antigravity_status_snapshot
from .gemini_cli import gemini_preflight, gemini_status_snapshot
from .jules_orchestrator import jules_preflight

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ALLIANCE_DIR = _ROOT / "jules_inbox" / "alliance"
_DEFAULT_STATE = "ALLIANCE_SWITCHBOARD_STATE.json"
_DEFAULT_PROOF_STATE = _ROOT / "jules_inbox" / "proof" / "COLLABORATION_PROOF.json"
_JULES_PREFLIGHT_STATE = _ROOT / "jules_inbox" / "jules_dispatch" / "JULES_PREFLIGHT.json"
_WORD_RE = re.compile(r"\s+")


class AllianceSwitchboardResult(dict):
    """Keys: status, roles, switching_policy, gates, workflow, packets."""


def build_alliance_switchboard(
    objective: str,
    target_files: list[str] | None = None,
    complexity: str = "complex",
    preferred_creator: str = "jules",
    preferred_implementer: str = "antigravity_cli",
    include_live_checks: bool = False,
    run_implementer_smoke: bool = False,
    write_packets: bool = False,
    state_path: str = "",
    timeout_s: int = 12,
) -> AllianceSwitchboardResult:
    """Build a dry-run-first role plan for complex Jules/Google CLI work.

    Args:
        objective: User objective to assign across the alliance.
        target_files: Optional files or directories that bound the work.
        complexity: Caller classification; complex defaults to two-agent mode.
        preferred_creator: Preferred owner for actual change creation.
        preferred_implementer: Preferred support implementer/reviewer.
        include_live_checks: Run bounded preflight probes instead of snapshots.
        run_implementer_smoke: If live checks are enabled, run a minimal agy smoke.
        write_packets: Persist switchboard state and markdown role packets.
        state_path: Optional state JSON path or output directory.
        timeout_s: Bounded CLI/API preflight timeout.

    Returns:
        AllianceSwitchboardResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        clean_objective = _compact(objective)
        clean_files = _clean_target_files(target_files or [])
        clean_complexity = _normalize_token(complexity, "complex")
        creator_key = _normalize_actor(preferred_creator, "jules")
        implementer_key = _normalize_actor(preferred_implementer, "antigravity_cli")
        timeout = max(1, int(timeout_s or 1))

        proof = _read_json(_DEFAULT_PROOF_STATE)
        jules = _jules_readiness(include_live_checks, timeout)
        antigravity = _antigravity_readiness(include_live_checks, run_implementer_smoke, timeout)
        gemini = _gemini_readiness(include_live_checks, timeout)
        akc = check_akc_readiness()

        active_implementer = _select_implementer(
            implementer_key=implementer_key,
            antigravity=antigravity,
            gemini=gemini,
            jules=jules,
        )
        roles = _role_assignments(
            objective=clean_objective,
            complexity=clean_complexity,
            preferred_creator=creator_key,
            preferred_implementer=implementer_key,
            active_implementer=active_implementer,
            target_files=clean_files,
        )
        switching_policy = _switching_policy(
            preferred_creator=creator_key,
            preferred_implementer=implementer_key,
            active_implementer=active_implementer,
        )
        gates = _gates(
            objective=clean_objective,
            creator_key=creator_key,
            implementer_key=implementer_key,
            active_implementer=active_implementer,
            jules=jules,
            antigravity=antigravity,
            gemini=gemini,
            akc=akc,
            proof=proof,
        )
        workflow = _workflow(clean_complexity, active_implementer)
        agent_views = _agent_views(jules, antigravity, gemini, akc, proof)
        packet_previews = _packet_previews(clean_objective, clean_files, roles, switching_policy)

        payload = AllianceSwitchboardResult(
            generated_at_utc=generated_at,
            status=_overall_status(gates),
            summary=_summary(gates, active_implementer),
            objective=clean_objective,
            complexity=clean_complexity,
            target_files=clean_files,
            roles=roles,
            active_implementer=active_implementer,
            switching_policy=switching_policy,
            workflow=workflow,
            agent_views=agent_views,
            gates=gates,
            packets={
                "written": False,
                "state_path": "",
                "packet_paths": {},
                "previews": packet_previews,
            },
            safety_policy=_build_safety_policy(include_live_checks, run_implementer_smoke),
            readiness=_build_readiness_block(jules, antigravity, gemini, akc, proof),
            completion_assessment=_completion_assessment(gates, active_implementer),
        )

        if write_packets:
            packet_result = _write_packets(payload, state_path)
            payload["packets"].update(packet_result)
            if packet_result.get("error"):
                payload["status"] = "partial" if payload["status"] == "ready" else payload["status"]

        return payload
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return AllianceSwitchboardResult(
            generated_at_utc=generated_at,
            status="error",
            summary="Alliance switchboard failed before role assignment completed.",
            error=str(exc),
            gates=[_gate("switchboard_runtime", "blocked", str(exc), required=True, blocker=str(exc))],
            blockers=[{"gate": "switchboard_runtime", "blocker": str(exc), "status": "blocked"}],
        )



def _build_safety_policy(include_live_checks: bool, run_implementer_smoke: bool) -> dict[str, Any]:
    return {
        "default_mode": "dry_run",
        "live_side_effects": "none",
        "jules_sessions_created": False,
        "google_cli_prompts_run": bool(include_live_checks and run_implementer_smoke),
        "workspace_edits": False,
        "note": (
            "This switchboard only assigns roles and prepares packets. "
            "Execution still requires explicit route calls and live flags."
        ),
    }


def _build_readiness_block(jules: dict[str, Any], antigravity: dict[str, Any], gemini: dict[str, Any], akc: dict[str, Any], proof: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "jules": _readiness_summary(jules),
        "antigravity_cli": _readiness_summary(antigravity),
        "legacy_gemini_cli": _readiness_summary(gemini),
        "akc": {
            "ready": bool(akc.get("ready")),
            "status": akc.get("status", ""),
            "checkpoint_path": akc.get("checkpoint_path", ""),
        },
        "collaboration_proof_state": {
            "available": bool(proof),
            "status": proof.get("status", "") if isinstance(proof, dict) else "",
            "state_path": str(_DEFAULT_PROOF_STATE) if _DEFAULT_PROOF_STATE.exists() else "",
        },
    }


def _jules_readiness(include_live_checks: bool, timeout_s: int) -> dict[str, Any]:
    if include_live_checks:
        result = dict(jules_preflight(timeout_s=timeout_s, check_remote=True, write_state=False))
        result["source"] = "live_preflight"
        return result
    state = _read_json(_JULES_PREFLIGHT_STATE)
    return {
        "ready": bool(state.get("ready")),
        "installed": bool(state.get("ready") or state.get("version")),
        "likely_blocker": state.get("likely_blocker", "missing_jules_preflight_state") if not state else state.get("likely_blocker", ""),
        "state_path": str(_JULES_PREFLIGHT_STATE) if _JULES_PREFLIGHT_STATE.exists() else "",
        "source": "persisted_preflight_state",
        "rest_api": bool(state.get("rest_api")),
        "auth_indicators": state.get("auth_indicators", {}) if isinstance(state, dict) else {},
    }


def _antigravity_readiness(
    include_live_checks: bool,
    run_implementer_smoke: bool,
    timeout_s: int,
) -> dict[str, Any]:
    if include_live_checks:
        result = dict(antigravity_preflight(
            timeout_s=timeout_s,
            run_smoke=run_implementer_smoke,
            write_state=False,
        ))
        result["source"] = "live_preflight"
        return result
    result = dict(antigravity_status_snapshot())
    result["source"] = "status_snapshot"
    return result


def _gemini_readiness(include_live_checks: bool, timeout_s: int) -> dict[str, Any]:
    if include_live_checks:
        result = dict(gemini_preflight(timeout_s=timeout_s, run_smoke=False, write_state=False))
        result["source"] = "live_preflight"
        return result
    result = dict(gemini_status_snapshot())
    result["source"] = "status_snapshot"
    return result


def _select_implementer(
    implementer_key: str,
    antigravity: dict[str, Any],
    gemini: dict[str, Any],
    jules: dict[str, Any],
) -> dict[str, Any]:
    agy_ready = bool(antigravity.get("ready"))
    gemini_available = bool(gemini.get("ready") or gemini.get("installed"))
    jules_ready = bool(jules.get("ready"))

    if implementer_key in ("antigravity_cli", "google_terminal", "agy"):
        if agy_ready:
            return _active_implementer("antigravity_cli", "preferred", True, "Supported Google terminal agent is ready.")
        if gemini_available:
            return _active_implementer("gemini_cli_legacy", "fallback", False, "Legacy Gemini CLI is available as a compatibility fallback.")
        if jules_ready:
            return _active_implementer("jules_solo_fallback", "fallback", False, "Jules is ready, but no separate Google implementer is ready.")
        return _active_implementer("unassigned", "blocked", False, "No implementer lane is ready.")

    if implementer_key in ("gemini_cli", "gemini_cli_legacy"):
        if gemini_available:
            return _active_implementer("gemini_cli_legacy", "preferred", False, "Legacy Gemini CLI is available.")
        if agy_ready:
            return _active_implementer("antigravity_cli", "fallback", True, "Supported Antigravity CLI replaces the legacy Gemini lane.")
        if jules_ready:
            return _active_implementer("jules_solo_fallback", "fallback", False, "Jules is ready, but no Google implementer is ready.")
        return _active_implementer("unassigned", "blocked", False, "No implementer lane is ready.")

    if implementer_key in ("jules", "jules_cli", "jules_rest"):
        if jules_ready:
            return _active_implementer("jules_solo_fallback", "preferred", False, "Jules owns both creation and implementation.")
        return _active_implementer("unassigned", "blocked", False, "Requested Jules implementer is not ready.")

    if agy_ready:
        return _active_implementer("antigravity_cli", "fallback", True, "Unknown implementer preference; using supported Google terminal agent.")
    if jules_ready:
        return _active_implementer("jules_solo_fallback", "fallback", False, "Unknown implementer preference; using Jules-only fallback.")
    return _active_implementer("unassigned", "blocked", False, "Unknown implementer preference and no fallback is ready.")


def _active_implementer(name: str, selection: str, separate_agent: bool, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "selection": selection,
        "separate_agent": separate_agent,
        "reason": reason,
    }


def _role_assignments(
    objective: str,
    complexity: str,
    preferred_creator: str,
    preferred_implementer: str,
    active_implementer: dict[str, Any],
    target_files: list[str],
) -> dict[str, Any]:
    return {
        "switch_controller": {
            "agent": "jules_bridge_codex",
            "owns": [
                "classify task complexity",
                "keep live execution gated",
                "route work to creator and implementer lanes",
                "collect proof before completion",
            ],
            "code_surfaces": ["POST /alliance/switchboard", "POST /proof/collaboration"],
        },
        "creator": {
            "agent": preferred_creator,
            "preferred_agent": "jules",
            "owns": [
                "actual change plan",
                "patch or worker packet creation",
                "repo-specific context application",
                "completion ledger back to the bridge",
            ],
            "code_surfaces": [
                "modules/jules_orchestrator.py",
                "POST /jules/dispatch",
                "POST /jules/cycle",
                "POST /jules/fleet-watch",
                "POST /jules/api/sessions",
            ],
            "objective": objective,
            "target_files": target_files,
        },
        "implementer": {
            "agent": active_implementer["name"],
            "preferred_agent": preferred_implementer,
            "selection": active_implementer["selection"],
            "owns": [
                "implementation critique and local-code suggestions",
                "model/plugin capability explanation",
                "bounded prompt response for complex codebase questions",
                "second-opinion review before live launch",
            ],
            "code_surfaces": _implementer_surfaces(active_implementer["name"]),
        },
        "verifier": {
            "agent": "jules_bridge_tests",
            "owns": [
                "py_compile",
                "focused pytest",
                "full pytest when the touched surface is broad",
                "recorded evidence hash",
            ],
            "code_surfaces": ["tests/", "POST /retrospective/record_evidence"],
        },
        "mode": "two_agent_alliance" if active_implementer.get("separate_agent") else "single_agent_fallback",
        "complexity": complexity,
    }


def _implementer_surfaces(agent: str) -> list[str]:
    if agent == "antigravity_cli":
        return [
            "modules/antigravity_cli.py",
            "POST /gemini/antigravity/preflight",
            "POST /gemini/antigravity/prompt",
        ]
    if agent == "gemini_cli_legacy":
        return ["modules/gemini_cli.py", "POST /gemini/preflight", "POST /gemini/prompt"]
    if agent == "jules_solo_fallback":
        return ["modules/jules_orchestrator.py", "POST /jules/dispatch", "POST /jules/cycle"]
    return []


def _switching_policy(
    preferred_creator: str,
    preferred_implementer: str,
    active_implementer: dict[str, Any],
) -> dict[str, Any]:
    return {
        "preferred": {
            "creator": preferred_creator,
            "implementer": preferred_implementer,
        },
        "active": {
            "creator": preferred_creator,
            "implementer": active_implementer["name"],
            "selection": active_implementer["selection"],
        },
        "decision_table": [
            {
                "condition": "complex task and Jules ready and Antigravity ready",
                "route": "Jules creates the patch/worker packet; Antigravity implements/reviews through dry-run prompt support.",
            },
            {
                "condition": "Jules ready but Antigravity unavailable",
                "route": "Jules owns creation and implementation; bridge marks alliance as partial until the Google lane is restored.",
            },
            {
                "condition": "Antigravity ready but Jules unavailable",
                "route": "Antigravity can analyze, but actual change creation is blocked until Jules or Codex owns the patch.",
            },
            {
                "condition": "legacy Gemini installed but model smoke blocked",
                "route": "Use it only for capability/skill visibility; prefer Antigravity for supported model execution.",
            },
            {
                "condition": "any live execution requested",
                "route": "Require explicit route-specific live flags, bounded timeout, proof capture, and no secret printing.",
            },
        ],
        "handoff_contract": [
            "creator returns changed files, tests run, blockers, and next action",
            "implementer returns reasoning, suggested patch scope, and risk list",
            "switch controller records proof before calling the goal complete",
        ],
    }


def _gates(
    objective: str,
    creator_key: str,
    implementer_key: str,
    active_implementer: dict[str, Any],
    jules: dict[str, Any],
    antigravity: dict[str, Any],
    gemini: dict[str, Any],
    akc: dict[str, Any],
    proof: dict[str, Any],
) -> list[dict[str, Any]]:
    creator_ready = bool(jules.get("ready")) if creator_key in ("jules", "jules_cli", "jules_rest") else False
    agy_ready = bool(antigravity.get("ready"))
    gemini_available = bool(gemini.get("ready") or gemini.get("installed"))
    preferred_implementer_ready = (
        agy_ready
        if implementer_key in ("antigravity_cli", "google_terminal", "agy")
        else gemini_available
        if implementer_key in ("gemini_cli", "gemini_cli_legacy")
        else creator_ready
        if implementer_key in ("jules", "jules_cli", "jules_rest")
        else False
    )
    implementer_assigned = active_implementer["name"] != "unassigned"
    separate_ready = bool(creator_ready and implementer_assigned and active_implementer.get("separate_agent"))

    return [
        _gate(
            "objective_present",
            "pass" if objective else "blocked",
            "Objective is present." if objective else "Objective is required before assigning work.",
            required=True,
            blocker="" if objective else "missing_objective",
        ),
        _gate(
            "creator_jules_reachable",
            "pass" if creator_ready else "blocked",
            "Jules is ready to own creation." if creator_ready else "Preferred creator Jules is not ready.",
            evidence=_readiness_summary(jules),
            required=True,
            blocker="" if creator_ready else jules.get("likely_blocker", "jules_not_ready"),
        ),
        _gate(
            "preferred_implementer_reachable",
            "pass" if preferred_implementer_ready else "partial" if implementer_assigned else "blocked",
            _implementer_gate_summary(preferred_implementer_ready, active_implementer),
            evidence={
                "preferred": implementer_key,
                "active": active_implementer,
                "antigravity": _readiness_summary(antigravity),
                "legacy_gemini": _readiness_summary(gemini),
            },
            required=True,
            blocker="" if implementer_assigned else "no_implementer_lane_ready",
        ),
        _gate(
            "simultaneous_alliance_ready",
            "pass" if separate_ready else "partial" if creator_ready and implementer_assigned else "blocked",
            "Creator and separate implementer lanes are both ready."
            if separate_ready
            else active_implementer.get("reason", "Alliance fallback selected."),
            evidence={"mode": "two_agent_alliance" if separate_ready else "fallback", "active_implementer": active_implementer},
            required=False,
            blocker="" if separate_ready or implementer_assigned else "not_simultaneous",
        ),
        _gate(
            "context_checkpoint_ready",
            "pass" if akc.get("ready") else "partial" if akc.get("status") == "partial" else "blocked",
            "AKC checkpoint is ready." if akc.get("ready") else f"AKC checkpoint status={akc.get('status', '')}.",
            evidence={
                "checkpoint_path": akc.get("checkpoint_path", ""),
                "missing_required_rules": akc.get("missing_required_rules", []),
            },
            required=False,
            blocker="" if akc.get("ready") else "akc_not_ready",
        ),
        _gate(
            "switching_policy_defined",
            "pass",
            "Decision table and handoff contract are defined.",
            required=True,
        ),
        _gate(
            "dry_run_safety_enforced",
            "pass",
            "Switchboard prepares packets only; live agent execution remains behind explicit route flags.",
            required=True,
        ),
        _gate(
            "collaboration_proof_state_available",
            "pass" if proof else "partial",
            "Prior collaboration proof state is available." if proof else "No persisted collaboration proof state found.",
            evidence={
                "state_path": str(_DEFAULT_PROOF_STATE) if _DEFAULT_PROOF_STATE.exists() else "",
                "status": proof.get("status", "") if isinstance(proof, dict) else "",
            },
            required=False,
        ),
    ]


def _implementer_gate_summary(preferred_ready: bool, active_implementer: dict[str, Any]) -> str:
    if preferred_ready:
        return "Preferred implementer lane is ready."
    if active_implementer["name"] != "unassigned":
        return f"Preferred implementer is not ready; selected {active_implementer['name']} as {active_implementer['selection']}."
    return "No implementer lane is ready."


def _workflow(complexity: str, active_implementer: dict[str, Any]) -> list[dict[str, Any]]:
    mode = "two_agent_alliance" if active_implementer.get("separate_agent") else "single_agent_fallback"
    return [
        {
            "step": "classify",
            "owner": "switch_controller",
            "action": f"Treat this as {complexity}; choose {mode}.",
        },
        {
            "step": "context",
            "owner": "switch_controller",
            "action": "Load AKC/context and target file inventory before any implementation prompt.",
        },
        {
            "step": "creator_plan",
            "owner": "jules",
            "action": "Produce the concrete change plan, affected files, test plan, and blocker list.",
        },
        {
            "step": "implementer_review",
            "owner": active_implementer["name"],
            "action": "Review or draft implementation details through dry-run-first terminal-agent prompts.",
        },
        {
            "step": "apply_change",
            "owner": "jules_or_codex_operator",
            "action": "Apply code only after the plan is bounded and live flags are explicit.",
        },
        {
            "step": "verify",
            "owner": "verifier",
            "action": "Run focused tests, full tests when needed, and record evidence hash.",
        },
    ]


def _agent_views(
    jules: dict[str, Any],
    antigravity: dict[str, Any],
    gemini: dict[str, Any],
    akc: dict[str, Any],
    proof: dict[str, Any],
) -> dict[str, Any]:
    proof_agents = proof.get("agents", {}) if isinstance(proof, dict) else {}
    return {
        "jules": {
            "point_of_view": (
                "I am Jules in this bridge: I own asynchronous creation work, "
                "worker packets, patches, completion ledgers, and repo-specific execution."
            ),
            "skills_framework": (
                "My skills are SKILL.md packages under .agents/skills plus the operating "
                "contract in .agents/AGENTS.md, AKC checkpoints, gotchas, and memory."
            ),
            "code_surfaces": [
                "modules/jules_orchestrator.py",
                "modules/jules_api.py",
                "POST /jules/preflight",
                "POST /jules/dispatch",
                "POST /jules/cycle",
                "POST /jules/fleet-watch",
            ],
            "readiness": _readiness_summary(jules),
            "skill_count": len(_jules_skills()),
            "skills": _jules_skills(),
            "akc_ready": bool(akc.get("ready")),
        },
        "google_terminal_agent": {
            "point_of_view": (
                "I am the supported Google terminal-agent lane, exposed here through "
                "Antigravity CLI after the Gemini CLI migration."
            ),
            "skills_framework": (
                "My capability framework is command-discovered: agy models for model "
                "routing, agy plugin list for plugin/skill packages, and agy -p for "
                "bounded noninteractive prompts."
            ),
            "code_surfaces": [
                "modules/antigravity_cli.py",
                "POST /gemini/antigravity/preflight",
                "POST /gemini/antigravity/prompt",
            ],
            "readiness": _readiness_summary(antigravity),
            "skills": _google_terminal_skills(antigravity, proof_agents),
        },
        "legacy_gemini_cli": {
            "point_of_view": (
                "I am the legacy @google/gemini-cli lane. I can still expose install, "
                "MCP, extension, and skill surfaces, but model execution may be blocked "
                "by Google consumer-tier migration state."
            ),
            "skills_framework": (
                "My skills are discovered with gemini skills list --all, alongside MCP "
                "and extension listings. The bridge keeps this lane visible as a caveat "
                "instead of treating it as the supported model-execution path."
            ),
            "code_surfaces": ["modules/gemini_cli.py", "POST /gemini/preflight", "POST /gemini/prompt"],
            "readiness": _readiness_summary(gemini),
            "skills": _legacy_gemini_skills(gemini, proof_agents),
        },
    }


def _packet_previews(
    objective: str,
    target_files: list[str],
    roles: dict[str, Any],
    switching_policy: dict[str, Any],
) -> dict[str, str]:
    return {
        "creator_jules": _creator_packet(objective, target_files, roles),
        "implementer_google": _implementer_packet(objective, target_files, roles),
        "switching_policy": _policy_packet(switching_policy),
    }


def _write_packets(payload: dict[str, Any], state_path: str) -> dict[str, Any]:
    try:
        state_file, packet_dir = _state_destination(state_path)
        packet_dir.mkdir(parents=True, exist_ok=True)
        previews = payload.get("packets", {}).get("previews", {})
        paths = {
            "creator_jules": packet_dir / "ALLIANCE_CREATOR_JULES.md",
            "implementer_google": packet_dir / "ALLIANCE_IMPLEMENTER_GOOGLE_TERMINAL.md",
            "switching_policy": packet_dir / "ALLIANCE_SWITCHING_POLICY.md",
        }
        for key, path in paths.items():
            path.write_text(previews.get(key, ""), encoding="utf-8")
        payload["packets"]["state_path"] = str(state_file)
        payload["packets"]["packet_paths"] = {key: str(path) for key, path in paths.items()}
        payload["packets"]["written"] = True
        state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "written": True,
            "state_path": str(state_file),
            "packet_paths": {key: str(path) for key, path in paths.items()},
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {"written": False, "state_path": "", "packet_paths": {}, "error": str(exc)}


def _creator_packet(objective: str, target_files: list[str], roles: dict[str, Any]) -> str:
    files = "\n".join(f"- {item}" for item in target_files) if target_files else "- No explicit target files supplied."
    return f"""# Alliance Creator Packet: Jules

Objective: {objective}

Role: Create the actual change plan and own the patch or Jules worker packet.

Target Files:
{files}

Responsibilities:
- Read AKC/context and current repo state before editing.
- Return affected files, tests, blockers, and exact next action.
- Do not create remote sessions or apply live changes unless the operator sends explicit live flags.
- Preserve dry-run-first behavior and keep secrets redacted.

Bridge Surfaces:
- POST /jules/preflight
- POST /jules/dispatch
- POST /jules/cycle
- POST /jules/fleet-watch

Current Mode: {roles.get("mode", "")}
"""


def _implementer_packet(objective: str, target_files: list[str], roles: dict[str, Any]) -> str:
    files = "\n".join(f"- {item}" for item in target_files) if target_files else "- No explicit target files supplied."
    implementer = roles.get("implementer", {}).get("agent", "")
    return f"""# Alliance Implementer Packet: Google Terminal Agent

Objective: {objective}

Active Implementer: {implementer}

Role: Support implementation with bounded codebase reasoning, model/plugin capability checks, and review notes.

Target Files:
{files}

Responsibilities:
- Use Antigravity CLI as the supported Google terminal-agent path when ready.
- Keep prompts dry-run-first; do not request edit-capable execution without explicit approval.
- Explain skill/plugin/model capability from the CLI point of view.
- Return risks, suggested patch scope, and verification ideas to Jules/the bridge.

Bridge Surfaces:
- POST /gemini/antigravity/preflight
- POST /gemini/antigravity/prompt
- POST /gemini/preflight
- POST /gemini/prompt
"""


def _policy_packet(policy: dict[str, Any]) -> str:
    rows = "\n".join(
        f"- If {item['condition']}: {item['route']}"
        for item in policy.get("decision_table", [])
    )
    contract = "\n".join(f"- {item}" for item in policy.get("handoff_contract", []))
    return f"""# Alliance Switching Policy

Preferred Creator: {policy.get("preferred", {}).get("creator", "")}
Preferred Implementer: {policy.get("preferred", {}).get("implementer", "")}
Active Implementer: {policy.get("active", {}).get("implementer", "")}

Decision Table:
{rows}

Handoff Contract:
{contract}
"""


def _state_destination(state_path: str) -> tuple[Path, Path]:
    if state_path:
        raw = Path(state_path)
        if raw.suffix.lower() == ".json":
            return raw, raw.parent
        return raw / _DEFAULT_STATE, raw
    return _DEFAULT_ALLIANCE_DIR / _DEFAULT_STATE, _DEFAULT_ALLIANCE_DIR


def _completion_assessment(gates: list[dict[str, Any]], active_implementer: dict[str, Any]) -> dict[str, Any]:
    required_blockers = [
        {"gate": gate["name"], "blocker": gate.get("blocker", ""), "status": gate["status"]}
        for gate in gates
        if gate.get("required", True) and gate["status"] == "blocked"
    ]
    partials = [
        {"gate": gate["name"], "status": gate["status"], "summary": gate["summary"]}
        for gate in gates
        if gate["status"] == "partial"
    ]
    return {
        "ready_to_execute_alliance": not required_blockers and active_implementer["name"] != "unassigned",
        "simultaneous_two_agent_mode": bool(active_implementer.get("separate_agent")),
        "required_blockers": required_blockers,
        "partial_caveats": partials,
        "safe_to_launch_live_work": False,
        "launch_note": "This result is a plan/packet proof only; live work still needs explicit live route calls.",
    }


def _overall_status(gates: list[dict[str, Any]]) -> str:
    if any(gate.get("required", True) and gate["status"] == "blocked" for gate in gates):
        return "blocked"
    if any(gate["status"] == "partial" for gate in gates):
        return "partial"
    return "ready"


def _summary(gates: list[dict[str, Any]], active_implementer: dict[str, Any]) -> str:
    status = _overall_status(gates)
    passed = sum(1 for gate in gates if gate["status"] == "pass")
    total = len(gates)
    if status == "ready":
        return f"{passed}/{total} switchboard gates passed; Jules creator and {active_implementer['name']} implementer are assigned."
    if status == "partial":
        return f"{passed}/{total} switchboard gates passed; alliance uses {active_implementer['name']} with caveats."
    blockers = [gate["name"] for gate in gates if gate.get("required", True) and gate["status"] == "blocked"]
    return f"{passed}/{total} switchboard gates passed; required blockers remain at {', '.join(blockers)}."


def _gate(
    name: str,
    status: str,
    summary: str,
    evidence: dict[str, Any] | None = None,
    required: bool = True,
    blocker: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "required": required,
        "summary": summary,
        "evidence": evidence or {},
        "blocker": blocker,
    }


def _readiness_summary(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "ready": bool(source.get("ready")),
        "installed": bool(source.get("installed") or source.get("ready")),
        "source": source.get("source", ""),
        "likely_blocker": source.get("likely_blocker", "") or source.get("last_blocker", ""),
        "state_path": source.get("state_path", ""),
        "version": source.get("version", "") if isinstance(source.get("version", ""), str) else "",
    }


def _jules_skills() -> list[dict[str, str]]:
    skills_dir = _ROOT / ".agents" / "skills"
    skills: list[dict[str, str]] = []
    if not skills_dir.is_dir():
        return skills
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        text = _read_text(skill_file)
        frontmatter = _frontmatter(text)
        skills.append({
            "name": frontmatter.get("name") or skill_file.parent.name,
            "description": frontmatter.get("description", ""),
            "location": str(skill_file),
        })
    return skills


def _google_terminal_skills(antigravity: dict[str, Any], proof_agents: dict[str, Any]) -> list[dict[str, str]]:
    proof_skills = proof_agents.get("antigravity", {}).get("skills", []) if isinstance(proof_agents, dict) else []
    if proof_skills:
        return proof_skills
    skills = [
        {
            "name": "headless-print-mode",
            "description": "Run bounded noninteractive prompts with agy -p.",
            "location": "agy -p",
        },
        {
            "name": "plugin-management",
            "description": "List and manage terminal-agent plugins.",
            "location": "agy plugin list",
        },
    ]
    model_count = antigravity.get("model_count")
    capabilities = antigravity.get("capabilities", {})
    if isinstance(capabilities, dict):
        models = capabilities.get("models", {})
        if isinstance(models, dict):
            model_count = len([line for line in models.get("stdout", "").splitlines() if line.strip()])
    if model_count:
        skills.append({
            "name": "model-routing",
            "description": f"Route prompts across {model_count} discovered models.",
            "location": "agy models",
        })
    return skills


def _legacy_gemini_skills(gemini: dict[str, Any], proof_agents: dict[str, Any]) -> list[dict[str, str]]:
    proof_skills = proof_agents.get("gemini", {}).get("skills", []) if isinstance(proof_agents, dict) else []
    if proof_skills:
        return proof_skills
    skills_result = gemini.get("capabilities", {}).get("skills", {}) if isinstance(gemini.get("capabilities"), dict) else {}
    stdout = skills_result.get("stdout", "") if isinstance(skills_result, dict) else ""
    parsed = []
    current: dict[str, str] | None = None
    for line in stdout.splitlines():
        if not line.strip() or line.startswith("Discovered Agent Skills"):
            continue
        if not line.startswith(" ") and "[" in line:
            if current:
                parsed.append(current)
            current = {"name": line.split("[", 1)[0].strip(), "description": "", "location": ""}
        elif current and line.strip().startswith("Description:"):
            current["description"] = line.split(":", 1)[1].strip()
        elif current and line.strip().startswith("Location:"):
            current["location"] = line.split(":", 1)[1].strip()
    if current:
        parsed.append(current)
    if parsed:
        return parsed
    return [
        {
            "name": "skill-discovery",
            "description": "Discover Gemini CLI SKILL.md packages with gemini skills list --all.",
            "location": "gemini skills list --all",
        },
        {
            "name": "mcp-extension-discovery",
            "description": "Inspect MCP and extension surfaces without provider SDK coupling.",
            "location": "gemini mcp list; gemini extensions list",
        },
    ]


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    current = ""
    collected: list[str] = []
    for line in parts[1].splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:\s*", line):
            if current:
                data[current] = _compact(" ".join(collected))
            key, value = line.split(":", 1)
            current = key.strip()
            value = value.strip()
            collected = [] if value in (">", "|") else [value]
        elif current and line.startswith((" ", "\t")):
            stripped = line.strip()
            if stripped:
                collected.append(stripped)
    if current:
        data[current] = _compact(" ".join(collected))
    return data


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
    return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _clean_target_files(target_files: list[str]) -> list[str]:
    clean = []
    for item in target_files:
        value = _compact(str(item))
        if value:
            clean.append(value)
    return clean


def _normalize_actor(value: str, default: str) -> str:
    token = _normalize_token(value, default)
    aliases = {
        "jules_cli": "jules",
        "jules_rest": "jules",
        "google": "antigravity_cli",
        "google_cli": "antigravity_cli",
        "google_terminal_agent": "antigravity_cli",
        "antigravity": "antigravity_cli",
        "agy": "antigravity_cli",
        "gemini": "gemini_cli_legacy",
        "gemini_cli": "gemini_cli_legacy",
    }
    return aliases.get(token, token)


def _normalize_token(value: str, default: str) -> str:
    raw = (value or default).strip().lower()
    return re.sub(r"[^a-z0-9_]+", "_", raw).strip("_") or default


def _compact(value: str) -> str:
    return _WORD_RE.sub(" ", (value or "").strip())
