"""Dashboard module — real-time multi-cloud status aggregator.

Collects GCP VM, Azure VM, bridge health, resource pressure, Jules fleet
state, and recent log lines into a single snapshot dict.

Public interface:
    get_dashboard_status() -> dict
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.antigravity_cli import antigravity_status_snapshot
from modules.codebase_analyzer import analyze_codebase
from modules.cloud_sync import get_cloud_sync_status
from modules.gemini_cli import gemini_status_snapshot
from modules.repo_context_guard import build_repo_context_guard
from modules.vm_manager import detect_resource_pressure

_ROOT = Path(__file__).parent.parent
_LOG_PATH = _ROOT / "bridge.log"
_LAUNCH_STATE = _ROOT / "jules_inbox" / "jules_dispatch" / "JULES_LAUNCH_STATE.json"
_COT_LEDGER = _ROOT / "jules_inbox" / "jules_dispatch" / "JULES_COT_LEDGER.json"
_WATCH_STATE = _ROOT / "jules_inbox" / "jules_dispatch" / "JULES_WATCH_STATE.json"
_ALLIANCE_STATE = _ROOT / "jules_inbox" / "alliance" / "ALLIANCE_SWITCHBOARD_STATE.json"
_ENV_PATH = _ROOT / ".env"

_LOG_TAIL_LINES = 40

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_vars() -> dict[str, str]:
    """Read .env file into a dict (no process env side effects)."""
    env: dict[str, str] = {}
    try:
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return env


def _tcp_reachable(host: str, port: int = 22, timeout: float = 3.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _tail_log(n: int = _LOG_TAIL_LINES) -> list[str]:
    """Return the last n lines of bridge.log."""
    try:
        text = _LOG_PATH.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return lines[-n:] if len(lines) >= n else lines
    except Exception:  # pylint: disable=broad-exception-caught
        return []


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _runtime_context(env: dict[str, str]) -> dict[str, Any]:
    """Return the Jules execution context gate expected by dashboard clients."""
    context = (env.get("JULES_CONTEXT") or "").strip().strip("\"'")
    if context not in ("[LOCAL]", "[REMOTE_VM]", "[SCHOOL_COMPUTE]"):
        context = "[SCHOOL_COMPUTE]"
    return {
        "hostname": socket.gethostname(),
        "execution_context": context,
        "quant_allowed": context in ("[LOCAL]", "[REMOTE_VM]"),
    }


def _fleet_status() -> dict[str, Any]:
    """Summarise Jules fleet state from persisted JSON files."""
    cot = _read_json(_COT_LEDGER)
    launch = _read_json(_LAUNCH_STATE)
    watch = _read_json(_WATCH_STATE)

    launched = 0
    completed = 0
    pending = 0
    failed = 0
    in_progress = 0
    all_complete = False

    if cot and isinstance(cot, dict):
        launched = cot.get("selected_count", 0)
        completed = cot.get("completed_count", 0)
        pending = cot.get("pending_count", 0)
        all_complete = bool(cot.get("all_complete", False))

    if launch and isinstance(launch, dict):
        rows = launch.get("launched", [])
        if isinstance(rows, list):
            for row in rows:
                s = (row.get("remote_status") or "").lower()
                if s in ("failed",):
                    failed += 1
                elif s in ("in progress", "planning", "awaiting plan", "awaiting user"):
                    in_progress += 1

    sessions_total = 0
    if watch and isinstance(watch, dict):
        sessions_total = watch.get("sessions_checked", 0)

    return {
        "launched": launched,
        "completed": completed,
        "pending": pending,
        "failed": failed,
        "in_progress": in_progress,
        "all_complete": all_complete,
        "sessions_tracked": sessions_total,
    }


def _vm_info(env: dict[str, str]) -> dict[str, Any]:
    """Build status for all known cloud VMs from .env variables."""
    vms: list[dict] = []

    # GCP worker
    gcp_ip = env.get("GCE_WORKER_IP", "")
    gcp_name = env.get("GCE_WORKER_NAME", "jules-offload-worker")
    gcp_project = env.get("GCE_WORKER_PROJECT", "tibin-terminal-2026")
    gcp_zone = env.get("GCE_WORKER_ZONE", "us-central1-a")
    gcp_reachable = _tcp_reachable(gcp_ip) if gcp_ip else False
    vms.append({
        "provider": "GCP",
        "name": gcp_name,
        "ip": gcp_ip or "unknown",
        "project": gcp_project,
        "zone": gcp_zone,
        "reachable": gcp_reachable,
        "status": "online" if gcp_reachable else ("provisioned" if gcp_ip else "not_configured"),
    })

    # Azure workers — scan env for AZURE_WORKER_* keys
    for key, val in env.items():
        if key.startswith("AZURE_WORKER_") and val:
            raw_name = key.replace("AZURE_WORKER_", "").replace("_", "-").lower()
            az_reachable = _tcp_reachable(val)
            vms.append({
                "provider": "Azure",
                "name": raw_name,
                "ip": val,
                "project": "jules-offload-rg",
                "zone": "eastus",
                "reachable": az_reachable,
                "status": "online" if az_reachable else "provisioning",
            })

    return {"vms": vms, "total": len(vms), "online": sum(1 for v in vms if v["reachable"])}


def _codebase_analysis_summary() -> dict[str, Any]:
    """Return a privacy-safe codebase snapshot for dashboard clients."""
    analysis = analyze_codebase(max_files=1800, include_files=False)
    summary = analysis.get("summary", {}) if isinstance(analysis, dict) else {}
    frontend = analysis.get("frontend", {}) if isinstance(analysis, dict) else {}
    integrations = analysis.get("integrations", []) if isinstance(analysis, dict) else []
    findings = analysis.get("findings", []) if isinstance(analysis, dict) else []
    return {
        "status": analysis.get("status", "unknown") if isinstance(analysis, dict) else "unknown",
        "root_name": analysis.get("root", {}).get("name", "") if isinstance(analysis, dict) else "",
        "summary": {
            "file_count": summary.get("file_count", 0),
            "route_count": summary.get("route_count", 0),
            "module_count": summary.get("module_count", 0),
            "test_count": summary.get("test_count", 0),
            "frontend_dependency_count": summary.get("frontend_dependency_count", 0),
            "integration_ready_count": summary.get("integration_ready_count", 0),
            "truncated": bool(summary.get("truncated", False)),
        },
        "frontend": {
            "present": bool(frontend.get("present", False)),
            "package_name": frontend.get("package_name", ""),
            "app_entry_present": bool(frontend.get("app_entry_present", False)),
        },
        "integrations": [
            {
                "id": row.get("id", ""),
                "label": row.get("label", ""),
                "ready": bool(row.get("ready", False)),
                "tone": row.get("tone", "info"),
            }
            for row in integrations[:8]
            if isinstance(row, dict)
        ],
        "findings": [
            {
                "tone": row.get("tone", "info"),
                "title": row.get("title", ""),
                "detail": row.get("detail", ""),
            }
            for row in findings[:4]
            if isinstance(row, dict)
        ],
    }


def _alliance_status_summary(
    gemini_cli: dict[str, Any] | None = None,
    antigravity_cli: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a privacy-safe Jules plus Google terminal-agent alliance summary."""
    state = _read_json(_ALLIANCE_STATE)
    if not isinstance(state, dict):
        return {
            "status": "missing",
            "summary": "No persisted alliance switchboard state found.",
            "mode": "unconfigured",
            "creator": "jules",
            "implementer": "unassigned",
            "implementer_selection": "",
            "ready_to_execute_alliance": False,
            "simultaneous_two_agent_mode": False,
            "safe_to_launch_live_work": False,
            "required_blocker_count": 1,
            "partial_caveat_count": 0,
            "gate_pass_count": 0,
            "gate_total_count": 0,
            "packet_count": 0,
            "workflow_step_count": 0,
            "state_age_s": None,
            "lanes": [],
        }

    completion = state.get("completion_assessment", {})
    roles = state.get("roles", {})
    active_implementer = state.get("active_implementer", {})
    readiness = state.get("readiness", {})
    gates = state.get("gates", [])
    workflow = state.get("workflow", [])
    packets = state.get("packets", {})
    packet_paths = packets.get("packet_paths", {}) if isinstance(packets, dict) else {}
    required_blockers = completion.get("required_blockers", []) if isinstance(completion, dict) else []
    partial_caveats = completion.get("partial_caveats", []) if isinstance(completion, dict) else []
    gate_rows = gates if isinstance(gates, list) else []
    gate_total = len(gate_rows)
    gate_pass = sum(1 for row in gate_rows if isinstance(row, dict) and row.get("status") == "pass")
    gate_required_blockers = [
        row for row in gate_rows
        if isinstance(row, dict)
        and row.get("required")
        and row.get("status") not in ("pass", "ok", "ready")
    ]

    state_age_s: int | None = None
    generated_at = state.get("generated_at_utc")
    if isinstance(generated_at, str) and generated_at:
        try:
            generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            state_age_s = max(0, int((datetime.now(timezone.utc) - generated).total_seconds()))
        except ValueError:
            state_age_s = None

    live_rows = {
        "legacy_gemini_cli": gemini_cli,
        "antigravity_cli": antigravity_cli,
    }

    def readiness_row(name: str, label: str, role: str) -> dict[str, Any]:
        row = readiness.get(name, {}) if isinstance(readiness, dict) else {}
        live = live_rows.get(name)
        if isinstance(live, dict):
            ready = bool(live.get("ready"))
            installed = bool(live.get("installed", ready))
            blocker = live.get("last_blocker") or live.get("likely_blocker") or live.get("blocker") or ""
        else:
            ready = bool(row.get("ready") or row.get("available"))
            installed = bool(row.get("installed", ready))
            blocker = row.get("likely_blocker") or row.get("blocker") or ""
        return {
            "id": name,
            "label": label,
            "role": role,
            "ready": ready,
            "installed": installed,
            "blocker": blocker,
            "status": "ready" if ready else ("installed" if installed else "blocked"),
        }

    implementer_name = active_implementer.get("name") if isinstance(active_implementer, dict) else ""
    return {
        "status": state.get("status", "unknown"),
        "summary": state.get("summary", ""),
        "mode": roles.get("mode", "") if isinstance(roles, dict) else "",
        "creator": roles.get("creator", {}).get("agent", "jules") if isinstance(roles, dict) else "jules",
        "implementer": implementer_name or "unassigned",
        "implementer_selection": active_implementer.get("selection", "") if isinstance(active_implementer, dict) else "",
        "ready_to_execute_alliance": bool(completion.get("ready_to_execute_alliance")) if isinstance(completion, dict) else False,
        "simultaneous_two_agent_mode": bool(completion.get("simultaneous_two_agent_mode")) if isinstance(completion, dict) else False,
        "safe_to_launch_live_work": bool(completion.get("safe_to_launch_live_work")) if isinstance(completion, dict) else False,
        "required_blocker_count": len(required_blockers) + len(gate_required_blockers),
        "partial_caveat_count": len(partial_caveats),
        "gate_pass_count": gate_pass,
        "gate_total_count": gate_total,
        "packet_count": len(packet_paths) if isinstance(packet_paths, dict) else 0,
        "workflow_step_count": len(workflow) if isinstance(workflow, list) else 0,
        "state_age_s": state_age_s,
        "lanes": [
            readiness_row("jules", "Jules", "creator"),
            readiness_row("antigravity_cli", "Antigravity", "google terminal agent"),
            readiness_row("legacy_gemini_cli", "Gemini CLI", "legacy visibility"),
            readiness_row("akc", "AKC Context", "checkpoint"),
            readiness_row("collaboration_proof_state", "Proof State", "evidence"),
        ],
    }


