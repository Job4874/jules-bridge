"""Dashboard command/workflow store and projection for the Jules control plane."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.cloud_sync import build_cloud_publish_packet, get_cloud_sync_status
from modules.dashboard_module import get_dashboard_status

_ROOT = Path(__file__).parent.parent
_DASHBOARD_ROOT = _ROOT / ".jules-dashboard"
_COMMANDS_DIR = _DASHBOARD_ROOT / "commands"
_WORKFLOWS_DIR = _DASHBOARD_ROOT / "workflows"

_TERMINAL_STATUSES = frozenset({
    "succeeded",
    "failed",
    "blocked",
    "not_implemented",
    "cancelled",
})

_CONTRACT_NAME = "jules_dashboard_projection"
_CONTRACT_VERSION = 1

COMMAND_TYPES = frozenset({
    "button_sweep",
    "break_test",
    "proof_replay",
    "collaboration_proof",
    "publish_preview",
    "chat_send",
    "route_probe",
})

COMMAND_STATUSES = frozenset({
    "admitted",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "cancelled",
    "not_implemented",
})

WORKFLOW_STATUSES = frozenset({
    "ready",
    "running",
    "blocked",
    "succeeded",
    "failed",
    "cancelled",
    "stale",
})

FRONTEND_ONLY_TYPES = frozenset({"button_sweep", "proof_replay"})

SENSITIVE_KEY_PARTS = (
    "authorization",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "cookie",
    "credential",
    "private_key",
    "gnupg",
    "gpg",
)

_TYPE_WORKFLOW_TITLES = {
    "button_sweep": "Button sweep",
    "break_test": "Break test",
    "proof_replay": "Proof replay",
    "collaboration_proof": "Collaboration proof",
    "publish_preview": "Publish preview",
    "chat_send": "Comms send",
    "route_probe": "Route probe",
}


def _store_root() -> Path:
    return _DASHBOARD_ROOT


def _commands_dir() -> Path:
    return _COMMANDS_DIR


def _workflows_dir() -> Path:
    return _WORKFLOWS_DIR


def configure_store_root(root: Path | None) -> None:
    """Point the dashboard store at an alternate root (tests only)."""
    global _DASHBOARD_ROOT, _COMMANDS_DIR, _WORKFLOWS_DIR  # pylint: disable=global-statement
    base = root or (_ROOT / ".jules-dashboard")
    _DASHBOARD_ROOT = base
    _COMMANDS_DIR = base / "commands"
    _WORKFLOWS_DIR = base / "workflows"


def reset_store_root() -> None:
    configure_store_root(None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _ensure_dirs() -> None:
    _commands_dir().mkdir(parents=True, exist_ok=True)
    _workflows_dir().mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_dirs()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def sanitize_projection_value(value: Any) -> Any:
    """Redact secrets, tokens, cookies, and credentials from projection payloads."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower == "image_base64":
                sanitized[key] = "<image_base64 omitted>"
            elif any(part in key_lower for part in SENSITIVE_KEY_PARTS):
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = sanitize_projection_value(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_projection_value(item) for item in value]
    if isinstance(value, str):
        redacted = value
        redacted = re.sub(
            r"(?i)(authorization|token|secret|password|api[_-]?key|cookie)\s*[:=]\s*\S+",
            r"\1=<redacted>",
            redacted,
        )
        redacted = re.sub(r"Bearer\s+[A-Za-z0-9._\-+/=]+", "Bearer <redacted>", redacted)
        return redacted
    return value


