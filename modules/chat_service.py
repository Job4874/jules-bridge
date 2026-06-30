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


def _sanitize_detail(detail: Any, env: Mapping[str, str]) -> str:
    text = str(detail)
    keys_to_redact = ["GEMINI_API_KEY", "OPENROUTER_API_KEY"]
    for key_name in keys_to_redact:
        secret = _env_value(env, key_name)
        if secret:
            text = text.replace(secret, "[redacted]")

    # Also redact from plural keys
    plural_keys = _env_value(env, "OPENROUTER_API_KEYS")
    if plural_keys:
        for secret in plural_keys.split(","):
            secret = secret.strip()
            if secret:
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


def _get_openrouter_keys(env: Mapping[str, str]) -> list[str]:
    keys = []
    main_key = _env_value(env, "OPENROUTER_API_KEY")
    if main_key:
        keys.append(main_key)
    plural_keys = _env_value(env, "OPENROUTER_API_KEYS")
    if plural_keys:
        for k in plural_keys.split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def test_chat_providers(
    env: Mapping[str, str] | None = None,
    requests_client: Any | None = None,
    clock: Any = time.monotonic,
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
                    "detail": _sanitize_detail(response.text, env_map),
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

    or_keys = _get_openrouter_keys(env_map)
    if or_keys:
        start = clock()
        # Try keys in order for health check too, or just report first successful?
        # Requirement: "Try candidates in order, redact every candidate in error details"
        or_ok = False
        last_error: dict[str, Any] = {}
        for key in or_keys:
            try:
                if client is None:
                    raise RuntimeError("requests package unavailable")
                response = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={"model": _OPENROUTER_FAST, "messages": [{"role": "user", "content": "Say OK"}]},
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=20,
                )
                elapsed = _elapsed_ms(start, clock)
                if response.status_code == 200:
                    results["openrouter"] = {"status": "ok", "model": _OPENROUTER_FAST, "ms": elapsed}
                    or_ok = True
                    break
                else:
                    last_error = {
                        "status": "error",
                        "code": response.status_code,
                        "detail": _sanitize_detail(response.text, env_map),
                        "ms": elapsed,
                    }
            except Exception as exc:  # pylint: disable=broad-exception-caught
                last_error = {
                    "status": "exception",
                    "detail": _sanitize_detail(exc, env_map),
                    "ms": _elapsed_ms(start, clock),
                }

        if not or_ok:
            results["openrouter"] = last_error
    else:
        results["openrouter"] = {"status": "no_key", "detail": "OPENROUTER_API_KEY(S) not set"}

    # VM Fallback health
    is_vm_test = getattr(requests_client, "_is_vm_test", False)
    # In production, we don't pass anything, and client is the requests module.
    if is_vm_test or (requests_client is None and client is not None and str(type(client)) == "<class 'module'>"):
        start = clock()
        try:
            from modules import vm_relay  # pylint: disable=import-outside-toplevel
            vm_status = vm_relay.get_vm_status()
            if vm_status.get("online"):
                results["vm"] = {"status": "ok", "model": "jules-worker", "ms": _elapsed_ms(start, clock)}
            else:
                results["vm"] = {"status": "offline"}
        except Exception:  # pylint: disable=broad-exception-caught
            results["vm"] = {"status": "error"}

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
    """Send a chat request through Gemini with OpenRouter fallback."""
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
        or_keys = _get_openrouter_keys(env_map)
        for key in or_keys:
            try:
                if client is None:
                    raise RuntimeError("requests package unavailable")
                model = _openrouter_model(model_alias)
                response = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={"model": model, "messages": _openrouter_messages(message, image_base64, history, system)},
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=45,
                )
                if response.status_code == 200:
                    response_text = _extract_openrouter_text(response.json())
                    model_used = f"openrouter/{model}"
                    break
                else:
                    errors.append(
                        f"OpenRouter {response.status_code}: {_sanitize_detail(response.text, env_map)[:200]}"
                    )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors.append(f"OpenRouter exception: {_sanitize_detail(exc, env_map)}")

    if not response_text:
        # VM Chat Fallback
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
                            # The VM agent logs task text in 'task' field.
                            # Our marker is in the task text.
                            if marker in task_entry.get("task", "") and task_entry.get("status") == "done":
                                response_text = task_entry.get("result")
                                model_used = "vm/jules-worker"
                                break
                        if response_text:
                            break
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors.append(f"VM fallback exception: {str(exc)[:100]}")

    elapsed_ms = _elapsed_ms(start, clock)
    if response_text:
        return ChatResult(response=response_text, model_used=model_used, elapsed_ms=elapsed_ms)

    return ChatResult(
        response=(
            "I'm offline right now - no API keys responded. "
            "Check GEMINI_API_KEY or OPENROUTER_API_KEY in .env."
        ),
        model_used="none",
        elapsed_ms=elapsed_ms,
        errors=errors,
    )
