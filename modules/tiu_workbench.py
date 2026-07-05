"""Interactive TIU workbench planning surface.

This module turns simple dashboard controls into a safe, evidence-backed
operator packet. It composes existing deep-module readiness surfaces instead of
launching workers, running model prompts, or mutating Git.

Public interface:
    build_tiu_workbench_plan(...) -> TIUWorkbenchResult
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .alliance_switchboard import build_alliance_switchboard
from .codebase_analyzer import analyze_codebase
from .cloud_sync import get_cloud_sync_status

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUTPUT_DIR = _ROOT / "jules_inbox" / "tiu_workbench"
_WORD_RE = re.compile(r"\s+")

_SCOPE_TARGETS = {
    "dashboard": [
        "dashboard-ui/src/App.jsx",
        "dashboard-ui/src/dashboardModel.js",
        "dashboard-ui/src/index.css",
        "modules/dashboard_module.py",
        "tests/test_dashboard_module.py",
    ],
    "model_bridge": [
        "modules/gemini_cli.py",
        "modules/antigravity_cli.py",
        "modules/alliance_switchboard.py",
        "modules/collaboration_proof.py",
        "tests/test_gemini_cli.py",
        "tests/test_antigravity_cli.py",
        "tests/test_alliance_switchboard.py",
    ],
    "cloud_sync": [
        "modules/cloud_sync.py",
        "bridge.py",
        "dashboard-ui/src/App.jsx",
        "tests/test_cloud_sync.py",
    ],
    "full_bridge": [
        "bridge.py",
        "modules",
        "dashboard-ui/src",
        "tests",
        "context",
    ],
}


class TIUWorkbenchResult(dict):
    """Keys: status, plan_state, readiness, packet, blockers, artifacts."""


def build_tiu_workbench_plan(
    objective: str,
    *,
    scope: str = "dashboard",
    model_lane: str = "alliance",
    mode: str = "design_review",
    target_files: list[str] | None = None,
    require_cloud_sync: bool = True,
    include_live_checks: bool = False,
    write_packet: bool = False,
    timeout_s: int = 12,
    output_dir: str = "",
) -> TIUWorkbenchResult:
    """Build a safe workbench packet from simple TIU controls.

    Returns a typed dict and never raises. The route/UI can ask for persisted
    packets, but this function does not launch Jules, run Gemini/Antigravity
    prompts, stage files, commit, push, or pull.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        clean_objective = _compact(objective)
        clean_scope = _normalize_token(scope, "dashboard")
        clean_lane = _normalize_token(model_lane, "alliance")
        clean_mode = _normalize_token(mode, "design_review")
        timeout = max(1, min(int(timeout_s or 1), 300))
        files = _target_files(clean_scope, target_files or [])

        codebase = analyze_codebase(max_files=1800, include_files=False)
        cloud_sync = get_cloud_sync_status(timeout_s=min(timeout, 30), use_cache=False)
        alliance = build_alliance_switchboard(
            objective=clean_objective,
            target_files=files,
            complexity="complex" if clean_lane == "alliance" else "focused",
            preferred_creator="jules",
            preferred_implementer=_preferred_implementer(clean_lane),
            include_live_checks=include_live_checks,
            run_implementer_smoke=False,
            write_packets=False,
            timeout_s=timeout,
        )

        readiness = _readiness(codebase, cloud_sync, alliance)
        blockers = _blockers(readiness, require_cloud_sync)
        warnings = _warnings(readiness, require_cloud_sync)
        plan_state = _plan_state(blockers, warnings)
        packet = _packet(
            objective=clean_objective,
            scope=clean_scope,
            mode=clean_mode,
            model_lane=clean_lane,
            target_files=files,
            readiness=readiness,
            blockers=blockers,
            warnings=warnings,
            require_cloud_sync=require_cloud_sync,
        )

        result = TIUWorkbenchResult(
            status="blocked" if blockers else "ready",
            plan_state=plan_state,
            generated_at_utc=generated_at,
            objective=clean_objective,
            controls={
                "scope": clean_scope,
                "model_lane": clean_lane,
                "mode": clean_mode,
                "require_cloud_sync": bool(require_cloud_sync),
                "include_live_checks": bool(include_live_checks),
                "write_packet": bool(write_packet),
            },
            target_files=files,
            readiness=readiness,
            blockers=blockers,
            warnings=warnings,
            packet=packet,
            safety_policy={
                "dry_run_first": True,
                "jules_sessions_created": False,
                "google_prompts_run": False,
                "git_mutations": False,
                "secret_values_returned": False,
            },
            artifacts={"packet_written": False, "packet_path": "", "state_path": ""},
        )

        if write_packet:
            result["artifacts"].update(_write_packet(result, output_dir))

        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return TIUWorkbenchResult(
            status="error",
            plan_state="error",
            generated_at_utc=generated_at,
            error=str(exc),
            blockers=["tiu_workbench_error"],
            warnings=[],
            artifacts={"packet_written": False, "packet_path": "", "state_path": ""},
        )


