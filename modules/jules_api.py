"""Jules REST API client (v1alpha).

Wraps https://jules.googleapis.com/v1alpha with the local bridge's
never-raises result style so orchestrator code can prefer REST over CLI.

Public interface:
    api_preflight() -> JulesApiResult
    list_sources() -> JulesApiResult
    list_sessions(page_size= int) -> JulesApiResult
    create_session(prompt, source, ...) -> JulesApiResult
    get_session(session_id) -> JulesApiResult
    list_activities(session_id, page_size= int) -> JulesApiResult
    send_message(session_id, prompt) -> JulesApiResult
    approve_plan(session_id) -> JulesApiResult
    sessions_stdout(sessions_payload) -> str
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping
from urllib import error, parse, request

_BASE_URL = "https://jules.googleapis.com/v1alpha"
_API_KEY_HEADER = "X-Goog-Api-Key"
_STATE_LABELS = {
    "STATE_UNSPECIFIED": "unknown",
    "STATE_PENDING": "Planning",
    "STATE_RUNNING": "In Progress",
    "STATE_SUCCEEDED": "Completed",
    "STATE_FAILED": "Failed",
    "STATE_CANCELLED": "Failed",
    "STATE_AWAITING_PLAN_APPROVAL": "Awaiting Plan",
    "STATE_AWAITING_USER_INPUT": "Awaiting User",
}


class JulesApiResult(dict):
    """Keys: ok, status, status_code, payload, error, session_ids, stdout."""


def _env_value(env: Mapping[str, str] | None, key: str) -> str:
    source = os.environ if env is None else env
    return (source.get(key, "") or "").strip()


def api_key(env: Mapping[str, str] | None = None) -> str:
    return _env_value(env, "JULES_API_KEY")


def default_source(env: Mapping[str, str] | None = None) -> str:
    return _env_value(env, "JULES_SOURCE")


def use_rest_api(env: Mapping[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    if not api_key(env_map):
        return False
    flag = _env_value(env_map, "JULES_USE_REST_API").lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return True


def _session_id_from_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "/" in text:
        return text.rsplit("/", 1)[-1]
    return text


def _state_label(session: Mapping[str, Any]) -> str:
    raw = str(session.get("state") or session.get("status") or "").strip()
    if raw in _STATE_LABELS:
        return _STATE_LABELS[raw]
    if raw:
        cleaned = raw.replace("STATE_", "").replace("_", " ").strip()
        return cleaned.title() if cleaned else "In Progress"
    outputs = session.get("outputs")
    if isinstance(outputs, list) and outputs:
        return "Completed"
    return "In Progress"


def sessions_stdout(payload: Mapping[str, Any]) -> str:
    """Render API session list output in CLI-like lines for orchestrator parsers."""
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        return ""
    lines: list[str] = []
    for session in sessions:
        if not isinstance(session, Mapping):
            continue
        session_id = _session_id_from_name(session.get("id") or session.get("name"))
        if not session_id:
            continue
        title = str(session.get("title") or session.get("prompt") or "session")[:80]
        state = _state_label(session)
        lines.append(f"{session_id}  {state}  0s ago  {title}")
    return "\n".join(lines)


def extract_session_ids(payload: Mapping[str, Any]) -> list[str]:
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        single = payload.get("id") or payload.get("name")
        clean = _session_id_from_name(single)
        return [clean] if clean else []
    ids: list[str] = []
    seen: set[str] = set()
    for session in sessions:
        if not isinstance(session, Mapping):
            continue
        clean = _session_id_from_name(session.get("id") or session.get("name"))
        if clean and clean not in seen:
            ids.append(clean)
            seen.add(clean)
    return ids


def _request(
    method: str,
    path: str,
    *,
    query: Mapping[str, Any] | None = None,
    body: Mapping[str, Any] | None = None,
    timeout_s: float = 30,
    env: Mapping[str, str] | None = None,
) -> JulesApiResult:
    key = api_key(env)
    if not key:
        return JulesApiResult(ok=False, status="no_key", error="JULES_API_KEY not set")

    url = f"{_BASE_URL}/{path.lstrip('/')}"
    if query:
        filtered = {k: v for k, v in query.items() if v is not None and v != ""}
        if filtered:
            url = f"{url}?{parse.urlencode(filtered)}"

    headers = {
        _API_KEY_HEADER: key,
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw.strip() else {}
            session_ids = extract_session_ids(payload if isinstance(payload, dict) else {})
            stdout = sessions_stdout(payload) if isinstance(payload, dict) else ""
            return JulesApiResult(
                ok=True,
                status="ok",
                status_code=getattr(resp, "status", 200),
                payload=payload,
                session_ids=session_ids,
                stdout=stdout,
            )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return JulesApiResult(
            ok=False,
            status="http_error",
            status_code=exc.code,
            error=detail[:500],
            payload=_safe_json(detail),
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return JulesApiResult(ok=False, status="error", error=str(exc)[:500])


def _safe_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def api_preflight(env: Mapping[str, str] | None = None, timeout_s: float = 15) -> JulesApiResult:
    key = api_key(env)
    if not key:
        return JulesApiResult(ok=False, status="no_key", error="JULES_API_KEY not set")
    sources = list_sources(env=env, timeout_s=timeout_s)
    if not sources.get("ok"):
        return JulesApiResult(
            ok=False,
            status="auth_failed",
            error=sources.get("error") or "Jules REST API sources probe failed",
            status_code=sources.get("status_code"),
            payload=sources.get("payload") or {},
        )
    return JulesApiResult(
        ok=True,
        status="ok",
        payload={"sources": sources.get("payload", {}), "default_source": default_source(env)},
        stdout=sources.get("stdout", ""),
    )


def list_sources(env: Mapping[str, str] | None = None, timeout_s: float = 30) -> JulesApiResult:
    result = _request("GET", "sources", timeout_s=timeout_s, env=env)
    if not result.get("ok"):
        return result
    payload = result.get("payload") or {}
    sources = payload.get("sources") if isinstance(payload, dict) else []
    lines = []
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, Mapping):
                lines.append(str(source.get("name") or source.get("id") or source))
    result["stdout"] = "\n".join(lines)
    return result


def list_sessions(
    page_size: int = 30,
    page_token: str = "",
    env: Mapping[str, str] | None = None,
    timeout_s: float = 30,
) -> JulesApiResult:
    query: dict[str, Any] = {"pageSize": max(1, min(int(page_size or 30), 100))}
    if page_token:
        query["pageToken"] = page_token
    result = _request("GET", "sessions", query=query, timeout_s=timeout_s, env=env)
    if result.get("ok"):
        payload = result.get("payload") or {}
        result["stdout"] = sessions_stdout(payload if isinstance(payload, dict) else {})
        result["session_ids"] = extract_session_ids(payload if isinstance(payload, dict) else {})
    return result


def create_session(
    prompt: str,
    source: str = "",
    *,
    title: str = "",
    starting_branch: str = "main",
    automation_mode: str = "",
    require_plan_approval: bool = False,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 60,
) -> JulesApiResult:
    clean_prompt = (prompt or "").strip()
    if not clean_prompt:
        return JulesApiResult(ok=False, status="invalid_input", error="prompt is required")

    source_name = (source or default_source(env)).strip()
    if not source_name:
        return JulesApiResult(ok=False, status="invalid_input", error="JULES_SOURCE not configured")

    body: dict[str, Any] = {
        "prompt": clean_prompt,
        "title": (title or clean_prompt[:80]).strip(),
        "sourceContext": {
            "source": source_name,
            "githubRepoContext": {"startingBranch": starting_branch or "main"},
        },
    }
    if automation_mode:
        body["automationMode"] = automation_mode
    if require_plan_approval:
        body["requirePlanApproval"] = True

    result = _request("POST", "sessions", body=body, timeout_s=timeout_s, env=env)
    if result.get("ok"):
        payload = result.get("payload") or {}
        session_id = _session_id_from_name(
            payload.get("id") if isinstance(payload, dict) else ""
        ) or _session_id_from_name(payload.get("name") if isinstance(payload, dict) else "")
        if session_id:
            result["session_ids"] = [session_id]
            result["stdout"] = f"{session_id}  Planning  0s ago  {body['title']}"
    return result


def get_session(session_id: str, env: Mapping[str, str] | None = None, timeout_s: float = 30) -> JulesApiResult:
    clean_id = re.sub(r"[^\d]", "", str(session_id or ""))
    if not clean_id:
        return JulesApiResult(ok=False, status="invalid_input", error="session_id is required")
    result = _request("GET", f"sessions/{clean_id}", timeout_s=timeout_s, env=env)
    if result.get("ok"):
        payload = result.get("payload") or {}
        if isinstance(payload, dict):
            result["session_ids"] = [_session_id_from_name(payload.get("id") or payload.get("name"))]
            result["stdout"] = sessions_stdout({"sessions": [payload]})
    return result


def list_activities(
    session_id: str,
    page_size: int = 30,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 30,
) -> JulesApiResult:
    clean_id = re.sub(r"[^\d]", "", str(session_id or ""))
    if not clean_id:
        return JulesApiResult(ok=False, status="invalid_input", error="session_id is required")
    return _request(
        "GET",
        f"sessions/{clean_id}/activities",
        query={"pageSize": max(1, min(int(page_size or 30), 100))},
        timeout_s=timeout_s,
        env=env,
    )


def send_message(
    session_id: str,
    prompt: str,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 30,
) -> JulesApiResult:
    clean_id = re.sub(r"[^\d]", "", str(session_id or ""))
    clean_prompt = (prompt or "").strip()
    if not clean_id or not clean_prompt:
        return JulesApiResult(ok=False, status="invalid_input", error="session_id and prompt are required")
    return _request(
        "POST",
        f"sessions/{clean_id}:sendMessage",
        body={"prompt": clean_prompt},
        timeout_s=timeout_s,
        env=env,
    )


def approve_plan(session_id: str, env: Mapping[str, str] | None = None, timeout_s: float = 30) -> JulesApiResult:
    clean_id = re.sub(r"[^\d]", "", str(session_id or ""))
    if not clean_id:
        return JulesApiResult(ok=False, status="invalid_input", error="session_id is required")
    return _request("POST", f"sessions/{clean_id}:approvePlan", body={}, timeout_s=timeout_s, env=env)


def pull_session_snapshot(
    session_id: str,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 30,
) -> JulesApiResult:
    """Fetch session details and recent activities as a pull-compatible payload."""
    session = get_session(session_id, env=env, timeout_s=timeout_s)
    if not session.get("ok"):
        return session
    activities = list_activities(session_id, env=env, timeout_s=timeout_s)
    payload = {
        "session": session.get("payload") or {},
        "activities": (activities.get("payload") or {}) if activities.get("ok") else {},
        "activities_error": activities.get("error") if not activities.get("ok") else "",
    }
    clean_id = re.sub(r"[^\d]", "", str(session_id or ""))
    return JulesApiResult(
        ok=True,
        status="pulled",
        payload=payload,
        session_ids=[clean_id] if clean_id else [],
        stdout=json.dumps(payload, indent=2)[:4000],
    )
