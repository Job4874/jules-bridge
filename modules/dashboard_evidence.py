"""Durable redacted evidence store for dashboard command execution."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent
_DASHBOARD_ROOT = _ROOT / ".jules-dashboard"
_EVIDENCE_DIR = _DASHBOARD_ROOT / "evidence"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "bearer",
    "token",
    "cookie",
    "set-cookie",
    "secret",
    "password",
    "private_key",
    "api_key",
    "access_token",
    "refresh_token",
)

_SENSITIVE_STRING_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]+", re.IGNORECASE),
    re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]*?-----END OPENSSH PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----[\s\S]*?-----END PGP PRIVATE KEY BLOCK-----", re.IGNORECASE),
    re.compile(
        r"(?i)(authorization|bearer|token|secret|password|api[_-]?key|cookie|access_token|refresh_token)\s*[:=]\s*\S+",
    ),
)

_REDACTED = "[REDACTED]"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_evidence_id() -> str:
    return f"ev-{uuid.uuid4().hex[:12]}"


def _evidence_dir() -> Path:
    return _EVIDENCE_DIR


def configure_evidence_root(root: Path | None) -> None:
    """Point the evidence store at an alternate dashboard root (tests only)."""
    global _DASHBOARD_ROOT, _EVIDENCE_DIR  # pylint: disable=global-statement
    base = root or (_ROOT / ".jules-dashboard")
    _DASHBOARD_ROOT = base
    _EVIDENCE_DIR = base / "evidence"


def reset_evidence_root() -> None:
    configure_evidence_root(None)


def _ensure_dirs() -> None:
    _evidence_dir().mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_dirs()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _evidence_path(evidence_id: str) -> Path:
    safe_id = str(evidence_id or "").strip()
    if not safe_id.startswith("ev-"):
        raise ValueError("invalid_evidence_id")
    return _evidence_dir() / f"{safe_id}.json"


def redact_safe_payload(value: Any) -> Any:
    """Redact sensitive keys and secret-bearing strings from evidence payloads."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower().replace("-", "_")
            if any(part.replace("-", "_") in key_lower for part in _SENSITIVE_KEY_PARTS):
                redacted[key] = _REDACTED
            else:
                redacted[key] = redact_safe_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_safe_payload(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in _SENSITIVE_STRING_PATTERNS:
            redacted = pattern.sub(_REDACTED, redacted)
        if "BEGIN OPENSSH PRIVATE KEY" in redacted.upper():
            redacted = _REDACTED
        if "BEGIN PGP PRIVATE KEY BLOCK" in redacted.upper():
            redacted = _REDACTED
        return redacted
    return value


def compute_result_hash(safe_payload: dict[str, Any]) -> str:
    """Return a deterministic sha256 hash for a redacted evidence payload."""
    canonical = json.dumps(safe_payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _build_safe_payload(
    *,
    command: dict[str, Any],
    result: dict[str, Any] | None,
    status: str,
    summary: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "summary": summary,
        "route": str(command.get("route") or ""),
        "type": str(command.get("type") or ""),
    }
    block_reason = command.get("blockReason")
    if block_reason:
        payload["blockReason"] = str(block_reason)
    if isinstance(result, dict) and result:
        payload["result"] = result
    return redact_safe_payload(payload)


def evidence_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    """Return a projection-safe evidence summary without raw safePayload."""
    return {
        "evidenceId": str(evidence.get("evidenceId") or ""),
        "commandId": str(evidence.get("commandId") or ""),
        "workflowId": str(evidence.get("workflowId") or ""),
        "traceId": str(evidence.get("traceId") or ""),
        "type": str(evidence.get("type") or ""),
        "status": str(evidence.get("status") or ""),
        "summary": str(evidence.get("summary") or ""),
        "createdAt": str(evidence.get("createdAt") or ""),
        "redactionStatus": str(evidence.get("redactionStatus") or "redacted"),
    }


def write_command_evidence(
    command: dict[str, Any],
    *,
    result: dict[str, Any] | None = None,
    status: str,
    summary: str,
) -> dict[str, Any]:
    """Write durable redacted evidence for a command execution."""
    safe_payload = _build_safe_payload(
        command=command,
        result=result if isinstance(result, dict) else {},
        status=status,
        summary=summary,
    )
    evidence_id = _new_evidence_id()
    created_at = _now_iso()
    evidence = {
        "evidenceId": evidence_id,
        "commandId": str(command.get("commandId") or ""),
        "workflowId": str(command.get("workflowId") or ""),
        "traceId": str(command.get("traceId") or ""),
        "type": str(command.get("type") or ""),
        "status": status,
        "createdAt": created_at,
        "summary": summary,
        "route": str(command.get("route") or ""),
        "resultHash": compute_result_hash(safe_payload if isinstance(safe_payload, dict) else {}),
        "redactionStatus": "redacted",
        "safePayload": safe_payload if isinstance(safe_payload, dict) else {},
    }
    _write_json(_evidence_path(evidence_id), evidence)
    return evidence


def _load_evidence_rows(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit or 50), 200))
    directory = _evidence_dir()
    if not directory.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in directory.glob("ev-*.json"):
        data = _read_json(path)
        if data:
            rows.append(data)
    rows.sort(key=lambda item: item.get("createdAt") or "", reverse=True)
    return rows[:limit]


def list_evidence(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit or 20), 200))
    rows = _load_evidence_rows(limit=limit)
    return {
        "ok": True,
        "evidence": [evidence_summary(row) for row in rows],
        "count": len(rows),
    }


def get_evidence(evidence_id: str) -> dict[str, Any]:
    try:
        path = _evidence_path(evidence_id)
    except ValueError:
        return {"ok": False, "error": "evidence_not_found", "evidenceId": evidence_id}
    data = _read_json(path)
    if not data:
        return {"ok": False, "error": "evidence_not_found", "evidenceId": evidence_id}
    return {
        "ok": True,
        "evidence": evidence_summary(data),
        "resultHash": data.get("resultHash"),
        "safePayload": redact_safe_payload(data.get("safePayload") if isinstance(data.get("safePayload"), dict) else {}),
    }


def list_latest_evidence_summaries(limit: int = 10) -> list[dict[str, Any]]:
    return [evidence_summary(row) for row in _load_evidence_rows(limit=limit)]