def _compact(value: str, limit: int = 1600) -> str:
    text = _WORD_RE.sub(" ", str(value or "")).strip()
    return text[:limit]


def _normalize_token(value: str, fallback: str) -> str:
    token = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
    return token or fallback


def _target_files(scope: str, explicit: list[str]) -> list[str]:
    if explicit:
        return [_clean_path(item) for item in explicit if _clean_path(item)][:20]
    return list(_SCOPE_TARGETS.get(scope, _SCOPE_TARGETS["dashboard"]))


def _clean_path(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    text = text.replace("..", "").lstrip("/")
    return text[:180]


def _preferred_implementer(model_lane: str) -> str:
    if model_lane in ("gemini", "gemini_cli", "legacy_gemini"):
        return "gemini_cli"
    if model_lane in ("jules", "jules_only"):
        return "jules"
    return "antigravity_cli"


def _readiness(
    codebase: dict[str, Any],
    cloud_sync: dict[str, Any],
    alliance: dict[str, Any],
) -> dict[str, Any]:
    codebase_summary = codebase.get("summary", {}) if isinstance(codebase, dict) else {}
    sync_repo = cloud_sync.get("repo", {}) if isinstance(cloud_sync, dict) else {}
    sync_git = cloud_sync.get("git", {}) if isinstance(cloud_sync, dict) else {}
    sync_github = cloud_sync.get("github", {}) if isinstance(cloud_sync, dict) else {}
    return {
        "alliance": {
            "status": alliance.get("status", "unknown"),
            "summary": alliance.get("summary", ""),
            "mode": alliance.get("roles", {}).get("mode", ""),
            "implementer": alliance.get("active_implementer", {}).get("name", ""),
            "ready": alliance.get("completion_assessment", {}).get("ready_to_execute_alliance", False),
            "safe_to_launch_live_work": alliance.get("completion_assessment", {}).get("safe_to_launch_live_work", False),
        },
        "codebase": {
            "status": codebase.get("status", "unknown") if isinstance(codebase, dict) else "unknown",
            "route_count": codebase_summary.get("route_count", 0),
            "module_count": codebase_summary.get("module_count", 0),
            "test_count": codebase_summary.get("test_count", 0),
            "integration_ready_count": codebase_summary.get("integration_ready_count", 0),
        },
        "cloud_sync": {
            "status": cloud_sync.get("status", "unknown") if isinstance(cloud_sync, dict) else "unknown",
            "state": cloud_sync.get("state", "unknown") if isinstance(cloud_sync, dict) else "unknown",
            "branch": sync_repo.get("branch", ""),
            "upstream": sync_repo.get("upstream", ""),
            "remote_host": sync_repo.get("remote_host", ""),
            "ahead": sync_git.get("ahead", 0),
            "behind": sync_git.get("behind", 0),
            "dirty_count": sync_git.get("dirty_count", 0),
            "github_authenticated": bool(sync_github.get("authenticated")),
            "publish_ready": bool(cloud_sync.get("publish_ready", False)) if isinstance(cloud_sync, dict) else False,
            "synced": bool(cloud_sync.get("synced", False)) if isinstance(cloud_sync, dict) else False,
            "blockers": list(cloud_sync.get("blockers", [])) if isinstance(cloud_sync, dict) else [],
            "warnings": list(cloud_sync.get("warnings", [])) if isinstance(cloud_sync, dict) else [],
        },
    }


def _blockers(readiness: dict[str, Any], require_cloud_sync: bool) -> list[str]:
    blockers: list[str] = []
    if readiness["codebase"]["status"] != "ready":
        blockers.append("codebase_snapshot_not_ready")
    if not readiness["alliance"]["ready"]:
        blockers.append("alliance_not_ready")
    if require_cloud_sync:
        blockers.extend([f"cloud_sync:{item}" for item in readiness["cloud_sync"]["blockers"]])
    return blockers


def _warnings(readiness: dict[str, Any], require_cloud_sync: bool) -> list[str]:
    warnings = []
    if not readiness["alliance"]["safe_to_launch_live_work"]:
        warnings.append("live_work_gated")
    if not require_cloud_sync:
        warnings.append("cloud_sync_gate_not_required_by_packet")
    warnings.extend([f"cloud_sync:{item}" for item in readiness["cloud_sync"]["warnings"]])
    return warnings


def _plan_state(blockers: list[str], warnings: list[str]) -> str:
    if any(item.startswith("cloud_sync:") for item in blockers):
        return "publish_blocked"
    if blockers:
        return "blocked"
    if warnings:
        return "ready_with_warnings"
    return "ready_for_dry_run"


def _packet(
    *,
    objective: str,
    scope: str,
    mode: str,
    model_lane: str,
    target_files: list[str],
    readiness: dict[str, Any],
    blockers: list[str],
    warnings: list[str],
    require_cloud_sync: bool,
) -> str:
    lines = [
        "# TIU Workbench Packet",
        "",
        f"- objective: {objective}",
        f"- scope: {scope}",
        f"- mode: {mode}",
        f"- model_lane: {model_lane}",
        f"- cloud_sync_required: {str(bool(require_cloud_sync)).lower()}",
        "",
        "## Lanes",
        "",
        "- Jules: creator and actual-change owner",
        f"- Google terminal agent: {readiness['alliance']['implementer'] or 'unassigned'} implementer/reviewer support",
        "- Codex: local dependency, route, test, and browser verification owner",
        "",
        "## Target Files",
        "",
    ]
    lines.extend([f"- {item}" for item in target_files])
    lines.extend([
        "",
        "## Readiness",
        "",
        f"- alliance: {readiness['alliance']['status']} ({readiness['alliance']['summary'] or 'no summary'})",
        (
            "- codebase: "
            f"{readiness['codebase']['route_count']} routes, "
            f"{readiness['codebase']['module_count']} modules, "
            f"{readiness['codebase']['test_count']} tests"
        ),
        (
            "- cloud_sync: "
            f"{readiness['cloud_sync']['state']} on {readiness['cloud_sync']['branch'] or 'branch'} -> "
            f"{readiness['cloud_sync']['upstream'] or 'no upstream'}; "
            f"{readiness['cloud_sync']['dirty_count']} dirty"
        ),
        "",
        "## Operator Gates",
        "",
    ])
    if blockers:
        lines.extend([f"- BLOCKED: {item}" for item in blockers])
    else:
        lines.append("- READY: dry-run packet can be reviewed or sent to the selected lane.")
    lines.extend([f"- WARNING: {item}" for item in warnings])
    lines.extend([
        "",
        "## Next Actions",
        "",
        "1. Review this packet and target scope.",
        "2. Keep live Jules launch and Google edit prompts disabled unless explicitly approved.",
        "3. Implement locally, run focused tests, then browser QA on the Jules dashboard.",
        "4. Resolve cloud sync blockers before claiming push/simultaneous sync complete.",
    ])
    return "\n".join(lines)


def _write_packet(result: TIUWorkbenchResult, output_dir: str) -> dict[str, Any]:
    directory = Path(output_dir).expanduser() if output_dir else _DEFAULT_OUTPUT_DIR
    if not directory.is_absolute():
        directory = _ROOT / directory
    directory = directory.resolve()
    try:
        directory.relative_to(_ROOT)
    except ValueError:
        return {"packet_written": False, "packet_path": "", "state_path": "", "error": "output_dir must stay inside bridge repo"}
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    packet_path = directory / f"TIU_WORKBENCH_PACKET_{stamp}.md"
    state_path = directory / "TIU_WORKBENCH_STATE.json"
    packet_path.write_text(result["packet"], encoding="utf-8")
    state_path.write_text(json.dumps(dict(result), indent=2), encoding="utf-8")
    return {"packet_written": True, "packet_path": str(packet_path), "state_path": str(state_path)}
