"""Browser agent deep module — launch Edge with the local user profile.

Simple typed interface hiding Playwright lifecycle and Edge profile paths.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_EDGE_PROFILE_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", r"C:\Users\abdul\AppData\Local"),
    "Microsoft",
    "Edge",
    "User Data",
)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def init_browser(user_data_dir: str = ""):
    """Initialize Playwright configured to launch using the local Edge profile.

    Args:
        user_data_dir: Override the Edge profile directory.

    Returns:
        A Playwright browser context. Caller owns lifecycle.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir or _EDGE_PROFILE_PATH,
        channel="msedge",
        headless=False,
    )
    return context


def verify_quantower_login(url: str = "https://quantower.com") -> dict:
    """Launch the browser, navigate to Quantower, and detect login state.

    Args:
        url: URL to navigate to for login-state detection.

    Returns:
        dict with state (LOGGED_IN, LOGGED_OUT, UNKNOWN) and url.
    """
    from modules.ui_automation import detect_ui_state  # noqa: PLC0415

    context = init_browser()
    try:
        page = context.new_page()
        page.goto(url)
        page_text = page.content()
        state = detect_ui_state(page_text)
        return {"state": state, "url": url}
    finally:
        context.close()
