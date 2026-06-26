"""Unit tests for modules/ui_automation.py.

pyautogui calls are fully mocked — no real mouse movement occurs.
"""

import unittest
from unittest.mock import MagicMock, patch


class TestScreenshot(unittest.TestCase):
    @patch("modules.ui_automation._pyautogui")
    def test_screenshot_returns_base64(self, mock_pag_factory):
        import base64
        import os
        import tempfile

        # Write a small PNG stand-in so open() succeeds
        handle, path = tempfile.mkstemp(suffix=".png")
        os.write(handle, b"fake-png-data")
        os.close(handle)

        pag = MagicMock()
        # Intercept screenshot call and write to the expected temp path
        def fake_screenshot(p):
            import shutil
            shutil.copy(path, p)
        pag.screenshot.side_effect = fake_screenshot
        mock_pag_factory.return_value = pag

        from modules.ui_automation import screenshot
        result = screenshot(save=False)

        self.assertIn("image_base64", result)
        decoded = base64.b64decode(result["image_base64"])
        self.assertEqual(decoded, b"fake-png-data")
        self.assertNotIn("saved_path", result)

        os.unlink(path)

    @patch("modules.ui_automation._pyautogui")
    def test_screenshot_save_returns_path(self, mock_pag_factory):
        import os
        import tempfile

        handle, path = tempfile.mkstemp(suffix=".png")
        os.write(handle, b"px")
        os.close(handle)

        pag = MagicMock()
        def fake_screenshot(p):
            import shutil
            shutil.copy(path, p)
        pag.screenshot.side_effect = fake_screenshot
        mock_pag_factory.return_value = pag

        import tempfile as _tmp
        with _tmp.TemporaryDirectory() as d:
            from modules.ui_automation import screenshot
            result = screenshot(save=True, screenshot_dir=d)
            self.assertIn("saved_path", result)
            self.assertTrue(os.path.exists(result["saved_path"]))

        os.unlink(path)


class TestClick(unittest.TestCase):
    @patch("modules.ui_automation._pyautogui")
    def test_click_valid_coordinates(self, mock_pag_factory):
        pag = MagicMock()
        pag.size.return_value = (1920, 1080)
        mock_pag_factory.return_value = pag

        from modules.ui_automation import click
        result = click(100, 200)
        pag.moveTo.assert_called_once_with(100, 200, duration=0.2)
        pag.click.assert_called_once_with(button="left")
        self.assertIn("Clicked", result["status"])

    @patch("modules.ui_automation._pyautogui")
    def test_click_negative_coordinates_raises(self, mock_pag_factory):
        pag = MagicMock()
        pag.size.return_value = (1920, 1080)
        mock_pag_factory.return_value = pag

        from modules.ui_automation import click
        with self.assertRaises(ValueError):
            click(-1, 100)

    @patch("modules.ui_automation._pyautogui")
    def test_click_out_of_bounds_raises(self, mock_pag_factory):
        pag = MagicMock()
        pag.size.return_value = (1920, 1080)
        mock_pag_factory.return_value = pag

        from modules.ui_automation import click
        with self.assertRaises(ValueError) as ctx:
            click(5000, 100)
        self.assertIn("display bounds", str(ctx.exception))
        pag.moveTo.assert_not_called()

    @patch("modules.ui_automation._pyautogui")
    def test_click_invalid_button_raises(self, mock_pag_factory):
        pag = MagicMock()
        pag.size.return_value = (1920, 1080)
        mock_pag_factory.return_value = pag

        from modules.ui_automation import click
        with self.assertRaises(ValueError):
            click(100, 100, button="sideways")

    @patch("modules.ui_automation._pyautogui")
    def test_click_right_button(self, mock_pag_factory):
        pag = MagicMock()
        pag.size.return_value = (1920, 1080)
        mock_pag_factory.return_value = pag

        from modules.ui_automation import click
        click(10, 10, button="right")
        pag.click.assert_called_once_with(button="right")


class TestTypeText(unittest.TestCase):
    @patch("modules.ui_automation._pyautogui")
    def test_type_text_calls_write(self, mock_pag_factory):
        pag = MagicMock()
        mock_pag_factory.return_value = pag

        from modules.ui_automation import type_text
        result = type_text("hello")
        pag.write.assert_called_once_with("hello", interval=0.01)
        self.assertEqual(result["status"], "Typed successfully")

    @patch("modules.ui_automation._pyautogui")
    def test_type_text_empty_string(self, mock_pag_factory):
        pag = MagicMock()
        mock_pag_factory.return_value = pag

        from modules.ui_automation import type_text
        result = type_text("")
        pag.write.assert_called_once_with("", interval=0.01)
        self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main()
