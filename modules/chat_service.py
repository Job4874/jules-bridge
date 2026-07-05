"""Chat provider routing for the Jules Bridge chat endpoints.

This module hides provider selection, request payload construction, fallback
handling, and secret redaction behind two small public functions.

Public interface:
    test_chat_providers() -> ChatHealthResult
    chat(message, model_alias, system_prompt, image_base64, history) -> ChatResult
"""

from __future__ import annotations

import os
import json
import time
import uuid
from typing import Any, Mapping, Sequence


class ChatHealthResult(dict):
    """Keys: healthy, providers."""


class ChatResult(dict):
    """Keys: response, model_used, elapsed_ms, errors."""


_VM_FAILURE_MARKERS = (
    "No LLM available",
    "Browser model loop failed",
    "No browser model loop configured",
    "GEMINI_API_KEY is rate-limited",
    "OpenRouter free models failed",
)
_DEFAULT_VM_CHAT_TIMEOUT_S = 30.0
_DEFAULT_VM_CHAT_POLL_INTERVAL_S = 2.0
_CODEBASE_CONTEXT_KEYWORDS = (
    "codebase",
    "code base",
    "local repo",
    "local repository",
    "analyze your own code",
    "analyze my code",
)


def _default_system_prompt() -> str:
    return (
        "You are Jules - a powerful AI engineering agent built on Jules Bridge. "
        "You are direct, honest, and focused on shipping production-grade software. "
        "You have access to cloud VMs (GCP jules-offload-worker, Azure workers), "
        "a local Flask bridge at port 5000, and a fleet of Jules AI workers. "
        "When shown a screenshot, describe what you see and suggest concrete next actions. "
        "Be concise but complete. Never refuse to help with technical tasks."
    )


def _requests_client(client: Any | None = None) -> Any | None:
    if client is not None:
        return client
    try:
        import requests  # pylint: disable=import-outside-toplevel
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    return requests


def _elapsed_ms(start: float, clock: Any) -> int:
    return int((clock() - start) * 1000)


def _float_env(
    env: Mapping[str, str] | None,
    key: str,
    default: float,
    min_value: float,
    max_value: float,
) -> float:
    """Read a bounded float from supplied env or process env."""
    source = env if env is not None else os.environ
    try:
        value = float(source.get(key, default))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, value))


def _latest_vm_chat_result(vm_status: Mapping[str, Any]) -> str:
    """Return the most recent completed VM chat result, if the status exposes one."""
    recent = vm_status.get("recent", [])
    if not isinstance(recent, Sequence) or isinstance(recent, (str, bytes)):
        return ""

    for task_entry in reversed(recent):
        if not isinstance(task_entry, Mapping):
            continue
        task = str(task_entry.get("task", ""))
        if "chat-fallback-" not in task or task_entry.get("status") != "done":
            continue
        return str(task_entry.get("result", ""))
    return ""


def _vm_failure_detail(result: str) -> str:
    """Return a bounded failure detail when a VM chat result is provider exhaustion."""
    if not result:
        return ""
    if any(marker in result for marker in _VM_FAILURE_MARKERS):
        return result[:240]
    return ""


def _should_attach_codebase_context(message: str) -> bool:
    text = str(message or "").lower()
    return any(keyword in text for keyword in _CODEBASE_CONTEXT_KEYWORDS)


def _codebase_context_block() -> str:
    """Return a compact local codebase snapshot for VM prompts."""
    try:
        from modules.codebase_analyzer import analyze_codebase  # pylint: disable=import-outside-toplevel

        analysis = analyze_codebase(max_files=1200, include_files=False)
        if not analysis.get("ok"):
            return ""
        compact = {
            "status": analysis.get("status"),
            "summary": analysis.get("summary", {}),
            "routes": {
                "count": analysis.get("routes", {}).get("count", 0),
                "items": analysis.get("routes", {}).get("items", [])[:30],
            },
            "modules": analysis.get("modules", {}),
            "tests": analysis.get("tests", {}),
            "frontend": analysis.get("frontend", {}),
            "integrations": analysis.get("integrations", []),
            "findings": analysis.get("findings", [])[:8],
            "handoff": analysis.get("handoff", {}),
        }
        return json.dumps(compact, ensure_ascii=True, separators=(",", ":"))[:14000]
    except Exception:  # pylint: disable=broad-exception-caught
        return ""


