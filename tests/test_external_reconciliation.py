"""Unit tests for external action crash reconciliation in UnifiedOperator."""

import tempfile
import unittest
from pathlib import Path

from modules import unified_operator as uo


class TestExternalActionReconciliation(unittest.TestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "reconcile_state.db"
        self.db = uo.UnifiedOperatorStateDB(db_path=self.db_path)
        self.loop = uo.ObserveReasonActVerifyLoop(self.db)

    def tearDown(self):  # pylint: disable=invalid-name
        try:
            self.tmp_dir.cleanup()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def test_reconcile_jules_session_post_crash(self):
        """Simulate a crash after Jules cloud session creation and verify idempotency reconciliation."""
        idemp_key = "jules_crash_001"
        goal = "Dispatch Jules cloud task"
        step = {
            "description": "Create Jules session",
            "action_type": "jules_session",
            "external_id": "8503583543641914961",
        }

        # Step 1: Save mid-execution state as if process crashed after Jules API call
        self.db.save_checkpoint(
            idempotency_key=idemp_key,
            goal=goal,
            workflow_step="Create Jules session",
            status="executing",
            payload=step,
        )

        # Step 2: Restart and call act()
        res = self.loop.act(goal, step, idemp_key)
        self.assertTrue(res.get("reconciled"))
        self.assertEqual(res.get("external_id"), "8503583543641914961")

        # Checkpoint is updated to completed
        chk = self.db.get_checkpoint(idemp_key)
        self.assertEqual(chk["status"], "completed")

    def test_reconcile_git_commit_post_crash(self):
        """Simulate a crash after git commit creation and verify reconciliation against git commit object."""
        idemp_key = "git_crash_001"
        goal = "Commit patch"
        step = {
            "description": "Commit changes",
            "action_type": "git_commit",
            "external_id": "HEAD",  # Existing valid git ref
        }

        self.db.save_checkpoint(
            idempotency_key=idemp_key,
            goal=goal,
            workflow_step="Commit changes",
            status="executing",
            payload=step,
        )

        res = self.loop.act(goal, step, idemp_key)
        self.assertTrue(res.get("reconciled"))
        self.assertEqual(res.get("external_id"), "HEAD")


if __name__ == "__main__":
    unittest.main()
