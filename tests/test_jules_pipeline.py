"""Unit tests for modules/jules_pipeline.py."""

import unittest
from unittest.mock import patch

from modules.jules_pipeline import JulesPipeline


class TestJulesPipeline(unittest.TestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.pipeline = JulesPipeline()

    def test_dispatch_session_mock(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Created session 8503583543641914961"
            res = self.pipeline.dispatch_session("Inspect code")
            self.assertEqual(res["status"], "dispatched")

    def test_poll_session_completed(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "session 8503583543641914961 COMPLETED"
            res = self.pipeline.poll_session("8503583543641914961", max_wait_s=1.0)
            self.assertEqual(res["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
