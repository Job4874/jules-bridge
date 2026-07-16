"""Antigravity SDK agent integration for Jules Bridge.

Wraps the ``google-antigravity`` Python SDK so Flask routes can spin up
full Antigravity agents (streaming, custom tools, MCP, policies) through
the bridge's synchronous request/response model.

This module is complementary to ``antigravity_cli.py``, which wraps the
CLI binary (``agy -p "..."``).  This module wraps the Python SDK
(``pip install google-antigravity``) and enables richer agent sessions:
streaming tokens, tool registration, MCP server attachment, and stateful
conversation history.

Public interface:
    agent_preflight()                          -> AgentPreflightResult
    agent_chat(prompt, **kwargs)               -> AgentChatResult
    agent_stream(prompt, **kwargs)             -> AgentStreamResult
"""

from __future__ import annotations

import asyncio
import importlib
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_TEXT_LIMIT = 16_000
_SDK_PACKAGE = "google.antigravity"

# One persistent event loop per bridge process, running in a daemon thread.
# This avoids creating a new loop per request and is safe for concurrent calls
# because asyncio.run_coroutine_threadsafe is used for dispatch.
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------


class AgentPreflightResult(dict):
    """Keys: ready, installed, api_key_present, sdk_version, error."""


class AgentChatResult(dict):
    """Keys: status, dry_run, text, elapsed_ms, model, error."""