def _normalize_command(raw: dict[str, Any]) -> dict[str, Any]:
    command_type = str(raw.get("type") or "").strip()
    status = str(raw.get("status") or "admitted").strip()
    if command_type not in COMMAND_TYPES:
        command_type = "route_probe"
    if status not in COMMAND_STATUSES:
        status = "admitted"
    return {
        "commandId": str(raw.get("commandId") or _new_id("cmd")),
        "workflowId": str(raw.get("workflowId") or _new_id("wf")),
        "traceId": str(raw.get("traceId") or _new_id("trace")),
        "type": command_type,
        "status": status,
        "createdAt": str(raw.get("createdAt") or _now_iso()),
        "updatedAt": str(raw.get("updatedAt") or raw.get("createdAt") or _now_iso()),
        "requestedBy": str(raw.get("requestedBy") or "dashboard"),
        "route": str(raw.get("route") or ""),
        "summary": str(raw.get("summary") or ""),
        "blockReason": raw.get("blockReason"),
        "result": raw.get("result") if isinstance(raw.get("result"), dict) else {},
        "evidenceRefs": raw.get("evidenceRefs") if isinstance(raw.get("evidenceRefs"), list) else [],
    }


def _normalize_workflow(raw: dict[str, Any]) -> dict[str, Any]:
    status = str(raw.get("status") or "ready").strip()
    if status not in WORKFLOW_STATUSES:
        status = "ready"
    command_ids = raw.get("commandIds") if isinstance(raw.get("commandIds"), list) else []
    trace_ids = raw.get("traceIds") if isinstance(raw.get("traceIds"), list) else []
    return {
        "workflowId": str(raw.get("workflowId") or _new_id("wf")),
        "title": str(raw.get("title") or "Dashboard workflow"),
        "status": status,
        "commandIds": [str(item) for item in command_ids],
        "latestCommandId": str(raw.get("latestCommandId") or ""),
        "traceIds": [str(item) for item in trace_ids],
        "summary": str(raw.get("summary") or ""),
        "nextSafeAction": str(raw.get("nextSafeAction") or ""),
        "requiredOperatorAction": raw.get("requiredOperatorAction"),
    }


def _command_path(command_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9._-]", "", command_id)
    return _commands_dir() / f"{safe_id}.json"


def _workflow_path(workflow_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9._-]", "", workflow_id)
    return _workflows_dir() / f"{safe_id}.json"


