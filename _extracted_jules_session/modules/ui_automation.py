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

class SecretAccessError(Exception):
    pass

def get_secret(secret_name: str, allow_secret_use: bool = False) -> str:
    """Retrieve an OS-backed secret (Windows Credential Manager / DPAPI mock)."""
    if not allow_secret_use:
        raise SecretAccessError(f"Access to secret '{secret_name}' denied: allow_secret_use=False")
    
    # Mocking retrieval from OS-backed store.
    # In reality, we'd fetch the password here, but we MUST redact plaintext
    # from ever being returned directly as a usable string to logging/output.
    # For automation, the bridge would use it directly in the shell without
    # passing the literal value back up the stack.
    
    return "REDACTED"

def detect_ui_state(ocr_text: str) -> str:
    """Detect Quantower UI state from OCR text."""
    text_lower = ocr_text.lower()
    
    if "disconnect" in text_lower and "strategy manager" in text_lower:
        return "LOGGED_IN"
    
    if "login" in text_lower and "password" in text_lower:
        return "LOGGED_OUT"
        
    return "UNKNOWN"
