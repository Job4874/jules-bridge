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
_OPENROUTER_FAST_FALLBACKS = [
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "openchat/openchat-7b:free",
]
_OPENROUTER_SMART = "deepseek/deepseek-r1:free"
_OPENROUTER_SMART_FALLBACKS = [
    "deepseek/deepseek-chat:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]
_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_VM_CHAT_MODEL = "vm/jules-worker"
_VM_FAILURE_MARKERS = (
    "No LLM available",
    "GEMINI_API_KEY is rate-limited",
    "OpenRouter free models failed",
)
_VM_CHAT_FAILURE_TTL_S = 300
_VM_CHAT_SUCCESS_TTL_S = 300
_LAST_VM_CHAT_FAILURE: dict[str, Any] = {}
_LAST_VM_CHAT_SUCCESS: dict[str, Any] = {}


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


def _openrouter_models(alias: str) -> list[str]:
    if alias == "fast":
        return [_OPENROUTER_FAST] + _OPENROUTER_FAST_FALLBACKS
    return [_OPENROUTER_SMART] + _OPENROUTER_SMART_FALLBACKS


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


def _classify_error(status_code: int, text: str) -> str:
    """Classify provider failure into a standard category string."""
    lower_text = text.lower()
    if status_code in (401, 403):
        return "invalid_key"
    if status_code == 429 or "quota" in lower_text or "rate limit" in lower_text:
        return "quota_limit"
    if status_code == 404 or "model_not_found" in lower_text or "not found" in lower_text:
        return "model_unavailable"
    if status_code >= 500:
        return "transient_error"
    return "other_error"


def _vm_response_is_failure(text: str) -> bool:
    return any(marker in text for marker in _VM_FAILURE_MARKERS)


def _remember_vm_chat_failure(error: str) -> None:
    _LAST_VM_CHAT_FAILURE.clear()
    _LAST_VM_CHAT_FAILURE.update({"error": error, "ts": time.time()})


def _remember_vm_chat_success() -> None:
    _LAST_VM_CHAT_SUCCESS.clear()
    _LAST_VM_CHAT_SUCCESS.update({"ts": time.time()})


def _clear_vm_chat_failure() -> None:
    _LAST_VM_CHAT_FAILURE.clear()


def _latest_local_vm_chat_failure() -> str | None:
    if not _LAST_VM_CHAT_FAILURE:
        return None
    ts = float(_LAST_VM_CHAT_FAILURE.get("ts") or 0.0)
    if time.time() - ts > _VM_CHAT_FAILURE_TTL_S:
        _LAST_VM_CHAT_FAILURE.clear()
        return None
    error = str(_LAST_VM_CHAT_FAILURE.get("error") or "").strip()
    return error or None


def _latest_local_vm_chat_success() -> bool:
    if not _LAST_VM_CHAT_SUCCESS:
        return False
    ts = float(_LAST_VM_CHAT_SUCCESS.get("ts") or 0.0)
    if time.time() - ts > _VM_CHAT_SUCCESS_TTL_S:
        _LAST_VM_CHAT_SUCCESS.clear()
        return False
    return True


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


def _latest_vm_chat_result(status: Mapping[str, Any]) -> tuple[str, str] | None:
    recent = status.get("recent", [])
    if not isinstance(recent, Sequence) or isinstance(recent, (str, bytes)):
        return None
    for entry in reversed(recent):
        if not isinstance(entry, Mapping):
            continue
        task_text = str(entry.get("task") or "")
        if "chat-fallback-" not in task_text:
            continue
        result = str(entry.get("result") or "").strip()
        if not result:
            continue
        return task_text, result
    return None


def _vm_worker_status(
    vm_get_status: Any | None = None,
    vm_send_task: Any | None = None,
    sleep_func: Any = time.sleep,
    probe_chat: bool = True,
    task_attempts: int = 2,
    poll_attempts: int = 3,
    poll_interval_s: float = 1.5,
) -> dict[str, Any]:
    _, status_fn = _default_vm_functions() if vm_get_status is None else (None, vm_get_status)
    status = status_fn()
    if not isinstance(status, Mapping):
        return {"status": "error", "detail": "VM status returned a non-object response"}
    if not status.get("online"):
        return {"status": "offline", "detail": "VM worker offline"}

    local_success = _latest_local_vm_chat_success()
    if probe_chat:
        response, error = _vm_chat_fallback(
            message="Health probe: reply exactly OK.",
            system_prompt="You are a health probe. Reply exactly OK.",
            vm_send_task=vm_send_task,
            vm_get_status=status_fn,
            sleep_func=sleep_func,
            task_attempts=task_attempts,
            poll_attempts=poll_attempts,
            poll_interval_s=poll_interval_s,
        )
        if response:
            return {
                "status": "ok",
                "model": _VM_CHAT_MODEL,
                "detail": "VM chat probe succeeded",
                "tasks_completed": status.get("tasks_completed"),
            }
        if local_success:
            return {
                "status": "ok",
                "model": _VM_CHAT_MODEL,
                "detail": f"VM chat recently succeeded; latest probe failed: {error or 'VM chat probe failed'}",
                "tasks_completed": status.get("tasks_completed"),
            }
        return {
            "status": "error",
            "model": _VM_CHAT_MODEL,
            "detail": error or "VM chat probe failed",
            "tasks_completed": status.get("tasks_completed"),
        }

    if local_success:
        return {
            "status": "ok",
            "model": _VM_CHAT_MODEL,
            "detail": "VM worker online; VM chat recently succeeded",
            "tasks_completed": status.get("tasks_completed"),
        }

    local_failure = _latest_local_vm_chat_failure()
    if local_failure:
        return {
            "status": "error",
            "model": _VM_CHAT_MODEL,
            "detail": f"VM worker online but latest local chat fallback failed: {local_failure}",
            "tasks_completed": status.get("tasks_completed"),
        }

    latest_chat = _latest_vm_chat_result(status)
    if latest_chat is not None:
        _, result = latest_chat
        if _vm_response_is_failure(result):
            return {
                "status": "error",
                "model": _VM_CHAT_MODEL,
                "detail": "VM worker online but latest chat fallback reported provider quota/key failure",
                "tasks_completed": status.get("tasks_completed"),
            }

    return {
        "status": "ok",
        "model": _VM_CHAT_MODEL,
        "detail": "VM worker online; latest chat fallback is not failing",
        "tasks_completed": status.get("tasks_completed"),
    }


def _vm_chat_fallback(
    message: str,
    system_prompt: str,
    vm_send_task: Any | None = None,
    vm_get_status: Any | None = None,
    sleep_func: Any = time.sleep,
    task_attempts: int = 2,
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
        error = "VM fallback unavailable: worker offline"
        _remember_vm_chat_failure(error)
        return None, error

    last_error = "VM fallback did not return a response"
    task_attempt_count = max(1, int(task_attempts or 1))
    attempts = max(1, int(poll_attempts or 1))

    for task_attempt_index in range(task_attempt_count):
        marker = f"chat-fallback-{uuid.uuid4().hex[:12]}"
        queued = send_fn(f"[{marker}] {message}", task_type="chat", context=system_prompt)
        if isinstance(queued, Mapping) and queued.get("ok") is False:
            last_error = f"VM fallback enqueue failed: {str(queued.get('error', 'unknown'))[:120]}"
            continue

        found_terminal_result = False
        for index in range(attempts):
            poll_status = status_fn()
            recent = poll_status.get("recent", []) if isinstance(poll_status, Mapping) else []
            if isinstance(recent, Sequence) and not isinstance(recent, (str, bytes)):
                for entry in reversed(recent):
                    if not isinstance(entry, Mapping):
                        continue
                    if marker not in str(entry.get("task", "")) or entry.get("status") != "done":
                        continue
                    found_terminal_result = True
                    result = str(entry.get("result") or "").strip()
                    if result:
                        if _vm_response_is_failure(result):
                            last_error = "VM fallback provider unavailable: worker reported no LLM available"
                            break
                        _remember_vm_chat_success()
                        _clear_vm_chat_failure()
                        return result, None
                    last_error = "VM fallback completed without a response"
                    break
            if found_terminal_result:
                break
            if index < attempts - 1:
                sleep_func(max(0.0, float(poll_interval_s or 0.0)))

        if not found_terminal_result:
            last_error = "VM fallback timed out waiting for a completed chat task"
        if task_attempt_index < task_attempt_count - 1:
            sleep_func(max(0.0, float(poll_interval_s or 0.0)))

    _remember_vm_chat_failure(last_error)
    return None, last_error


def test_chat_providers(
    env: Mapping[str, str] | None = None,
    requests_client: Any | None = None,
    clock: Any = time.monotonic,
    vm_send_task: Any | None = None,
    vm_get_status: Any | None = None,
    enable_vm_fallback: bool = True,
    probe_vm_chat: bool = True,
    sleep_func: Any = time.sleep,
    vm_task_attempts: int = 2,
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
                    "error_type": _classify_error(response.status_code, response.text),
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
        # Health probe uses 'fast' model alias
        models = _openrouter_models("fast")
        success = False
        for model in models:
            for openrouter_key in openrouter_keys:
                try:
                    if client is None:
                        raise RuntimeError("requests package unavailable")
                    response = client.post(
                        _OPENROUTER_API_URL,
                        json={"model": model, "messages": [{"role": "user", "content": "Say OK"}]},
                        headers={"Authorization": f"Bearer {openrouter_key}"},
                        timeout=20,
                    )
                    elapsed = _elapsed_ms(start, clock)
                    if response.status_code == 200:
                        last_result = {"status": "ok", "model": model, "ms": elapsed}
                        success = True
                        break
                    last_result = {
                        "status": "error",
                        "error_type": _classify_error(response.status_code, response.text),
                        "code": response.status_code,
                        "detail": (
                            f"HTTP {response.status_code} for {model}: "
                            f"{_sanitize_detail(response.text, env_map)}"
                        ),
                        "ms": elapsed,
                    }
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    last_result = {
                        "status": "exception",
                        "detail": f"{model}: {_sanitize_detail(exc, env_map)}",
                        "ms": _elapsed_ms(start, clock),
                    }
            if success:
                break
        results["openrouter"] = last_result
    else:
        results["openrouter"] = {"status": "no_key", "detail": "OPENROUTER_API_KEY(S) not set"}

    if _should_use_vm(enable_vm_fallback, requests_client, vm_send_task, vm_get_status):
        start = clock()
        try:
            vm_result = _vm_worker_status(
                vm_get_status=vm_get_status,
                vm_send_task=vm_send_task,
                sleep_func=sleep_func,
                probe_chat=probe_vm_chat,
                task_attempts=vm_task_attempts,
            )
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
    vm_task_attempts: int = 2,
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
                etype = _classify_error(response.status_code, response.text)
                errors.append(f"Gemini {response.status_code} [{etype}]: {_sanitize_detail(response.text, env_map)[:200]}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        errors.append(f"Gemini exception: {_sanitize_detail(exc, env_map)}")

    if not response_text:
        try:
            openrouter_keys = _openrouter_keys(env_map)
            if openrouter_keys:
                if client is None:
                    raise RuntimeError("requests package unavailable")
                models = _openrouter_models(model_alias)
                for model in models:
                    success = False
                    for openrouter_key in openrouter_keys:
                        response = client.post(
                            _OPENROUTER_API_URL,
                            json={
                                "model": model,
                                "messages": _openrouter_messages(message, image_base64, history, system),
                            },
                            headers={"Authorization": f"Bearer {openrouter_key}"},
                            timeout=45,
                        )
                        if response.status_code == 200:
                            response_text = _extract_openrouter_text(response.json())
                            model_used = f"openrouter/{model}"
                            success = True
                            break
                        etype = _classify_error(response.status_code, response.text)
                        errors.append(
                            f"OpenRouter {response.status_code} [{etype}] for {model}: "
                            f"{_sanitize_detail(response.text, env_map)[:200]}"
                        )
                    if success:
                        break
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
                task_attempts=vm_task_attempts,
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
