"""Tests for the Human-Mimic Quantower ACT driver."""

from __future__ import annotations

from unittest.mock import Mock


class MockSecretProvider:
    def get_secret(self, target: str) -> dict:
        return {
            "target": target,
            "username": "operator@example.test",
            "password": "never-return-this",
        }

    def type_password(self, target: str, type_func, press_key_func) -> None:
        press_key_func("tab")
        type_func("never-return-this")


def test_drive_quantower_login_types_username_and_clicks_on_login_state():
    from modules.human_mimic_driver import drive_quantower_login

    typed: list[str] = []
    clicks: list[tuple[int, int]] = []
    keys: list[str] = []
    notifier = Mock()

    result = drive_quantower_login(
        ocr_text="Quantower Login Email Password Sign In",
        submit_x=640,
        submit_y=480,
        allow_secret_use=True,
        secret_provider=MockSecretProvider(),
        type_func=lambda text: typed.append(text) or {"status": "typed"},
        click_func=lambda x, y: clicks.append((x, y)) or {"status": "clicked"},
        press_key_func=lambda key: keys.append(key) or {"status": "pressed"},
        notify_func=notifier,
    )

    assert result["status"] == "success"
    assert result["state"] == "quantower_login"
    assert result["acted"] is True
    assert result["message"] == "Login sequence initiated"
    assert typed == ["operator@example.test", "never-return-this"]
    assert keys == ["tab"]
    assert clicks == [(640, 480)]
    assert "never-return-this" not in repr(result)
    notifier.assert_called_once()


def test_drive_quantower_login_blocks_secret_use_without_runtime_flag():
    from modules.human_mimic_driver import drive_quantower_login

    type_func = Mock()
    click_func = Mock()
    notifier = Mock()

    result = drive_quantower_login(
        ocr_text="Quantower Login Email Password Sign In",
        submit_x=640,
        submit_y=480,
        allow_secret_use=False,
        secret_provider=MockSecretProvider(),
        type_func=type_func,
        click_func=click_func,
        notify_func=notifier,
    )

    assert result["status"] == "blocked"
    assert result["state"] == "quantower_login"
    assert result["acted"] is False
    assert "allow_secret_use" in result["message"]
    type_func.assert_not_called()
    click_func.assert_not_called()
    notifier.assert_called_once()


def test_drive_quantower_login_ignores_unknown_state():
    from modules.human_mimic_driver import drive_quantower_login

    type_func = Mock()
    click_func = Mock()

    result = drive_quantower_login(
        ocr_text="Desktop with random unrelated content",
        submit_x=640,
        submit_y=480,
        allow_secret_use=True,
        secret_provider=MockSecretProvider(),
        type_func=type_func,
        click_func=click_func,
    )

    assert result["status"] == "unknown"
    assert result["acted"] is False
    type_func.assert_not_called()
    click_func.assert_not_called()
