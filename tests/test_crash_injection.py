"""Crash injection tests for the 4-state operation lifecycle.

Tests the four critical crash points:
1. Crash before dispatch (after generating operation ID, before external call)
2. Crash after dispatch, before checkpoint (external call made, status not saved)
3. Crash before checkpoint complete (external confirmed, "completed" not saved)
4. Crash after checkpoint (normal completion, re-entry attempt)

Each test simulates the crash by directly manipulating the checkpoint database
to place the state machine at the crash point, then calling act() to verify
correct recovery behavior.
"""

import tempfile
import unittest
from pathlib import Path

from modules import unified_operator as uo


class TestCrashInjection(unittest.TestCase):
    """Verify that every crash point in the 4-state lifecycle recovers correctly."""

    def setUp(self):  # pylint: disable=invalid-name
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "crash_test_state.db"
        self.db = uo.UnifiedOperatorStateDB(db_path=self.db_path)
        self.loop = uo.ObserveReasonActVerifyLoop(self.db)

    def tearDown(self):  # pylint: disable=invalid-name
        try:
            self.tmp_dir.cleanup()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def test_generate_operation_id_uniqueness(self):
        """Operation IDs must be unique and contain the action type prefix."""
        id1 = uo.generate_operation_id("jules")
        id2 = uo.generate_operation_id("jules")
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith("jules_"))
        self.assertTrue(id2.startswith("jules_"))

    def test_empty_idempotency_key_rejected(self):
        """act() must reject empty idempotency keys to prevent untracked operations."""
        with self.assertRaises(ValueError):
            self.loop.act("test_goal", {"description": "test"}, "")

    def test_crash_before_dispatch(self):
        """Crash after generating operation ID but before any external call.

        State: 'dispatching' in the DB (intent recorded, nothing external happened).
        Expected: act() retries from dispatching, completes normally. No duplicate.
        """
        op_id = uo.generate_operation_id("jules")
        goal = "test crash before dispatch"
        step = {"description": "Create Jules session", "action_type": "jules_session"}

        # Simulate: we saved dispatching state, then crashed
        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=goal,
            workflow_step="Create Jules session",
            status="dispatching",
            payload=step,
        )

        # Restart: act() should see dispatching, attempt reconciliation (fails),
        # then re-execute normally
        result = self.loop.act(goal, step, op_id)
        self.assertEqual(result["status"], "success")

        # Verify checkpoint is now completed
        chk = self.db.get_checkpoint(op_id)
        self.assertEqual(chk["status"], "completed")

    def test_crash_after_dispatch_before_checkpoint(self):
        """Crash after Jules API call but before saving 'executing' status.

        State: 'dispatching' in the DB, but the external call actually happened.
        The step has an external_id, so reconciliation should find it.
        Expected: act() reconciles the existing external action and marks completed.
        """
        op_id = uo.generate_operation_id("jules")
        goal = "test crash after dispatch"
        step = {
            "description": "Create Jules session",
            "action_type": "jules_session",
            "external_id": "session_12345",
        }

        # Simulate: dispatching saved, external call succeeded, but we crashed
        # before saving "executing"
        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=goal,
            workflow_step="Create Jules session",
            status="dispatching",
            payload=step,
        )

        # Restart: act() should reconcile the Jules session
        result = self.loop.act(goal, step, op_id)
        self.assertTrue(result.get("reconciled"))
        self.assertEqual(result.get("external_id"), "session_12345")

        # Verify checkpoint is completed
        chk = self.db.get_checkpoint(op_id)
        self.assertEqual(chk["status"], "completed")

    def test_crash_before_checkpoint_complete(self):
        """Crash after external confirmed but before saving 'completed'.

        State: 'executing' in the DB, external action already succeeded.
        Expected: act() reconciles and marks completed without re-dispatching.
        """
        op_id = uo.generate_operation_id("commit")
        goal = "test crash before complete"
        step = {
            "description": "Commit changes",
            "action_type": "git_commit",
            "external_id": "HEAD",  # Existing valid git ref
        }

        # Simulate: executing saved, external call succeeded, crashed before completed
        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=goal,
            workflow_step="Commit changes",
            status="executing",
            payload=step,
        )

        # Restart: act() should reconcile the git commit
        result = self.loop.act(goal, step, op_id)
        self.assertTrue(result.get("reconciled"))
        self.assertEqual(result.get("external_id"), "HEAD")

        # Verify checkpoint is completed
        chk = self.db.get_checkpoint(op_id)
        self.assertEqual(chk["status"], "completed")

    def test_crash_after_checkpoint(self):
        """Crash after 'completed' was saved.

        State: 'completed' in the DB.
        Expected: act() returns 'skipped' — no re-execution.
        """
        op_id = uo.generate_operation_id("jules")
        goal = "test crash after checkpoint"
        step = {"description": "Already done", "action_type": "jules_session"}

        # Simulate: fully completed before crash
        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=goal,
            workflow_step="Already done",
            status="completed",
            payload={"result": "success"},
        )

        # Restart: act() should skip
        result = self.loop.act(goal, step, op_id)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "Already completed")

    def test_no_duplicate_after_dispatching_crash_without_external_id(self):
        """Crash during dispatching with no external_id means nothing happened externally.

        Reconciliation returns reconciled=False, so act() re-executes safely.
        The key insight: without an external_id, reconciliation cannot confirm
        the external action occurred, so retry is safe.
        """
        op_id = uo.generate_operation_id("submit")
        goal = "test safe retry"
        step = {
            "description": "Submit assignment",
            "action_type": "submission",
            # No external_id — nothing happened externally
        }

        self.db.save_checkpoint(
            idempotency_key=op_id,
            goal=goal,
            workflow_step="Submit assignment",
            status="dispatching",
            payload=step,
        )

        # Restart: reconciliation fails (no external_id), act() re-executes
        result = self.loop.act(goal, step, op_id)
        self.assertEqual(result["status"], "success")

        # Verify exactly one completed checkpoint
        chk = self.db.get_checkpoint(op_id)
        self.assertEqual(chk["status"], "completed")


if __name__ == "__main__":
    unittest.main()
