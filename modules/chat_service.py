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

_GEMINI_FAST = "gemini-2.0-flash"
_GEMINI_SMART = "gemini-2.5-pro"
_OPENROUTER_FAST = "google/gemma-3-27b-it:free"
_OPENROUTER_SMART = "deepseek/deepseek-r1:free"
_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_VM_CHAT_MODEL = "vm/jules-worker"


class ChatHealthResult(dict):
    """Keys: healthy, providers."""


class ChatResult(dict):
    """Keys: response, model_used, elapsed_ms, errors."""


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


def _env_value(env: Mapping[str, str], key: str) -> str:
    return (env.get(key, "") or "").strip()


def _openrouter_keys(env: Mapping[str, str]) -> list[str]:
    keys: list[str] = []
    for value in (_env_value(env, "OPENROUTER_API_KEY"), _env_value(env, "OPENROUTER_API_KEYS")):
        for key in value.split(","):
            candidate = key.strip()
            if candidate and candidate not in keys:
                keys.append(candidate)
    return keys


def _redaction_values(env: Mapping[str, str]) -> list[str]:
    values: list[str] = []
    for value in (_env_value(env, "GEMINI_API_KEY"), *_openrouter_keys(env)):
        if value and value not in values:
            values.append(value)
    return values


def _sanitize_detail(detail: Any, env: Mapping[str, str]) -> str:
    text = str(detail)
    for secret in _redaction_values(env):
        text = text.replace(secret, "[redacted]")
    return text[:300]


def _elapsed_ms(start: float, clock: Any) -> int:
    return int((clock() - start) * 1000)


def _gemini_model(alias: str) -> str:
    return _GEMINI_FAST if alias == "fast" else _GEMINI_SMART


def _openrouter_model(alias: str) -> str:
    return _OPENROUTER_FAST if alias == "fast" else _OPENROUTER_SMART


def _history_messages(history: Any) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if not isinstance(history, Sequence) or isinstance(history, (str, bytes)):
        return messages
    for turn in history:
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant"):
            messages.append({"role": turn["role"], "content": turn.get("content", "")})
    return messages


def _gemini_contents(message: str, image_base64: str, history: Any) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"text": message}]
    if image_base64:
        parts.append({"inline_data": {"mime_type": "image/png", "data": image_base64}})

    if not isinstance(history, Sequence) or isinstance(history, (str, bytes)):
        return [{"role": "user", "parts": parts}]

    contents = []
    for turn in history:
        if not isinstance(turn, dict):
            continue
        role = "user" if turn.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": str(turn.get("content", ""))}]})
    contents.append({"role": "user", "parts": parts})
    return contents


def _openrouter_messages(
    message: str,
    image_base64: str,
    history: Any,
    system_prompt: str,
) -> list[dict[str, Any]]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_history_messages(history))
    if image_base64:
        user_content: str | list[dict[str, Any]] = [
            {"type": "text", "text": message},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
        ]
    else:
        user_content = message
    messages.append({"role": "user", "content": user_content})
    return messages


def _extract_gemini_text(payload: Any) -> str:
    return str(payload["candidates"][0]["content"]["parts"][0]["text"])


def _extract_openrouter_text(payload: Any) -> str:
    return str(payload["choices"][0]["message"]["content"])


def _default_vm_functions() -> tuple[Any, Any]:
    from modules import vm_relay  # pylint: disable=import-outside-toplevel

    return vm_relay.send_task_to_vm, vm_relay.get_vm_status


def _should_use_vm(
    enable_vm_fallback: bool,
    requests_client: Any | None,
    vm_send_task: Any | None,
    vm_get_status: Any | None,
) -> bool:
    if not enable_vm_fallback:
        return False
    return requests_client is None or vm_send_task is not None or vm_get_status is not None


def _vm_worker_status(vm_get_status: Any | None = None) -> dict[str, Any]:
    _, status_fn = _default_vm_functions() if vm_get_status is None else (None, vm_get_status)
    status = status_fn()
    if not isinstance(status, Mapping):
        return {"status": "error", "detail": "VM status returned a non-object response"}
    if status.get("online"):
        return {
            "status": "ok",
            "model": _VM_CHAT_MODEL,
            "detail": "VM worker online; chat fallback available",
            "tasks_completed": status.get("tasks_completed"),
        }
    return {"status": "offline", "detail": "VM worker offline"}


