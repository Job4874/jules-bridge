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
    for key_name in ("GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        secret = _env_value(env, key_name)
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


def test_chat_providers(
    env: Mapping[str, str] | None = None,
    requests_client: Any | None = None,
    clock: Any = time.monotonic,
) -> ChatHealthResult:
    """Probe configured chat providers with minimal requests in parallel."""
    from concurrent.futures import ThreadPoolExecutor

    env_map = os.environ if env is None else env
    client = _requests_client(requests_client)

    def _probe_gemini():
        gemini_key = _env_value(env_map, "GEMINI_API_KEY")
        if not gemini_key:
            return {"status": "no_key", "detail": "GEMINI_API_KEY not set"}
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
                body = response.json() if response.text else {}
                if "candidates" in body:
                    return {"status": "ok", "model": _GEMINI_FAST, "ms": elapsed}
                return {
                    "status": "error",
                    "code": 200,
                    "detail": f"Unexpected response shape: {str(body)[:100]}",
                    "ms": elapsed,
                }
            return {
                "status": "error",
                "code": response.status_code,
                "detail": _sanitize_detail(response.text, env_map),
                "ms": elapsed,
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "status": "exception",
                "detail": _sanitize_detail(exc, env_map),
                "ms": _elapsed_ms(start, clock),
            }

    def _probe_openrouter():
        openrouter_key = _env_value(env_map, "OPENROUTER_API_KEY")
        if not openrouter_key:
            return {"status": "no_key", "detail": "OPENROUTER_API_KEY not set"}
        start = clock()
        try:
            if client is None:
                raise RuntimeError("requests package unavailable")
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"model": _OPENROUTER_FAST, "messages": [{"role": "user", "content": "Say OK"}]},
                headers={"Authorization": f"Bearer {openrouter_key}"},
                timeout=20,
            )
            elapsed = _elapsed_ms(start, clock)
            if response.status_code == 200:
                body = response.json() if response.text else {}
                if "choices" in body:
                    return {"status": "ok", "model": _OPENROUTER_FAST, "ms": elapsed}
                return {
                    "status": "error",
                    "code": 200,
                    "detail": f"Unexpected response shape: {str(body)[:100]}",
                    "ms": elapsed,
                }
            return {
                "status": "error",
                "code": response.status_code,
                "detail": _sanitize_detail(response.text, env_map),
                "ms": elapsed,
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "status": "exception",
                "detail": _sanitize_detail(exc, env_map),
                "ms": _elapsed_ms(start, clock),
            }

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_gemini = executor.submit(_probe_gemini)
        f_openrouter = executor.submit(_probe_openrouter)
        results = {
            "gemini": f_gemini.result(),
            "openrouter": f_openrouter.result(),
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
        try:
            openrouter_key = _env_value(env_map, "OPENROUTER_API_KEY")
            if openrouter_key:
                if client is None:
                    raise RuntimeError("requests package unavailable")
                model = _openrouter_model(model_alias)
                response = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={"model": model, "messages": _openrouter_messages(message, image_base64, history, system)},
                    headers={"Authorization": f"Bearer {openrouter_key}"},
                    timeout=45,
                )
                if response.status_code == 200:
                    response_text = _extract_openrouter_text(response.json())
                    model_used = f"openrouter/{model}"
                else:
                    errors.append(
                        f"OpenRouter {response.status_code}: {_sanitize_detail(response.text, env_map)[:200]}"
                    )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"OpenRouter exception: {_sanitize_detail(exc, env_map)}")

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