def _cloud_sync_status_summary() -> dict[str, Any]:
    """Return a compact cloud sync snapshot for unauthenticated dashboard use."""
    status = get_cloud_sync_status(timeout_s=3)
    repo = status.get("repo", {}) if isinstance(status, dict) else {}
    git = status.get("git", {}) if isinstance(status, dict) else {}
    github = status.get("github", {}) if isinstance(status, dict) else {}
    return {
        "status": status.get("status", "unknown") if isinstance(status, dict) else "unknown",
        "state": status.get("state", "unknown") if isinstance(status, dict) else "unknown",
        "branch": repo.get("branch", ""),
        "upstream": repo.get("upstream", ""),
        "remote_host": repo.get("remote_host", ""),
        "remote_label": repo.get("remote_label", ""),
        "ahead": git.get("ahead", 0),
        "behind": git.get("behind", 0),
        "dirty_count": git.get("dirty_count", 0),
        "staged_count": git.get("staged_count", 0),
        "unstaged_count": git.get("unstaged_count", 0),
        "untracked_count": git.get("untracked_count", 0),
        "github_authenticated": bool(github.get("authenticated", False)),
        "github_account": github.get("account", ""),
        "publish_ready": bool(status.get("publish_ready", False)) if isinstance(status, dict) else False,
        "synced": bool(status.get("synced", False)) if isinstance(status, dict) else False,
        "blockers": status.get("blockers", [])[:6] if isinstance(status.get("blockers", []), list) else [],
        "warnings": status.get("warnings", [])[:4] if isinstance(status.get("warnings", []), list) else [],
        "cache_age_s": status.get("cache_age_s", 0) if isinstance(status, dict) else 0,
    }


