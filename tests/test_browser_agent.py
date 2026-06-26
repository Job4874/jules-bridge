import pytest
from unittest.mock import patch, MagicMock

from modules.ui_automation import get_secret, detect_ui_state, SecretAccessError


class TestGetSecret:
    def test_get_secret_redacts_when_allowed(self):
        result = get_secret("QuantowerLogin", allow_secret_use=True)
        assert result == "REDACTED"

    def test_get_secret_denied_when_not_allowed(self):
        with pytest.raises(SecretAccessError):
            get_secret("QuantowerLogin", allow_secret_use=False)


class TestDetectUIState:
    def test_logged_in(self):
        text = "Quantower v1.146.13 - Disconnect - Strategy Manager"
        assert detect_ui_state(text) == "LOGGED_IN"

    def test_logged_out(self):
        text = "Quantower - Login - Username Password"
        assert detect_ui_state(text) == "LOGGED_OUT"

    def test_unknown(self):
        assert detect_ui_state("Some random text") == "UNKNOWN"


class TestBrowserAgent:
    @patch("playwright.sync_api.sync_playwright")
    def test_init_browser_launches_persistent_context(self, mock_sync_playwright):
        mock_playwright = MagicMock()
        mock_context = MagicMock()
        mock_playwright.chromium.launch_persistent_context.return_value = mock_context
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        from modules.browser_agent import init_browser

        ctx = init_browser(user_data_dir=r"C:\Test\Edge")
        assert ctx is mock_context
        mock_playwright.chromium.launch_persistent_context.assert_called_once_with(
            user_data_dir=r"C:\Test\Edge",
            channel="msedge",
            headless=False,
        )

    @patch("modules.browser_agent.init_browser")
    @patch("modules.ui_automation.detect_ui_state")
    def test_verify_quantower_login_detects_state(
        self, mock_detect, mock_init_browser
    ):
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "login page html"
        mock_context.new_page.return_value = mock_page
        mock_init_browser.return_value = mock_context
        mock_detect.return_value = "LOGGED_IN"

        from modules.browser_agent import verify_quantower_login

        result = verify_quantower_login(url="https://quantower.com")
        assert result["state"] == "LOGGED_IN"
        assert result["url"] == "https://quantower.com"
        mock_context.close.assert_called_once()
