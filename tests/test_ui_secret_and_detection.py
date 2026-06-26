import pytest
from modules.ui_automation import get_secret, detect_ui_state, SecretAccessError

def test_get_secret_with_allow_true():
    # Should redact plaintext
    result = get_secret("QuantowerLogin", allow_secret_use=True)
    assert result == "REDACTED"

def test_get_secret_with_allow_false():
    # Should raise error if not allowed
    with pytest.raises(SecretAccessError):
        get_secret("QuantowerLogin", allow_secret_use=False)

def test_detect_ui_state_logged_in():
    ocr_text = "Quantower v1.146.13 - Disconnect - Strategy Manager"
    state = detect_ui_state(ocr_text)
    assert state == "LOGGED_IN"

def test_detect_ui_state_logged_out():
    ocr_text = "Quantower - Login - Username Password"
    state = detect_ui_state(ocr_text)
    assert state == "LOGGED_OUT"

def test_detect_ui_state_unknown():
    ocr_text = "Some random text"
    state = detect_ui_state(ocr_text)
    assert state == "UNKNOWN"