def _vm_chat_fallback(
    message: str,
    system_prompt: str,
    vm_send_task: Any | None = None,
    vm_get_status: Any | None = None,
    sleep_func: Any = time.sleep,
    poll_attempts: int = 6,
    poll_interval_s: float = 2.0,
) -> tuple[str | None, str | None]:
    send_fn, status_fn = (
        _default_vm_functions()
        if vm_send_task is None or vm_get_status is None
        else (vm_send_task, vm_get_status)
    )
    if vm_send_task is not None:
        send_fn = vm_send_task
    if vm_get_status is not None:
        status_fn = vm_get_status

    status = status_fn()
    if not isinstance(status, Mapping) or not status.get("online"):
        return None, "VM fallback unavailable: worker offline"

    marker = f"chat-fallback-{uuid.uuid4().hex[:12]}"
    queued = send_fn(f"[{marker}] {message}", task_type="chat", context=system_prompt)
    if isinstance(queued, Mapping) and queued.get("ok") is False:
        return None, f"VM fallback enqueue failed: {str(queued.get('error', 'unknown'))[:120]}"

    attempts = max(1, int(poll_attempts or 1))
    for index in range(attempts):
        poll_status = status_fn()
        recent = poll_status.get("recent", []) if isinstance(poll_status, Mapping) else []
        if isinstance(recent, Sequence) and not isinstance(recent, (str, bytes)):
            for entry in reversed(recent):
                if not isinstance(entry, Mapping):
                    continue
                if marker in str(entry.get("task", "")) and entry.get("status") == "done":
                    result = str(entry.get("result") or "").strip()
                    if result:
                        return result, None
                    return None, "VM fallback completed without a response"
        if index < attempts - 1:
            sleep_func(max(0.0, float(poll_interval_s or 0.0)))

    return None, "VM fallback timed out waiting for a completed chat task"


