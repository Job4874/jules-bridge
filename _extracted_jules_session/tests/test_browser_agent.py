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
    
    mock_detect.return_value = "LOGGED_IN"
    
    result = verify_quantower_login()
    
    mock_page.goto.assert_called_once_with("https://quantower.com")
    assert result == True
