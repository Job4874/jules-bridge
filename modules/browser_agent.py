import os
from playwright.sync_api import sync_playwright
from modules.ui_automation import detect_ui_state

EDGE_PROFILE_PATH = r"C:\Users\abdul\AppData\Local\Microsoft\Edge\User Data"

def init_browser():
    """Initialize Playwright configured to launch using the local Edge profile."""
    # We do not actually manage the 'with' context lifecycle in this mock,
    # as playwright usually requires it. But for the test we'll use a mocked instance.
    playwright = sync_playwright().start()

    # Launch persistent context using the Edge Profile
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=EDGE_PROFILE_PATH,
        channel="msedge",
        headless=False
    )
    return context

def verify_quantower_login() -> bool:
    """Launch the browser, navigate to Quantower, and confirm Logged In status."""
    context = init_browser()
    page = context.new_page()
    page.goto("https://quantower.com")

    # Extract text from the page to simulate OCR/UI detection
    page_text = page.content()

    state = detect_ui_state(page_text)

    # Clean up (mocked cleanup)
    # context.close()

    return state == "LOGGED_IN"
