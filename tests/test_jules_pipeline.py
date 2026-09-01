"""Unit tests for modules/jules_pipeline.py."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from modules.jules_pipeline import JulesPipeline
from modules.unified_operator import UnifiedOperatorStateDB


class TestJulesPipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "pipeline_state.db"
        self.db = UnifiedOperatorStateDB(db_path=self.db_path)
        self.pipeline = JulesPipeline(state_db=self.db)

    def tearDown(self):  # pylint: disable=invalid-name
        try:
            self.tmp_dir.cleanup()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def test_dispatch_session_mock(self):
        with patch("modules.jules_pipeline.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Created session 8503583543641914961"
            mock_run.return_value.stderr = ""
            res = self.pipeline.dispatch_session("Inspect code")
            self.assertEqual(res["status"], "dispatched")
            self.assertIn("operation_id", res)
            self.assertTrue(res["operation_id"].startswith("jules_dispatch_"))

    def test_dispatch_creates_checkpoint(self):
        """Dispatch must create a completed checkpoint in the state DB."""
        with patch("modules.jules_pipeline.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Created session 999"
            mock_run.return_value.stderr = ""
            res = self.pipeline.dispatch_session("Test prompt")
            op_id = res["operation_id"]
            chk = self.db.get_checkpoint(op_id)
            self.assertIsNotNone(chk)
            self.assertEqual(chk["status"], "completed")

    async def test_poll_session_completed(self):
        with patch("modules.jules_pipeline.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"session 8503583543641914961 COMPLETED", b"")
            mock_exec.return_value = mock_proc
            res = await self.pipeline.poll_session("8503583543641914961", max_wait_s=1.0)
            self.assertEqual(res["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