def test_chat_providers(
    env: Mapping[str, str] | None = None,
    requests_client: Any | None = None,
    clock: Any = time.monotonic,
    vm_get_status: Any | None = None,
    enable_vm_fallback: bool = True,
) -> ChatHealthResult:
    """Probe configured chat providers with minimal requests."""
    env_map = os.environ if env is None else env
    client = _requests_client(requests_client)
    results: dict[str, dict[str, Any]] = {}

    gemini_key = _env_value(env_map, "GEMINI_API_KEY")
    if gemini_key:
        start = clock()
        try:
            if client is None:
                raise RuntimeError("requests package unavailable")
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{_GEMINI_FAST}:generateContent?key={gemini_key}"
            )
            payload = {"contents": [{"role": "user", "parts": [{"text": "Say OK"}]}]}
            response = client.post(url, json=payload, timeout=15)
            elapsed = _elapsed_ms(start, clock)
            if response.status_code == 200:
                results["gemini"] = {"status": "ok", "model": _GEMINI_FAST, "ms": elapsed}
            else:
                results["gemini"] = {
                    "status": "error",
                    "code": response.status_code,
                    "detail": f"HTTP {response.status_code}: {_sanitize_detail(response.text, env_map)}",
                    "ms": elapsed,
                }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            results["gemini"] = {
                "status": "exception",
                "detail": _sanitize_detail(exc, env_map),
                "ms": _elapsed_ms(start, clock),
            }
    else:
        results["gemini"] = {"status": "no_key", "detail": "GEMINI_API_KEY not set"}

    openrouter_keys = _openrouter_keys(env_map)
    if openrouter_keys:
        start = clock()
        last_result: dict[str, Any] = {}
        for openrouter_key in openrouter_keys:
            try:
                if client is None:
                    raise RuntimeError("requests package unavailable")
                response = client.post(
                    _OPENROUTER_API_URL,
                    json={"model": _OPENROUTER_FAST, "messages": [{"role": "user", "content": "Say OK"}]},
                    headers={"Authorization": f"Bearer {openrouter_key}"},
                    timeout=20,
                )
                elapsed = _elapsed_ms(start, clock)
                if response.status_code == 200:
                    last_result = {"status": "ok", "model": _OPENROUTER_FAST, "ms": elapsed}
                    break
                last_result = {
                    "status": "error",
                    "code": response.status_code,
                    "detail": f"HTTP {response.status_code}: {_sanitize_detail(response.text, env_map)}",
                    "ms": elapsed,
                }
            except Exception as exc:  # pylint: disable=broad-exception-caught
                last_result = {
                    "status": "exception",
                    "detail": _sanitize_detail(exc, env_map),
                    "ms": _elapsed_ms(start, clock),
                }
        results["openrouter"] = last_result
    else:
        results["openrouter"] = {"status": "no_key", "detail": "OPENROUTER_API_KEY(S) not set"}

    if _should_use_vm(enable_vm_fallback, requests_client, None, vm_get_status):
        start = clock()
        try:
            vm_result = _vm_worker_status(vm_get_status=vm_get_status)
            vm_result["ms"] = _elapsed_ms(start, clock)
            results["vm_worker"] = vm_result
        except Exception as exc:  # pylint: disable=broad-exception-caught
            results["vm_worker"] = {
                "status": "exception",
                "detail": str(exc)[:200],
                "ms": _elapsed_ms(start, clock),
            }

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
    vm_send_task: Any | None = None,
    vm_get_status: Any | None = None,
    sleep_func: Any = time.sleep,
    vm_poll_attempts: int = 6,
    vm_poll_interval_s: float = 2.0,
    enable_vm_fallback: bool = True,
) -> ChatResult:
    """Send a chat request through Gemini, OpenRouter, then VM worker fallback."""
    env_map = os.environ if env is None else env
    client = _requests_client(requests_client)
    system = system_prompt or _default_system_prompt()
    start = clock()
    response_text: str | None = None
    model_used: str | None = None
    errors: list[str] = []

    try:
        gemini_key = _env_value(env_map, "GEMINI_API_KEY")
        if gemini_key:
            if client is None:
                raise RuntimeError("requests package unavailable")
            model = _gemini_model(model_alias)
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={gemini_key}"
            )
            payload = {
                "system_instruction": {"parts": [{"text": system}]},
                "contents": _gemini_contents(message, image_base64, history),
            }
            response = client.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                response_text = _extract_gemini_text(response.json())
                model_used = model
            else:
                errors.append(f"Gemini {response.status_code}: {_sanitize_detail(response.text, env_map)[:200]}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        errors.append(f"Gemini exception: {_sanitize_detail(exc, env_map)}")

    if not response_text:
        try:
            openrouter_keys = _openrouter_keys(env_map)
            if openrouter_keys:
                if client is None:
                    raise RuntimeError("requests package unavailable")
                model = _openrouter_model(model_alias)
                for openrouter_key in openrouter_keys:
                    response = client.post(
                        _OPENROUTER_API_URL,
                        json={"model": model, "messages": _openrouter_messages(message, image_base64, history, system)},
                        headers={"Authorization": f"Bearer {openrouter_key}"},
                        timeout=45,
                    )
                    if response.status_code == 200:
                        response_text = _extract_openrouter_text(response.json())
                        model_used = f"openrouter/{model}"
                        break
                    errors.append(
                        f"OpenRouter {response.status_code}: {_sanitize_detail(response.text, env_map)[:200]}"
                    )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"OpenRouter exception: {_sanitize_detail(exc, env_map)}")

    if not response_text and _should_use_vm(enable_vm_fallback, requests_client, vm_send_task, vm_get_status):
        try:
            response_text, vm_error = _vm_chat_fallback(
                message=message,
                system_prompt=system,
                vm_send_task=vm_send_task,
                vm_get_status=vm_get_status,
                sleep_func=sleep_func,
                poll_attempts=vm_poll_attempts,
                poll_interval_s=vm_poll_interval_s,
            )
            if response_text:
                model_used = _VM_CHAT_MODEL
            elif vm_error:
                errors.append(vm_error)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"VM fallback exception: {str(exc)[:120]}")

    elapsed_ms = _elapsed_ms(start, clock)
    if response_text:
        return ChatResult(response=response_text, model_used=model_used, elapsed_ms=elapsed_ms)

    return ChatResult(
        response=(
            "I'm offline right now - no API keys responded. "
            "Check GEMINI_API_KEY, OPENROUTER_API_KEY(S), or the VM worker fallback."
        ),
        model_used="none",
        elapsed_ms=elapsed_ms,
        errors=errors,
    )