def _persist_command(command: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_command(command)
    normalized["updatedAt"] = _now_iso()
    _write_json(_command_path(normalized["commandId"]), normalized)
    return normalized


def _persist_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_workflow(workflow)
    _write_json(_workflow_path(normalized["workflowId"]), normalized)
    return normalized


def _load_commands(limit: int = 50) -> list[dict[str, Any]]:
    _ensure_dirs()
    rows: list[dict[str, Any]] = []
    for path in sorted(_commands_dir().glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        data = _read_json(path)
        if data:
            rows.append(_normalize_command(data))
        if len(rows) >= limit:
            break
    rows.sort(key=lambda item: item.get("updatedAt") or "", reverse=True)
    return rows[:limit]


def _load_workflows(limit: int = 50) -> list[dict[str, Any]]:
    _ensure_dirs()
    rows: list[dict[str, Any]] = []
    for path in sorted(_workflows_dir().glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        data = _read_json(path)
        if data:
            rows.append(_normalize_workflow(data))
        if len(rows) >= limit:
            break
    rows.sort(key=lambda item: item.get("summary") or "", reverse=False)
    rows.sort(key=lambda item: item.get("workflowId") or "", reverse=True)
    return rows[:limit]


def _workflow_status_for_command(status: str) -> str:
    mapping = {
        "admitted": "running",
        "running": "running",
        "succeeded": "succeeded",
        "failed": "failed",
        "blocked": "blocked",
        "cancelled": "cancelled",
        "not_implemented": "blocked",
    }
    return mapping.get(status, "running")


def _next_safe_action(command: dict[str, Any]) -> str:
    status = command.get("status")
    if status == "blocked":
        return str(command.get("blockReason") or "Review the blocker and retry when safe.")
    if status == "not_implemented":
        return "Use the dashboard UI path for this control; backend route is not implemented."
    if status == "failed":
        return "Inspect command result and rerun after fixing the bridge dependency."
    if status == "cancelled":
        return "Start a fresh command when the operator lane is ready."
    if status == "succeeded":
        return "Continue with the next safe dashboard control."
    return "Wait for the command lifecycle to finish."


def _touch_workflow(command: dict[str, Any]) -> dict[str, Any]:
    workflow_id = command["workflowId"]
    existing = _read_json(_workflow_path(workflow_id)) or {}
    command_ids = existing.get("commandIds") if isinstance(existing.get("commandIds"), list) else []
    trace_ids = existing.get("traceIds") if isinstance(existing.get("traceIds"), list) else []
    if command["commandId"] not in command_ids:
        command_ids.append(command["commandId"])
    if command["traceId"] not in trace_ids:
        trace_ids.append(command["traceId"])
    workflow = _normalize_workflow({
        "workflowId": workflow_id,
        "title": existing.get("title") or _TYPE_WORKFLOW_TITLES.get(command["type"], "Dashboard workflow"),
        "status": _workflow_status_for_command(command["status"]),
        "commandIds": command_ids,
        "latestCommandId": command["commandId"],
        "traceIds": trace_ids,
        "summary": command.get("summary") or existing.get("summary") or command["type"],
        "nextSafeAction": _next_safe_action(command),
        "requiredOperatorAction": command.get("blockReason") if command["status"] in {"blocked", "not_implemented"} else None,
    })
    return _persist_workflow(workflow)


def _execute_command(command: dict[str, Any], *, bridge_start_utc: datetime | None = None) -> dict[str, Any]:
    """Run command logic and return the command with a terminal (or blocked) status."""
    command = dict(command)
    command_type = command["type"]

    if command_type in FRONTEND_ONLY_TYPES:
        command["status"] = "not_implemented"
        command["blockReason"] = f"{command_type} runs in the dashboard UI; backend stores admission only."
        command["route"] = command.get("route") or "local_preview"
        command["summary"] = command.get("summary") or command["blockReason"]
        return command

    if command_type == "chat_send":
        draft = str((command.get("result") or {}).get("draft") or command.get("summary") or "").strip()
        if not draft:
            command["status"] = "blocked"
            command["blockReason"] = "Press Send blocked because there is no draft content to send."
            command["route"] = "POST /chat"
            command["summary"] = command["blockReason"]
            return command
        command["status"] = "blocked"
        command["blockReason"] = "Comms send remains a protected route; dashboard must call POST /chat with bearer auth."
        command["route"] = "POST /chat"
        command["summary"] = command["blockReason"]
        return command

    try:
        if command_type == "break_test":
            command["route"] = "GET /dashboard/status"
            status = get_dashboard_status(bridge_start_utc=bridge_start_utc)
            command["result"] = sanitize_projection_value({
                "ok": status.get("ok"),
                "contract": status.get("contract"),
                "execution_context": status.get("execution_context"),
                "cloud_sync": status.get("cloud_sync"),
            })
            command["status"] = "succeeded" if status.get("ok") else "failed"
            command["summary"] = command.get("summary") or (
                "Break test status refresh succeeded." if status.get("ok") else "Break test status refresh failed."
            )
            return command

        if command_type == "route_probe":
            route = str(command.get("route") or "GET /ping").strip()
            command["route"] = route
            if route.endswith("/chat") or "publish-packet" in route:
                command["status"] = "blocked"
                command["blockReason"] = f"{route} is protected and cannot be probed from the command store."
                command["summary"] = command["blockReason"]
                return command
            if route.startswith("GET /dashboard/status"):
                status = get_dashboard_status(bridge_start_utc=bridge_start_utc)
                command["result"] = sanitize_projection_value({"ok": status.get("ok"), "contract": status.get("contract")})
                command["status"] = "succeeded" if status.get("ok") else "failed"
                command["summary"] = command.get("summary") or f"Route probe {route} completed."
                return command
            command["status"] = "not_implemented"
            command["blockReason"] = f"{route} is not executed by the dashboard command store."
            command["summary"] = command["blockReason"]
            return command

        if command_type == "publish_preview":
            command["route"] = "GET /sync/publish-preview"
            preview = build_cloud_publish_packet(
                root="",
                objective=str((command.get("result") or {}).get("objective") or ""),
                timeout_s=4,
                use_cache=False,
                write_packet=False,
                output_dir="",
            )
            preview = sanitize_projection_value(preview)
            command["result"] = preview
            blocked = preview.get("status") == "error" or preview.get("blocked")
            command["status"] = "blocked" if blocked else "succeeded"
            if blocked:
                command["blockReason"] = str(preview.get("summary") or preview.get("error") or "Publish preview blocked.")
            command["summary"] = command.get("summary") or str(preview.get("summary") or "Publish preview built.")
            return command

        if command_type == "collaboration_proof":
            from modules import build_collaboration_proof  # pylint: disable=import-outside-toplevel

            command["route"] = "POST /proof/collaboration"
            proof = build_collaboration_proof(
                include_live_checks=False,
                run_gemini_smoke=False,
                timeout_s=12,
                write_state=False,
                state_path="",
            )
            proof = sanitize_projection_value(proof)
            command["result"] = proof
            command["status"] = "failed" if proof.get("error") else "succeeded"
            command["summary"] = command.get("summary") or str(proof.get("summary") or "Collaboration proof evaluated.")
            if proof.get("error"):
                command["blockReason"] = str(proof.get("error"))
            return command
    except Exception as exc:  # pylint: disable=broad-exception-caught
        command["status"] = "failed"
        command["blockReason"] = str(exc)
        command["summary"] = f"Command execution failed: {exc}"
        command["result"] = {"error": str(exc)}

    return command


def list_commands(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 200))
    commands = [_normalize_command(row) for row in _load_commands(limit)]
    return {
        "ok": True,
        "commands": sanitize_projection_value(commands),
        "count": len(commands),
    }


def get_command(command_id: str) -> dict[str, Any]:
    data = _read_json(_command_path(command_id))
    if not data:
        return {"ok": False, "error": "command_not_found", "commandId": command_id}
    return {"ok": True, "command": sanitize_projection_value(_normalize_command(data))}


def update_command_status(
    command_id: str,
    status: str,
    *,
    result: dict[str, Any] | None = None,
    block_reason: str | None = None,
    summary: str | None = None,
    evidence_refs: list[Any] | None = None,
    route: str | None = None,
) -> dict[str, Any]:
    """Update a persisted command status and mirror the workflow lane."""
    data = _read_json(_command_path(command_id))
    if not data:
        return {"ok": False, "error": "command_not_found", "commandId": command_id}
    command = _normalize_command(data)
    if status not in COMMAND_STATUSES:
        return {"ok": False, "error": "unsupported_command_status", "commandId": command_id}
    command["status"] = status
    if result is not None:
        command["result"] = result if isinstance(result, dict) else {}
    if block_reason is not None:
        command["blockReason"] = block_reason
    if summary is not None:
        command["summary"] = summary
    if evidence_refs is not None:
        command["evidenceRefs"] = evidence_refs if isinstance(evidence_refs, list) else []
    if route is not None:
        command["route"] = route
    command = _persist_command(command)
    workflow = _touch_workflow(command)
    return {
        "ok": True,
        "command": sanitize_projection_value(command),
        "workflow": sanitize_projection_value(workflow),
    }


def get_command_status_counts(*, limit: int = 200) -> dict[str, int]:
    """Return aggregate command counts for worker status and projection."""
    commands = _load_commands(limit=limit)
    return {
        "pendingCount": sum(1 for command in commands if command.get("status") == "admitted"),
        "runningCount": sum(1 for command in commands if command.get("status") == "running"),
        "terminalCount": sum(1 for command in commands if command.get("status") in _TERMINAL_STATUSES),
    }


def list_pending_commands(limit: int = 20) -> list[dict[str, Any]]:
    """Return admitted commands oldest-first for worker pickup."""
    limit = max(1, min(int(limit or 20), 200))
    pending = [
        command
        for command in _load_commands(limit=200)
        if command.get("status") == "admitted"
    ]
    pending.sort(key=lambda item: item.get("createdAt") or "")
    return pending[:limit]


def process_command(command_id: str, *, bridge_start_utc: datetime | None = None) -> dict[str, Any]:
    """Advance one command through running to a terminal status."""
    data = _read_json(_command_path(command_id))
    if not data:
        return {"ok": False, "error": "command_not_found", "commandId": command_id}
    command = _normalize_command(data)
    if command["status"] == "cancelled":
        return {"ok": False, "error": "command_cancelled", "commandId": command_id}
    if command["status"] not in {"admitted", "running"}:
        return {
            "ok": True,
            "command": sanitize_projection_value(command),
            "skipped": True,
            "commandId": command_id,
        }

    command["status"] = "running"
    command = _persist_command(command)
    _touch_workflow(command)

    command = _execute_command(command, bridge_start_utc=bridge_start_utc)
    command = _persist_command(command)
    workflow = _touch_workflow(command)
    return {
        "ok": True,
        "command": sanitize_projection_value(command),
        "workflow": sanitize_projection_value(workflow),
    }


def process_pending_commands(*, bridge_start_utc: datetime | None = None, limit: int = 5) -> dict[str, Any]:
    """Process admitted commands synchronously (worker tick or tests)."""
    processed: list[dict[str, Any]] = []
    skipped = 0
    succeeded = 0
    failed = 0
    blocked = 0
    not_implemented = 0

    for command in list_pending_commands(limit=limit):
        result = process_command(command["commandId"], bridge_start_utc=bridge_start_utc)
        if not result.get("ok") or result.get("skipped"):
            skipped += 1
            continue
        terminal = result["command"]
        processed.append(terminal)
        status = str(terminal.get("status") or "")
        if status == "succeeded":
            succeeded += 1
        elif status == "failed":
            failed += 1
        elif status == "blocked":
            blocked += 1
        elif status == "not_implemented":
            not_implemented += 1

    return {
        "ok": True,
        "processed": sanitize_projection_value(processed),
        "count": len(processed),
        "processedCount": len(processed),
        "skipped": skipped,
        "succeeded": succeeded,
        "failed": failed,
        "blocked": blocked,
        "not_implemented": not_implemented,
    }


def admit_command(payload: dict[str, Any] | None, *, bridge_start_utc: datetime | None = None) -> dict[str, Any]:
    del bridge_start_utc  # admission is async; worker executes after persist
    body = payload if isinstance(payload, dict) else {}
    command_type = str(body.get("type") or "").strip()
    if command_type not in COMMAND_TYPES:
        return {
            "ok": False,
            "error": "unsupported_command_type",
            "supported_types": sorted(COMMAND_TYPES),
        }

    command = _normalize_command({
        "commandId": body.get("commandId") or _new_id("cmd"),
        "workflowId": body.get("workflowId") or _new_id("wf"),
        "traceId": body.get("traceId") or _new_id("trace"),
        "type": command_type,
        "status": "admitted",
        "requestedBy": body.get("requestedBy") or "dashboard",
        "route": body.get("route") or "",
        "summary": body.get("summary") or "",
        "blockReason": body.get("blockReason"),
        "result": body.get("result") if isinstance(body.get("result"), dict) else {},
        "evidenceRefs": body.get("evidenceRefs") if isinstance(body.get("evidenceRefs"), list) else [],
    })
    command = _persist_command(command)
    workflow = _touch_workflow(command)
    return {
        "ok": True,
        "command": sanitize_projection_value(command),
        "workflow": sanitize_projection_value(workflow),
    }


def cancel_command(command_id: str) -> dict[str, Any]:
    data = _read_json(_command_path(command_id))
    if not data:
        return {"ok": False, "error": "command_not_found", "commandId": command_id}
    command = _normalize_command(data)
    if command["status"] in {"succeeded", "failed", "cancelled"}:
        return {"ok": False, "error": "command_not_cancellable", "command": sanitize_projection_value(command)}
    command["status"] = "cancelled"
    command["summary"] = command.get("summary") or "Command cancelled by operator."
    command["updatedAt"] = _now_iso()
    command = _persist_command(command)
    workflow = _touch_workflow(command)
    return {
        "ok": True,
        "command": sanitize_projection_value(command),
        "workflow": sanitize_projection_value(workflow),
    }


def list_workflows(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 200))
    workflows = [_normalize_workflow(row) for row in _load_workflows(limit)]
    return {
        "ok": True,
        "workflows": sanitize_projection_value(workflows),
        "count": len(workflows),
    }


def get_workflow(workflow_id: str) -> dict[str, Any]:
    data = _read_json(_workflow_path(workflow_id))
    if not data:
        return {"ok": False, "error": "workflow_not_found", "workflowId": workflow_id}
    return {"ok": True, "workflow": sanitize_projection_value(_normalize_workflow(data))}


def _collect_blockers(
    *,
    bridge_health: dict[str, Any],
    cloud_sync: dict[str, Any],
    commands: list[dict[str, Any]],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if not bridge_health.get("ok"):
        blockers.append({
            "id": "bridge_health",
            "label": "Bridge health",
            "detail": "Dashboard status is offline or contract drift detected.",
            "nextSafeAction": "Refresh /dashboard/status before running protected controls.",
        })
    sync_status = str(cloud_sync.get("status") or cloud_sync.get("sync_status") or "")
    if sync_status and sync_status not in {"synced", "clean", "ok"}:
        blockers.append({
            "id": "cloud_sync",
            "label": "Cloud sync",
            "detail": str(cloud_sync.get("summary") or cloud_sync.get("detail") or sync_status),
            "nextSafeAction": "Run GET /sync/publish-preview locally before any publish attempt.",
        })
    for command in commands[:5]:
        if command.get("status") in {"blocked", "failed", "not_implemented"}:
            blockers.append({
                "id": f"command:{command.get('commandId')}",
                "label": f"{command.get('type')} command",
                "detail": str(command.get("blockReason") or command.get("summary") or command.get("status")),
                "nextSafeAction": _next_safe_action(command),
            })
    return blockers[:8]


def get_dashboard_projection(*, bridge_start_utc: datetime | None = None, limit: int = 20) -> dict[str, Any]:
    from modules.dashboard_command_worker import worker_status  # pylint: disable=import-outside-toplevel

    bridge_health = get_dashboard_status(bridge_start_utc=bridge_start_utc)
    cache_age_s = int(bridge_health.get("cache_age_s") or 0)
    cloud_sync = sanitize_projection_value(bridge_health.get("cloud_sync") or get_cloud_sync_status(root="", timeout_s=4))
    commands = _load_commands(limit)
    workflows = _load_workflows(limit)
    collaboration = sanitize_projection_value(bridge_health.get("alliance") or {})
    blockers = _collect_blockers(
        bridge_health=bridge_health,
        cloud_sync=cloud_sync if isinstance(cloud_sync, dict) else {},
        commands=commands,
    )
    latest_workflow = workflows[0] if workflows else None
    projection = {
        "ok": True,
        "contract": {
            "name": _CONTRACT_NAME,
            "version": _CONTRACT_VERSION,
            "generated_at_utc": _now_iso(),
        },
        "bridgeHealth": sanitize_projection_value({
            "ok": bridge_health.get("ok"),
            "contract": bridge_health.get("contract"),
            "execution_context": bridge_health.get("execution_context"),
            "online": bridge_health.get("online"),
        }),
        "commands": sanitize_projection_value(commands),
        "workflows": sanitize_projection_value(workflows),
        "dashboardCache": {
            "cache_age_s": cache_age_s,
            "transport": (bridge_health.get("contract") or {}).get("transport", "poll"),
        },
        "cloudSyncPreview": cloud_sync if isinstance(cloud_sync, dict) else {},
        "collaborationProof": collaboration if isinstance(collaboration, dict) else {},
        "blockers": blockers,
        "nextSafeAction": (
            blockers[0]["nextSafeAction"]
            if blockers
            else (latest_workflow or {}).get("nextSafeAction") or "Continue with the next safe dashboard control."
        ),
        "currentWorkflowId": (latest_workflow or {}).get("workflowId"),
        "commandWorker": worker_status(),
    }
    return sanitize_projection_value(projection)
