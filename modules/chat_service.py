"""Chat provider routing for the Jules Bridge chat endpoints.

This module hides provider selection, request payload construction, fallback
handling, and secret redaction behind two small public functions.

Public interface:
    test_chat_providers() -> ChatHealthResult
    chat(message, model_alias, system_prompt, image_base64, history) -> ChatResult
"""

from __future__ import annotations

import os
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
                vm_relay.send_task_to_vm(task_payload, task_type="chat", context=system)

                # Brief polling
                for _ in range(5):
                    time.sleep(2)
                    status = vm_relay.get_vm_status()
                    recent = status.get("recent", [])
                    for task_entry in reversed(recent):
                        if marker in task_entry.get("task", "") and task_entry.get("status") == "done":
                            response_text = task_entry.get("result")
                            model_used = "vm/jules-worker"
                            break
                    if response_text:
                        break
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
