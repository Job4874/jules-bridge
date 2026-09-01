import pytest
from unittest.mock import patch, MagicMock
from modules.browser_agent import init_browser, verify_quantower_login

@patch('modules.browser_agent.sync_playwright')
def test_init_browser_with_edge_profile(mock_playwright):
    mock_context = MagicMock()
    mock_playwright_instance = MagicMock()
    mock_playwright.return_value.start.return_value = mock_playwright_instance
    mock_playwright_instance.chromium.launch_persistent_context.return_value = mock_context

    context = init_browser()

    mock_playwright_instance.chromium.launch_persistent_context.assert_called_once()
    call_args = mock_playwright_instance.chromium.launch_persistent_context.call_args
    assert "Microsoft" in call_args[1]["user_data_dir"]
    assert call_args[1].get('channel') == 'msedge'

@patch('modules.browser_agent.init_browser')
@patch('modules.browser_agent.detect_ui_state')
def test_verify_quantower_login(mock_detect, mock_init_browser):
    mock_page = MagicMock()
    mock_page.content.return_value = "<html>Quantower - Disconnect - Strategy Manager</html>"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_init_browser.return_value = mock_context

    # detect_ui_state returns a UIDetectionResult dict; "quantower_ready" is the
    # logged-in/ready state.
    mock_detect.return_value = {"state": "quantower_ready", "confidence": 0.8, "signals": [], "error": None}

    result = verify_quantower_login()

    mock_page.goto.assert_called_once_with("https://quantower.com")
    # The page text must be passed as the ocr_text keyword, not positionally.
    assert mock_detect.call_args.kwargs.get("ocr_text") == mock_page.content.return_value
    assert result is True


@patch('modules.browser_agent.init_browser')
@patch('modules.browser_agent.detect_ui_state')
def test_verify_quantower_login_not_ready_returns_false(mock_detect, mock_init_browser):
    mock_page = MagicMock()
    mock_page.content.return_value = "<html>Sign in - password</html>"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_init_browser.return_value = mock_context

    mock_detect.return_value = {"state": "auth_prompt", "confidence": 0.8, "signals": [], "error": None}

    result = verify_quantower_login()

    assert result is False


@patch('modules.browser_agent.sync_playwright', None)
def test_init_browser_playwright_missing():
    with pytest.raises(RuntimeError, match="Playwright is not installed"):
        init_browser()

def test_browser_agent_import_error():
    import sys
    import importlib
    import modules.browser_agent

    # Backup the original module
    orig_playwright = sys.modules.get('playwright.sync_api')

    # Force ImportError on next import
    sys.modules['playwright.sync_api'] = None

    try:
        # Reload the module so the try/except block at the top runs
        importlib.reload(modules.browser_agent)

        # Verify sync_playwright is set to None when ImportError occurs
        assert modules.browser_agent.sync_playwright is None
    finally:
        # Restore normal state
        if orig_playwright is not None:
            sys.modules['playwright.sync_api'] = orig_playwright
        else:
            del sys.modules['playwright.sync_api']

        # Reload to restore the original working module for other tests
        importlib.reload(modules.browser_agent)

@patch('modules.browser_agent.init_browser')
@patch('modules.browser_agent.detect_ui_state')
def test_verify_quantower_login_missing_state_key(mock_detect, mock_init_browser):
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_init_browser.return_value = mock_context

    # Return a dict without a 'state' key
    mock_detect.return_value = {"confidence": 0.5, "signals": []}

    result = verify_quantower_login()

    assert result is False


@patch('modules.browser_agent.init_browser')
def test_verify_quantower_login_goto_raises(mock_init_browser):
    mock_page = MagicMock()
    mock_page.goto.side_effect = Exception("Network error")
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_init_browser.return_value = mock_context

    with pytest.raises(Exception, match="Network error"):
        verify_quantower_login()


@patch('modules.browser_agent.init_browser')
@patch('modules.browser_agent.detect_ui_state')
def test_verify_quantower_login_empty_content(mock_detect, mock_init_browser):
    mock_page = MagicMock()
    mock_page.content.return_value = ""
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_init_browser.return_value = mock_context

    mock_detect.return_value = {"state": "quantower_ready"}

    result = verify_quantower_login()

    # Verify we still call detect_ui_state even if content is empty
    mock_detect.assert_called_once_with(ocr_text="")
    assert result is True


@patch('modules.browser_agent.init_browser')
def test_verify_quantower_login_init_browser_fails(mock_init_browser):
    mock_init_browser.side_effect = RuntimeError("Playwright is not installed")

    with pytest.raises(RuntimeError, match="Playwright is not installed"):
        verify_quantower_login()