def test_chat_providers(
    env: Mapping[str, str] | None = None,
    requests_client: Any | None = None,
    clock: Any = time.monotonic,
) -> ChatHealthResult:
    """Probe configured chat providers with minimal requests."""
    client = _requests_client(requests_client)
    results: dict[str, dict[str, Any]] = {}

    # VM Fallback health
    is_vm_test = getattr(requests_client, "_is_vm_test", False)
    # In production, we don't pass anything, and client is the requests module.
    if is_vm_test or (requests_client is None and client is not None and str(type(client)) == "<class 'module'>"):
        start = clock()
        try:
            from modules import vm_relay  # pylint: disable=import-outside-toplevel
            vm_status = vm_relay.get_vm_status()
            if vm_status.get("online"):
                elapsed = _elapsed_ms(start, clock)
                latest_result = _latest_vm_chat_result(vm_status)
                failure_detail = _vm_failure_detail(latest_result)
                if failure_detail:
                    results["vm"] = {
                        "status": "degraded",
                        "model": "jules-worker",
                        "ms": elapsed,
                        "detail": failure_detail,
                    }
                else:
                    results["vm"] = {"status": "ok", "model": "jules-worker", "ms": elapsed}
            else:
                results["vm"] = {"status": "offline"}
        except Exception:  # pylint: disable=broad-exception-caught
            results["vm"] = {"status": "error"}
    else:
        results["vm"] = {"status": "offline"}

    return ChatHealthResult(
        healthy=any(row.get("status") == "ok" for row in results.values()),
        providers=results,
    )


def chat(
    message: str,
    model_alias: str = "fast",
    system_prompt: str = "",
    image_base64: str = "",
    history: Any = None,
    env: Mapping[str, str] | None = None,
    requests_client: Any | None = None,
    clock: Any = time.monotonic,
) -> ChatResult:
    """Send a chat request strictly using the VM fallback language model browser loop."""
    client = _requests_client(requests_client)
    system = system_prompt or _default_system_prompt()
    start = clock()
    response_text: str | None = None
    model_used: str | None = None
    errors: list[str] = []

    # strictly use the language model browser loop that we automated
    is_vm_test = getattr(requests_client, "_is_vm_test", False)
    if is_vm_test or (requests_client is None and client is not None and str(type(client)) == "<class 'module'>"):
        try:
            from modules import vm_relay  # pylint: disable=import-outside-toplevel
            vm_status = vm_relay.get_vm_status()
            if vm_status.get("online"):
                marker = f"chat-fallback-{uuid.uuid4().hex[:8]}"
                task_payload = f"[{marker}] {message}"
                if _should_attach_codebase_context(message):
                    codebase_context = _codebase_context_block()
                    if codebase_context:
                        system = (
                            f"{system}\n\nLOCAL_CODEBASE_ANALYSIS_JSON:\n{codebase_context}\n\n"
                            "When the user asks about the local codebase, base your answer on "
                            "LOCAL_CODEBASE_ANALYSIS_JSON instead of the VM's /home/jules checkout."
                        )
                vm_relay.send_task_to_vm(task_payload, task_type="chat", context=system)

                timeout_s = _float_env(env, "VM_CHAT_TIMEOUT_S", _DEFAULT_VM_CHAT_TIMEOUT_S, 1.0, 120.0)
                poll_interval_s = _float_env(
                    env,
                    "VM_CHAT_POLL_INTERVAL_S",
                    _DEFAULT_VM_CHAT_POLL_INTERVAL_S,
                    0.1,
                    10.0,
                )
                attempts = max(1, int(timeout_s / poll_interval_s))
                for _ in range(attempts):
                    time.sleep(poll_interval_s)
                    status = vm_relay.get_vm_status()
                    recent = status.get("recent", [])
                    for task_entry in reversed(recent):
                        if marker in task_entry.get("task", "") and task_entry.get("status") == "done":
                            response_text = task_entry.get("result")
                            model_used = "vm/jules-worker"
                            break
                    if response_text:
                        break
                if not response_text:
                    errors.append(f"VM worker did not finish within {timeout_s:.1f}s")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"VM relay exception: {str(exc)[:100]}")
    else:
        errors.append("VM relay requires requests module (no overrides)")

    elapsed_ms = _elapsed_ms(start, clock)
    if response_text:
        return ChatResult(response=response_text, model_used=model_used, elapsed_ms=elapsed_ms)

    return ChatResult(
        response="I'm offline right now - VM worker did not respond.",
        model_used="none",
        elapsed_ms=elapsed_ms,
        errors=errors,
    )
