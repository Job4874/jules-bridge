"""Jules REST API client.

This module hides Jules REST API request construction, auth headers, response
normalization, and secret redaction behind small typed interfaces.

Public interface:
    jules_api_preflight(...) -> JulesApiResult
    list_sources(...) -> JulesApiResult
    list_sessions(...) -> JulesApiResult
    create_session(...) -> JulesApiResult
    get_session(...) -> JulesApiResult
    list_activities(...) -> JulesApiResult
    send_message(...) -> JulesApiResult
    approve_plan(...) -> JulesApiResult
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


class JulesApiResult(dict):
    """Result from a Jules REST API operation."""


_DEFAULT_BASE_URL = "https://jules.googleapis.com/v1alpha"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_rest_api_requested(env: dict[str, str] | None = None) -> bool:
    """Return whether existing Jules routes should prefer the REST API."""
    env_map = os.environ if env is None else env
    return str(env_map.get("JULES_USE_REST_API", "")).strip().lower() in _TRUE_VALUES


def is_rest_api_enabled(env: dict[str, str] | None = None) -> bool:
    """Return whether REST routing is requested and an API key is present."""
    env_map = os.environ if env is None else env
    return is_rest_api_requested(env_map) and bool(str(env_map.get("JULES_API_KEY", "")).strip())


def jules_api_preflight(
    check_sources: bool = True,
    api_key: str | None = None,
    source: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """Check REST API auth and optional source availability.

    Returns:
        JulesApiResult with ready, likely_blocker, and redacted config metadata.
        Never raises.
    """
    generated_at = _now()
    config = _config(api_key=api_key, source=source, base_url=base_url)
    if not config["api_key"]:
        return JulesApiResult(
            generated_at_utc=generated_at,
            status="error",
            ready=False,
            likely_blocker="missing_api_key",
            api_key_present=False,
            source=config["source"],
            base_url=config["base_url"],
            sources={},
        )
    if not check_sources:
        return JulesApiResult(
            generated_at_utc=generated_at,
            status="ok",
            ready=True,
            likely_blocker="",
            api_key_present=True,
            source=config["source"],
            base_url=config["base_url"],
            sources={"status": "skipped"},
        )

    sources = list_sources(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout_s=timeout_s,
    )
    ready = sources.get("status") == "ok"
    likely_blocker = ""
    if not ready:
        likely_blocker = sources.get("likely_blocker") or "sources_failed"
    elif config["source"]:
        source_names = set(sources.get("source_names", []))
        if config["source"] not in source_names:
            ready = False
            likely_blocker = "source_not_found"

    return JulesApiResult(
        generated_at_utc=generated_at,
        status="ok" if ready else "error",
        ready=ready,
        likely_blocker=likely_blocker,
        api_key_present=True,
        source=config["source"],
        base_url=config["base_url"],
        sources=_preflight_sources_summary(sources),
    )


def list_sources(
    page_size: int = 0,
    page_token: str = "",
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """List Jules sources connected to the account."""
    config = _config(api_key=api_key, base_url=base_url)
    query = _page_query(page_size, page_token)
    return _operation_result(
        operation="sources.list",
        request=_api_request(
            "GET",
            "sources",
            api_key=config["api_key"],
            base_url=config["base_url"],
            query=query,
            timeout_s=timeout_s,
        ),
        item_key="sources",
        id_key="source_names",
    )


def list_sessions(
    page_size: int = 5,
    page_token: str = "",
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """List Jules sessions for the account."""
    config = _config(api_key=api_key, base_url=base_url)
    query = _page_query(page_size, page_token)
    result = _operation_result(
        operation="sessions.list",
        request=_api_request(
            "GET",
            "sessions",
            api_key=config["api_key"],
            base_url=config["base_url"],
            query=query,
            timeout_s=timeout_s,
        ),
        item_key="sessions",
        id_key="session_ids",
    )
    if result.get("status") == "ok":
        result["stdout"] = sessions_to_stdout(result.get("sessions", []))
    return result


def create_session(
    prompt: str,
    title: str = "",
    source: str | None = None,
    starting_branch: str | None = None,
    automation_mode: str = "",
    require_plan_approval: bool = False,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 60,
) -> JulesApiResult:
    """Create a Jules REST API session."""
    config = _config(
        api_key=api_key,
        source=source,
        base_url=base_url,
        starting_branch=starting_branch,
    )
    clean_prompt = str(prompt or "").strip()
    if not clean_prompt:
        return _input_error("prompt is required")
    if not config["source"]:
        return _input_error("JULES_SOURCE or source is required")

    body: dict[str, Any] = {
        "prompt": clean_prompt,
        "sourceContext": {
            "source": config["source"],
        },
    }
    if config["starting_branch"]:
        body["sourceContext"]["githubRepoContext"] = {
            "startingBranch": config["starting_branch"],
        }
    if title:
        body["title"] = title
    if automation_mode:
        body["automationMode"] = automation_mode
    if require_plan_approval:
        body["requirePlanApproval"] = True

    result = _operation_result(
        operation="sessions.create",
        request=_api_request(
            "POST",
            "sessions",
            api_key=config["api_key"],
            base_url=config["base_url"],
            body=body,
            timeout_s=timeout_s,
        ),
    )
    if result.get("status") == "ok":
        session = result.get("payload", {})
        result["session"] = session
        result["session_ids"] = _session_ids_from_items([session])
    return result


def get_session(
    session_id: str,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """Fetch a Jules session snapshot."""
    path = _session_resource_path(session_id)
    if not path:
        return _input_error("session_id is required")
    config = _config(api_key=api_key, base_url=base_url)
    result = _operation_result(
        operation="sessions.get",
        request=_api_request(
            "GET",
            path,
            api_key=config["api_key"],
            base_url=config["base_url"],
            timeout_s=timeout_s,
        ),
    )
    if result.get("status") == "ok":
        session = result.get("payload", {})
        result["session"] = session
        result["session_ids"] = _session_ids_from_items([session])
        result["completed"] = bool(session.get("outputs"))
        result["stdout"] = json.dumps(session, ensure_ascii=True, indent=2)
    return result


def list_activities(
    session_id: str,
    page_size: int = 30,
    page_token: str = "",
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """List activities for one Jules session."""
    path = _session_resource_path(session_id)
    if not path:
        return _input_error("session_id is required")
    config = _config(api_key=api_key, base_url=base_url)
    return _operation_result(
        operation="sessions.activities.list",
        request=_api_request(
            "GET",
            f"{path}/activities",
            api_key=config["api_key"],
            base_url=config["base_url"],
            query=_page_query(page_size, page_token),
            timeout_s=timeout_s,
        ),
        item_key="activities",
        id_key="activity_ids",
    )


def send_message(
    session_id: str,
    prompt: str,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """Send a message to an existing Jules session."""
    path = _session_resource_path(session_id)
    clean_prompt = str(prompt or "").strip()
    if not path:
        return _input_error("session_id is required")
    if not clean_prompt:
        return _input_error("prompt is required")
    config = _config(api_key=api_key, base_url=base_url)
    return _operation_result(
        operation="sessions.sendMessage",
        request=_api_request(
            "POST",
            f"{path}:sendMessage",
            api_key=config["api_key"],
            base_url=config["base_url"],
            body={"prompt": clean_prompt},
            timeout_s=timeout_s,
        ),
    )


def approve_plan(
    session_id: str,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: int = 30,
) -> JulesApiResult:
    """Approve the latest plan for a Jules session."""
    path = _session_resource_path(session_id)
    if not path:
        return _input_error("session_id is required")
    config = _config(api_key=api_key, base_url=base_url)
    return _operation_result(
        operation="sessions.approvePlan",
        request=_api_request(
            "POST",
            f"{path}:approvePlan",
            api_key=config["api_key"],
            base_url=config["base_url"],
            body={},
            timeout_s=timeout_s,
        ),
    )


def sessions_to_stdout(sessions: list[dict]) -> str:
    """Format REST sessions into CLI-like lines for existing status parsers."""
    lines = []
    for session in sessions or []:
        session_id = _session_id_from_item(session)
        title = str(session.get("title") or session.get("name") or "Jules session")
        status = str(
            session.get("status")
            or session.get("state")
            or session.get("lifecycleState")
            or ("Completed" if session.get("outputs") else "unknown")
        )
        lines.append(f" {session_id} # {title} {status}".rstrip())
    return "\n".join(lines) + ("\n" if lines else "")


def _api_request(
    method: str,
    path: str,
    api_key: str,
    base_url: str,
    body: dict | None = None,
    query: dict | None = None,
    timeout_s: int = 30,
) -> dict:
    if not api_key:
        return {
            "ok": False,
            "http_status": None,
            "payload": {},
            "error": "JULES_API_KEY is required",
            "likely_blocker": "missing_api_key",
        }
    url = _url(base_url, path, query=query)
    data = None
    headers = {
        "X-Goog-Api-Key": api_key,
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=max(1, int(timeout_s or 30))) as response:
            text = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= int(response.status) < 300,
                "http_status": int(response.status),
                "payload": _parse_json(text),
                "error": "",
                "likely_blocker": "",
                "url": _redact(url, api_key),
            }
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "http_status": int(exc.code),
            "payload": _parse_json(text),
            "error": _redact(f"HTTP {exc.code}: {text or exc.reason}", api_key),
            "likely_blocker": _http_blocker(int(exc.code)),
            "url": _redact(url, api_key),
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "http_status": None,
            "payload": {},
            "error": _redact(str(exc.reason), api_key),
            "likely_blocker": "network_error",
            "url": _redact(url, api_key),
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return {
            "ok": False,
            "http_status": None,
            "payload": {},
            "error": _redact(str(exc), api_key),
            "likely_blocker": "request_error",
            "url": _redact(url, api_key),
        }


def _operation_result(
    operation: str,
    request: dict,
    item_key: str = "",
    id_key: str = "",
) -> JulesApiResult:
    payload = request.get("payload", {})
    result = JulesApiResult(
        generated_at_utc=_now(),
        operation=operation,
        status="ok" if request.get("ok") else "error",
        http_status=request.get("http_status"),
        api_key_present=True,
        error="" if request.get("ok") else request.get("error", ""),
        likely_blocker="" if request.get("ok") else request.get("likely_blocker", "request_failed"),
        payload=payload,
        url=request.get("url", ""),
    )
    if item_key:
        items = payload.get(item_key, []) if isinstance(payload, dict) else []
        result[item_key] = items
        result["nextPageToken"] = payload.get("nextPageToken", "") if isinstance(payload, dict) else ""
        if id_key:
            result[id_key] = _ids_from_items(items)
    return result


def _config(
    api_key: str | None = None,
    source: str | None = None,
    base_url: str | None = None,
    starting_branch: str | None = None,
) -> dict[str, str]:
    resolved_api_key = os.environ.get("JULES_API_KEY", "") if api_key is None else api_key
    resolved_source = os.environ.get("JULES_SOURCE", "") if source is None else source
    resolved_base_url = os.environ.get("JULES_API_BASE_URL", "") if base_url is None else base_url
    resolved_starting_branch = (
        os.environ.get("JULES_STARTING_BRANCH", "") if starting_branch is None else starting_branch
    )
    return {
        "api_key": str(resolved_api_key or "").strip(),
        "source": str(resolved_source or "").strip(),
        "base_url": str(resolved_base_url or _DEFAULT_BASE_URL).strip().rstrip("/"),
        "starting_branch": str(resolved_starting_branch or "").strip(),
    }


def _page_query(page_size: int = 0, page_token: str = "") -> dict[str, str]:
    query: dict[str, str] = {}
    if page_size:
        query["pageSize"] = str(max(1, int(page_size)))
    if page_token:
        query["pageToken"] = page_token
    return query


def _url(base_url: str, path: str, query: dict | None = None) -> str:
    clean_url = str(base_url or _DEFAULT_BASE_URL).rstrip("/")
    clean_path = str(path or "").lstrip("/")
    url = f"{clean_url}/{clean_path}"
    filtered_query = {key: value for key, value in (query or {}).items() if value not in ("", None)}
    if filtered_query:
        url = f"{url}?{urllib.parse.urlencode(filtered_query)}"
    return url


def _parse_json(text: str) -> dict:
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    return payload if isinstance(payload, dict) else {"data": payload}


def _http_blocker(status_code: int) -> str:
    if status_code in (401, 403):
        return "auth_failed"
    if status_code == 404:
        return "resource_not_found"
    if status_code == 429:
        return "rate_limited"
    if 500 <= status_code:
        return "server_error"
    return "request_failed"


def _input_error(message: str) -> JulesApiResult:
    return JulesApiResult(
        generated_at_utc=_now(),
        status="error",
        http_status=None,
        api_key_present=bool(os.environ.get("JULES_API_KEY", "").strip()),
        error=message,
        likely_blocker="invalid_input",
        payload={},
    )


def _preflight_sources_summary(sources: dict) -> dict:
    """Return a bounded source-list summary suitable for durable state files."""
    source_names = list(sources.get("source_names", []) or [])
    return {
        "generated_at_utc": sources.get("generated_at_utc", ""),
        "operation": sources.get("operation", "sources.list"),
        "status": sources.get("status", ""),
        "http_status": sources.get("http_status"),
        "api_key_present": bool(sources.get("api_key_present")),
        "error": sources.get("error", ""),
        "likely_blocker": sources.get("likely_blocker", ""),
        "source_count": len(source_names),
        "source_names": source_names,
        "next_page_token": sources.get("next_page_token", ""),
    }


def _ids_from_items(items: list[dict]) -> list[str]:
    if not items:
        return []
    if any("githubRepo" in item for item in items):
        return [str(item.get("name") or item.get("id") or "") for item in items if item.get("name") or item.get("id")]
    return _session_ids_from_items(items)


def _session_ids_from_items(items: list[dict]) -> list[str]:
    ids = []
    for item in items or []:
        session_id = _session_id_from_item(item)
        if session_id and session_id not in ids:
            ids.append(session_id)
    return ids


def _session_id_from_item(item: dict) -> str:
    raw = str(item.get("id") or "").strip()
    if raw:
        return raw
    name = str(item.get("name") or "").strip()
    if name.startswith("sessions/"):
        return name.rsplit("/", 1)[-1]
    return name


def _session_resource_path(session_id: str) -> str:
    clean = str(session_id or "").strip().strip("/")
    if not clean:
        return ""
    if clean.startswith("sessions/"):
        return clean
    return "sessions/" + urllib.parse.quote(clean, safe="")


def _redact(text: str, api_key: str) -> str:
    output = str(text or "")
    if api_key:
        output = output.replace(api_key, "[REDACTED_API_KEY]")
    return output


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