class AgentStreamResult(dict):
    """Keys: status, dry_run, tokens, token_count, text, elapsed_ms, model, error."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    """Return the shared background event loop, creating it if needed."""
    global _loop  # noqa: PLW0603
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            loop = asyncio.new_event_loop()

            def _run(lp: asyncio.AbstractEventLoop) -> None:
                lp.run_forever()

            t = threading.Thread(target=_run, args=(loop,), daemon=True, name="ag-sdk-loop")
            t.start()
            _loop = loop
        return _loop


def _run_async(coro: Any, timeout_s: int) -> Any:
    """Dispatch a coroutine to the shared background loop and block until done."""
    loop = _get_or_create_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout_s)


def _import_sdk() -> tuple[bool, str, Any, Any]:
    """Try to import the google-antigravity SDK.

    Returns:
        (ok, version_or_error, Agent_class, LocalAgentConfig_class)
    """
    try:
        ag = importlib.import_module("google.antigravity")
        agent_cls = getattr(ag, "Agent", None)
        config_cls = getattr(ag, "LocalAgentConfig", None)
        if agent_cls is None or config_cls is None:
            return False, "SDK missing Agent or LocalAgentConfig", None, None
        version = getattr(ag, "__version__", "installed")
        return True, version, agent_cls, config_cls
    except ImportError as exc:
        return False, str(exc), None, None
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return False, str(exc), None, None


def _bounded(text: str) -> str:
    if len(text) <= _TEXT_LIMIT:
        return text
    return text[-_TEXT_LIMIT:]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def agent_preflight() -> AgentPreflightResult:
    """Check whether the Antigravity SDK is installed and usable.

    Returns:
        AgentPreflightResult with keys:
            ready (bool): True when SDK is installed and API key is present.
            installed (bool): True when import succeeded.
            api_key_present (bool): True when GEMINI_API_KEY env var is set.
            sdk_version (str): SDK version string or error message.
            error (str | None): Set on hard failure.

    Never raises.
    """
    try:
        ok, version_or_err, _, _ = _import_sdk()
        api_key = os.environ.get("GEMINI_API_KEY", "")
        api_key_present = bool(api_key and api_key not in ("your-gemini-or-auth-key", ""))
        ready = ok and api_key_present
        return AgentPreflightResult(
            ready=ready,
            installed=ok,
            api_key_present=api_key_present,
            sdk_version=version_or_err if ok else "",
            install_hint=(
                ""
                if ok
                else "Run: pip install google-antigravity  (installs compiled runtime binary from PyPI)"
            ),
            key_hint=(
                ""
                if api_key_present
                else "Set GEMINI_API_KEY in .env to enable live agent calls"
            ),
            error="" if ok else version_or_err,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return AgentPreflightResult(
            ready=False,
            installed=False,
            api_key_present=False,
            error=str(exc),
        )


def agent_chat(
    prompt: str,
    system_instructions: str = "",
    model: str = "",
    tools: list[str] | None = None,
    timeout_s: int = 90,
    dry_run: bool = True,
) -> AgentChatResult:
    """Send one prompt to an Antigravity SDK agent and return the text response.

    Args:
        prompt: User message to send.
        system_instructions: Optional system prompt passed to LocalAgentConfig.
        model: Optional model name (e.g. "gemini-2.0-flash-exp").
        tools: Unused placeholder for future custom tool names.
        timeout_s: Total wall-clock timeout for the SDK call.
        dry_run: When True (default), return a preview without calling the SDK.

    Returns:
        AgentChatResult with keys: status, dry_run, text, elapsed_ms, model, error.

    Never raises.
    """
    started = time.monotonic()
    try:
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            return AgentChatResult(status="error", dry_run=dry_run, error="prompt is required")

        clean_model = (model or os.environ.get("ANTIGRAVITY_MODEL", "")).strip()
        preview = {
            "prompt_chars": len(clean_prompt),
            "system_instructions_chars": len(system_instructions or ""),
            "model": clean_model or "(sdk default)",
            "timeout_s": timeout_s,
        }

        if dry_run:
            return AgentChatResult(
                status="dry_run",
                dry_run=True,
                text="",
                elapsed_ms=0.0,
                model=clean_model,
                command_preview=preview,
                note="Set dry_run=false to invoke the Antigravity SDK agent.",
            )

        ok, err, Agent, LocalAgentConfig = _import_sdk()
        if not ok:
            return AgentChatResult(
                status="error",
                dry_run=False,
                error=f"SDK not available: {err}",
                install_hint="pip install google-antigravity",
            )

        async def _run() -> str:
            kwargs: dict[str, Any] = {}
            if system_instructions:
                kwargs["system_instructions"] = system_instructions
            if clean_model:
                kwargs["model"] = clean_model
            config = LocalAgentConfig(**kwargs)
            async with Agent(config) as agent:
                response = await agent.chat(clean_prompt)
                return await response.text()

        text = _run_async(_run(), timeout_s=timeout_s)
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return AgentChatResult(
            status="ok",
            dry_run=False,
            text=_bounded(text or ""),
            elapsed_ms=elapsed_ms,
            model=clean_model,
            error="",
        )

    except TimeoutError:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return AgentChatResult(
            status="timeout",
            dry_run=dry_run,
            error=f"Agent call timed out after {timeout_s}s",
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return AgentChatResult(
            status="error",
            dry_run=dry_run,
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )


def agent_stream(
    prompt: str,
    system_instructions: str = "",
    model: str = "",
    timeout_s: int = 120,
    dry_run: bool = True,
) -> AgentStreamResult:
    """Send one prompt and collect the full streaming token response.

    The SDK streams tokens via ``async for token in response``.  This helper
    collects all tokens into a list and returns them together with the joined
    text so callers can either display the final text or replay the stream.

    Args:
        prompt: User message.
        system_instructions: Optional system prompt.
        model: Optional model name.
        timeout_s: Total wall-clock timeout.
        dry_run: When True (default), return a preview without SDK call.

    Returns:
        AgentStreamResult with keys:
            status, dry_run, tokens (list[str]), token_count, text,
            elapsed_ms, model, error.

    Never raises.
    """
    started = time.monotonic()
    try:
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            return AgentStreamResult(status="error", dry_run=dry_run, error="prompt is required")

        clean_model = (model or os.environ.get("ANTIGRAVITY_MODEL", "")).strip()

        if dry_run:
            return AgentStreamResult(
                status="dry_run",
                dry_run=True,
                tokens=[],
                token_count=0,
                text="",
                elapsed_ms=0.0,
                model=clean_model,
                note="Set dry_run=false to invoke the Antigravity SDK streaming agent.",
            )

        ok, err, Agent, LocalAgentConfig = _import_sdk()
        if not ok:
            return AgentStreamResult(
                status="error",
                dry_run=False,
                error=f"SDK not available: {err}",
                install_hint="pip install google-antigravity",
            )

        async def _run() -> list[str]:
            kwargs: dict[str, Any] = {}
            if system_instructions:
                kwargs["system_instructions"] = system_instructions
            if clean_model:
                kwargs["model"] = clean_model
            config = LocalAgentConfig(**kwargs)
            collected: list[str] = []
            async with Agent(config) as agent:
                response = await agent.chat(clean_prompt)
                async for token in response:
                    collected.append(token)
            return collected

        tokens: list[str] = _run_async(_run(), timeout_s=timeout_s)
        text = _bounded("".join(tokens))
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return AgentStreamResult(
            status="ok",
            dry_run=False,
            tokens=tokens,
            token_count=len(tokens),
            text=text,
            elapsed_ms=elapsed_ms,
            model=clean_model,
            error="",
        )

    except TimeoutError:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return AgentStreamResult(
            status="timeout",
            dry_run=dry_run,
            error=f"Stream timed out after {timeout_s}s",
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return AgentStreamResult(
            status="error",
            dry_run=dry_run,
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
