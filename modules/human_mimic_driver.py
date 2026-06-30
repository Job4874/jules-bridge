"""Human-mimic UI driver routines.

This module binds UI detection, guarded secret access, and physical UI actions
into small ACT loops. It keeps orchestration in modules so bridge.py remains a
thin validate → call module → return JSON layer.

Public interface:
    drive_quantower_login(...) -> HumanMimicResult
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .ui_automation import click, detect_ui_state, get_secret, type_text


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class HumanMimicResult(dict):
    """Result of a human-mimic ACT loop.

    Keys always present:
      status (str): success, blocked, unknown, or error
      state (str): detected UI state
      acted (bool): whether keyboard/mouse actions were attempted
      message (str): non-secret operator-facing summary
      error (str | None): sanitized failure detail
    """


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _notify(
    notify_func: Callable[[str, str], Any] | None,
    subject: str,
    body: str,
) -> str:
    """Best-effort notification wrapper that never raises."""
    if notify_func is None:
        return "skipped"
    try:
        notify_func(subject, body)
        return "sent"
    except Exception:
        return "failed"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def drive_quantower_login(
    ocr_text: str = "",
    submit_x: int = 0,
    submit_y: int = 0,
    allow_secret_use: bool = False,
    secret_provider: object | None = None,
    type_func: Callable[[str], Any] = type_text,
    click_func: Callable[[int, int], Any] = click,
    press_key_func: Callable[[str], Any] | None = None,
    notify_func: Callable[[str, str], Any] | None = None,
) -> HumanMimicResult:
    """Run the Quantower login H/L/ACT loop.

    Args:
        ocr_text: OCR text from the current screen.
        submit_x: Submit button x-coordinate.
        submit_y: Submit button y-coordinate.
        allow_secret_use: Runtime gate for credential lookup.
        secret_provider: OS-backed secret provider, or mock provider in tests.
        type_func: Injectable keyboard action function.
        click_func: Injectable mouse action function.
        press_key_func: Injectable keyboard key press function (defaults to Tab).
        notify_func: Optional notification callback accepting subject and body.

    Returns:
        HumanMimicResult. Plaintext secrets are never returned.
        This function never raises.
    """
    state_result = detect_ui_state(ocr_text=ocr_text)
    state = str(state_result.get("state", "unknown"))

    if press_key_func is None:
        def _press_key(key: str) -> dict[str, str]:
            try:
                import pyautogui  # type: ignore

                pyautogui.press(key)
                return {"status": f"Pressed {key}"}
            except Exception:
                return {"status": "press failed"}
    else:
        _press_key = press_key_func

    if state != "quantower_login":
        message = "State unknown"
        _notify(notify_func, "Quantower login skipped", f"Detected state: {state}")
        return HumanMimicResult(
            status="unknown",
            state=state,
            acted=False,
            message=message,
            error=None,
        )

    secret = get_secret(
        "quantower_login",
        allow_secret_use=allow_secret_use,
        provider=secret_provider,
    )
    if not secret.get("secret_available"):
        message = str(secret.get("error") or "secret unavailable")
        _notify(notify_func, "Quantower login blocked", message)
        return HumanMimicResult(
            status="blocked",
            state=state,
            acted=False,
            message=message,
            error=None,
        )

    try:
        username = str(secret.get("username", ""))
        type_func(username)
        if secret_provider is not None and hasattr(secret_provider, "type_password"):
            secret_provider.type_password(
                "quantower_login",
                type_func,
                _press_key,
            )
        click_func(submit_x, submit_y)
        message = "Login sequence initiated"
        _notify(notify_func, "Quantower login action", message)
        return HumanMimicResult(
            status="success",
            state=state,
            acted=True,
            message=message,
            error=None,
        )
    except Exception:
        message = "Login action failed"
        _notify(notify_func, "Quantower login failed", message)
        return HumanMimicResult(
            status="error",
            state=state,
            acted=False,
            message=message,
            error="ui action failed",
        )
