"""UI automation deep module — screenshot, click, type.

Simple typed interface hiding pyautogui, display bounds checking,
base64 encoding, and file management.
"""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class ScreenshotResult(dict):
    """Result of a screenshot capture.

    Keys always present:
      image_base64 (str): base64-encoded PNG data
    Optional keys:
      saved_path (str): filesystem path if save=True was requested
    """


class ClickResult(dict):
    """Result of a mouse click action.

    Keys always present:
      status (str): human-readable confirmation
    """


class SecretResult(dict):
    """Result of a guarded secret lookup.

    Keys always present:
      status (str): available, blocked, or error
      target (str): requested secret target
      username (str): non-secret username when available
      secret_available (bool): whether a secret was retrieved without exposing it
      error (str | None): failure detail, never the secret value
    """


class UIDetectionResult(dict):
    """Result of OCR/template UI state classification.

    Keys always present:
      state (str): classified UI state
      confidence (float): coarse confidence score from deterministic signals
      signals (list[str]): matched non-secret state signals
      error (str | None): failure detail
    """


class UIActionResult(dict):
    """Result of a guarded UI action.

    Keys always present:
      status (str): success, blocked, unknown, or error
      state (str): detected UI state
      acted (bool): whether keyboard/mouse actions were attempted
      error (str | None): failure detail
    """


# ---------------------------------------------------------------------------
# Module-level lazy import guard — pyautogui is only imported at call time
# so that test environments can mock it cleanly.
# ---------------------------------------------------------------------------

def _pyautogui():
    import pyautogui as _pag  # noqa: PLC0415
    return _pag


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def get_secret(
    target: str,
    allow_secret_use: bool = False,
    provider: object | None = None,
) -> SecretResult:
    """Retrieve only non-secret metadata for an operator-authorized secret.

    Args:
        target: Logical secret target, for example ``quantower_login``.
        allow_secret_use: Runtime authorization gate. Secret lookup is blocked
            unless this is explicitly True.
        provider: Injected OS-backed provider. Tests may pass a mock provider
            with ``get_secret(target)``.

    Returns:
        SecretResult. The plaintext password/secret is never included.
        This function never raises.
    """
    if not allow_secret_use:
        return SecretResult(
            status="blocked",
            target=target,
            username="",
            secret_available=False,
            error="allow_secret_use must be true",
        )

    if provider is None:
        return SecretResult(
            status="error",
            target=target,
            username="",
            secret_available=False,
            error="secret provider is required",
        )

    try:
        raw_secret = provider.get_secret(target)
        username = ""
        if isinstance(raw_secret, dict):
            username = str(raw_secret.get("username", ""))
        return SecretResult(
            status="available",
            target=target,
            username=username,
            secret_available=True,
            error=None,
        )
    except Exception:
        return SecretResult(
            status="error",
            target=target,
            username="",
            secret_available=False,
            error="secret provider lookup failed",
        )


def detect_ui_state(
    _image_path: str | None = None,
    ocr_text: str = "",
    template_signals: dict | None = None,
) -> UIDetectionResult:
    """Classify a UI state from OCR text and optional template signals.

    Args:
        _image_path: Reserved for later OCR/OpenCV integration.
        ocr_text: Text extracted from the screen. Tests pass this directly.
        template_signals: Optional precomputed visual signals.

    Returns:
        UIDetectionResult with a deterministic state classification.
        This function never raises.
    """
    try:
        text = ocr_text.casefold()
        signals: list[str] = []
        templates = template_signals or {}

        if "quantower" in text:
            signals.append("quantower")
        if "login" in text or "sign in" in text:
            signals.append("login")
        if "password" in text or "email" in text:
            signals.append("credentials")
        if "loading" in text or "please wait" in text:
            signals.append("loading")
        if "connecting" in text or "workspace" in text:
            signals.append("workspace")

        for key, value in templates.items():
            if value:
                signals.append(str(key))

        if {"quantower", "login", "credentials"}.issubset(signals):
            return UIDetectionResult(
                state="quantower_login",
                confidence=0.9,
                signals=signals,
                error=None,
            )

        if "login" in signals and "credentials" in signals:
            return UIDetectionResult(
                state="auth_prompt",
                confidence=0.8,
                signals=signals,
                error=None,
            )

        if "quantower" in signals and "loading" in signals:
            return UIDetectionResult(
                state="quantower_loading",
                confidence=0.9,
                signals=signals,
                error=None,
            )

        if "quantower_ready" in signals:
            return UIDetectionResult(
                state="quantower_ready",
                confidence=0.8,
                signals=signals,
                error=None,
            )

        if "error" in text or "failed" in text:
            return UIDetectionResult(
                state="error",
                confidence=0.7,
                signals=signals,
                error=None,
            )

        return UIDetectionResult(
            state="unknown",
            confidence=0.0,
            signals=signals,
            error=None,
        )
    except Exception as exc:
        return UIDetectionResult(
            state="unknown",
            confidence=0.0,
            signals=[],
            error=str(exc),
        )


def screenshot(save: bool = False, screenshot_dir: str | None = None) -> ScreenshotResult:
    """Capture the full desktop as a PNG and return base64-encoded data.

    Args:
        save: If True, keep the file on disk and include saved_path in result.
        screenshot_dir: Directory to write screenshots. Defaults to
            <bridge_root>/jules_inbox/screenshots.

    Returns:
        ScreenshotResult with image_base64, and optionally saved_path.
    """
    pag = _pyautogui()

    if screenshot_dir is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        screenshot_dir = os.path.join(root, "jules_inbox", "screenshots")

    os.makedirs(screenshot_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(screenshot_dir, f"screen_{stamp}.png")

    pag.screenshot(path)

    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    if not save:
        os.remove(path)
        return ScreenshotResult(image_base64=encoded)
    return ScreenshotResult(image_base64=encoded, saved_path=path)


def click(x: int, y: int, button: str = "left") -> ClickResult:
    """Move the mouse to (x, y) and click.

    Args:
        x: Horizontal pixel position (must be within display width).
        y: Vertical pixel position (must be within display height).
        button: 'left' (default), 'right', or 'middle'.

    Returns:
        ClickResult with status message.

    Raises:
        ValueError: if x/y are outside display bounds or button is invalid.
    """
    pag = _pyautogui()

    if button not in ("left", "right", "middle"):
        raise ValueError(f"button must be left, right, or middle; got {button!r}")

    width, height = pag.size()
    if x < 0 or y < 0:
        raise ValueError(f"x and y must be >= 0; got x={x}, y={y}")
    if x >= width or y >= height:
        raise ValueError(
            f"x/y must fit within display bounds {width}x{height}; got x={x}, y={y}"
        )

    pag.moveTo(x, y, duration=0.2)
    pag.click(button=button)
    return ClickResult(status=f"Clicked {x}, {y}")


def type_text(text: str) -> dict:
    """Type text on the keyboard at the current focus.

    Args:
        text: String to type (may be empty).

    Returns:
        dict with status.
    """
    pag = _pyautogui()
    pag.write(text, interval=0.01)
    return {"status": "Typed successfully"}
