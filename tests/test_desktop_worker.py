"""Unit tests for modules/desktop_worker.py."""

import unittest

from modules.desktop_worker import DesktopWorker


class TestDesktopWorker(unittest.TestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.worker = DesktopWorker(headless=True)

    def test_browser_availability_check(self):
        is_avail = self.worker.is_browser_available()
        self.assertIsInstance(is_avail, bool)

    def test_navigate_web(self):
        res = self.worker.navigate_web("https://example.com", action="read")
        self.assertIn("status", res)
        self.assertIn("url", res)

    def test_execute_desktop_action_unsupported(self):
        res = self.worker.execute_desktop_action("unknown_action")
        self.assertEqual(res["status"], "unsupported_action")


if __name__ == "__main__":
    unittest.main()