_dashboard_status_cache: dict = {}
# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_dashboard_status(bridge_start_utc: datetime | None = None) -> dict[str, Any]:
    """Aggregate full dashboard status. Never raises."""
    try:
        cache_ttl = int(os.environ.get('DASHBOARD_CACHE_TTL_S', '5'))
        now_ts = time.time()

        if _dashboard_status_cache:
            ts, cached_res = _dashboard_status_cache.get('last', (0, {}))
            if now_ts - ts < cache_ttl:
                cached_res['cache_age_s'] = int(now_ts - ts)
                return cached_res

        now = datetime.now(timezone.utc)
        uptime_s = int((now - bridge_start_utc).total_seconds()) if bridge_start_utc else 0

        env = _env_vars()
        runtime = _runtime_context(env)
        pressure = detect_resource_pressure()
        fleet = _fleet_status()
        gemini_cli = gemini_status_snapshot()
        antigravity_cli = antigravity_status_snapshot()
        cloud = _vm_info(env)
        logs = _tail_log()
        repo_context = build_repo_context_guard(include_repos=False)
        codebase_analysis = _codebase_analysis_summary()
        alliance = _alliance_status_summary(gemini_cli=gemini_cli, antigravity_cli=antigravity_cli)
        cloud_sync = _cloud_sync_status_summary()
        repo_summary = dict(repo_context.get("summary", {}))
        repo_summary.pop("sample_repos", None)

        ngrok_url = ""
        # Try to extract ngrok URL from recent logs
        for line in reversed(logs):
            if "ngrok-free.dev" in line or "ngrok.io" in line:
                match = re.search(r"https://[a-z0-9\-]+\.ngrok[a-z.\-]*/", line)
                if match:
                    ngrok_url = match.group(0).rstrip("/")
                    break

        result = {
            "ok": True,
            "timestamp": now.isoformat(),
            "cache_age_s": 0,
            **runtime,
            "bridge": {
                "status": "running",
                "uptime_s": uptime_s,
                "uptime_human": _fmt_uptime(uptime_s),
                "ngrok_url": ngrok_url,
                "local_url": "http://127.0.0.1:5000",
            },
            "resource_pressure": {
                "status": pressure.get("status", "unknown"),
                "cpu_percent": pressure.get("cpu_percent"),
                "memory_percent": pressure.get("memory_percent"),
                "maxed_out": pressure.get("maxed_out", False),
                "reasons": pressure.get("reasons", []),
            },
            "cloud": cloud,
            "jules_fleet": fleet,
            "gemini_cli": gemini_cli,
            "antigravity_cli": antigravity_cli,
            "alliance": alliance,
            "cloud_sync": cloud_sync,
            "codebase_analysis": codebase_analysis,
            "repo_context": {
                "status": repo_context.get("status", "unknown"),
                "summary": repo_summary,
                "collisions": repo_context.get("collisions", [])[:12],
                "guardrails": repo_context.get("guardrails", []),
                "cache_age_s": repo_context.get("cache_age_s", 0),
            },
            "recent_logs": logs,
            "model_loop": {
                "mode": "vm_browser",
                "requires_provider_api_keys": False,
            },
            "env_keys_present": [
                k for k in [
                    "BROWSER_MODEL_LOOP_URL",
                    "GCE_WORKER_IP",
                    "GMAIL_USER",
                    "GEMINI_CLI_PATH",
                    "ANTIGRAVITY_CLI_PATH",
                    "AGY_CLI_PATH",
                ]
                if env.get(k)
            ],
        }
        _dashboard_status_cache['last'] = (now_ts, result)
        return result
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {"ok": False, "error": str(exc)}


def _fmt_uptime(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"
