"""TDD tests for secure UI state detection and secret provider boundaries."""

from __future__ import annotations


class MockSecretProvider:
    """Mock OS-backed secret provider for deterministic unit tests."""

    def get_secret(self, target: str) -> dict:
        return {
            "target": target,
            "username": "operator@example.test",
            "password": "super-secret-password",
        }


class TestMockSecretProviderBoundary:
    def test_get_secret_blocks_without_runtime_authorization(self):
        from modules.ui_automation import get_secret  # pylint: disable=import-outside-toplevel

        result = get_secret(
            "quantower_login",
            allow_secret_use=False,
            provider=MockSecretProvider(),
        )

        assert result["status"] == "blocked"
        assert result["target"] == "quantower_login"
        assert result["secret_available"] is False
        assert "password" not in result
        assert "super-secret-password" not in repr(result)

    def test_get_secret_reports_availability_without_returning_plaintext_secret(self):
        from modules.ui_automation import get_secret  # pylint: disable=import-outside-toplevel

        result = get_secret(
            "quantower_login",
            allow_secret_use=True,
            provider=MockSecretProvider(),
        )

        assert result["status"] == "available"
        assert result["target"] == "quantower_login"
        assert result["username"] == "operator@example.test"
        assert result["secret_available"] is True
        assert "password" not in result
        assert "super-secret-password" not in repr(result)


class TestUIDetectionStateEngine:
    def test_detects_quantower_login_from_ocr_text(self):
        from modules.ui_automation import detect_ui_state  # pylint: disable=import-outside-toplevel

        result = detect_ui_state(
            ocr_text="Quantower Login Email Password Sign In",
        )

        assert result["state"] == "quantower_login"
        assert result["confidence"] >= 0.8
        assert "login" in result["signals"]
        assert result["error"] is None

    def test_detects_quantower_loading_from_ocr_text(self):
        from modules.ui_automation import detect_ui_state  # pylint: disable=import-outside-toplevel

        result = detect_ui_state(
            ocr_text="Quantower loading workspace please wait connecting",
        )

        assert result["state"] == "quantower_loading"
        assert result["confidence"] >= 0.8
        assert "loading" in result["signals"]
        assert result["error"] is None

    def test_detects_auth_prompt_from_ocr_text(self):
        from modules.ui_automation import detect_ui_state  # pylint: disable=import-outside-toplevel

        result = detect_ui_state(
            ocr_text="Please enter your email and password to continue login",
        )

        assert result["state"] == "auth_prompt"
        assert result["confidence"] >= 0.8
        assert "credentials" in result["signals"]

    def test_detects_error_state_from_ocr_text(self):
        from modules.ui_automation import detect_ui_state  # pylint: disable=import-outside-toplevel

        result = detect_ui_state(
            ocr_text="Connection failed: unexpected error occurred",
        )

        assert result["state"] == "error"
        assert result["confidence"] >= 0.7
