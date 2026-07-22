# Unit tests for modules/unified_operator.py

import json
import os
import tempfile
import unittest
from pathlib import Path

from modules import unified_operator as uo


class TestUnifiedOperator(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_state.db"
        self.db = uo.UnifiedOperatorStateDB(db_path=self.db_path)

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_sqlite_state_db_checkpoint_idempotency(self):
        rec1 = self.db.save_checkpoint(
            idempotency_key="key_001",
            goal="Implement UnifiedOperator",
            workflow_step="Step 1: DB setup",
            status="in_progress",
            git_branch="main",
            git_commit="abcdef123456",
            payload={'step': 1},
        )
        self.assertIsNotNone(rec1)
        self.assertEqual(rec1["idempotency_key"], "key_001")
        self.assertEqual(rec1["status"], "in_progress")

        rec2 = self.db.save_checkpoint(
            idempotency_key="key_001",
            goal="Implement UnifiedOperator",
            workflow_step="Step 1: DB setup",
            status="completed",
            git_branch="main",
            git_commit="abcdef123456",
            payload={'step': 1, 'result': 'ok'},
        )
        self.assertEqual(rec2["status"], "completed")
        self.assertEqual(rec2["payload"]["result"], "ok")

    def test_list_active_checkpoints(self):
        self.db.save_checkpoint("k1", "Goal 1", "step 1", status="in_progress")
        self.db.save_checkpoint("k2", "Goal 2", "step 2", status="completed")
        self.db.save_checkpoint("k3", "Goal 3", "step 3", status="executing")

        active = self.db.list_active_checkpoints()
        keys = [a["idempotency_key"] for a in active]
        self.assertIn("k1", keys)
        self.assertIn("k3", keys)
        self.assertNotIn("k2", keys)

    def test_record_recovery_event(self):
        evt_id = self.db.record_recovery_event("Service crash", "UnifiedOperatorService", {'pid': 1234})
        self.assertTrue(evt_id.startswith("rec_"))

    def test_worktree_lock_manager(self):
        lock_mgr = uo.WorktreeLockManager()
        wt = str(Path(".").resolve())

        self.assertTrue(lock_mgr.acquire_lock(wt, "agent_1"))
        self.assertTrue(lock_mgr.is_locked(wt))
        self.assertTrue(lock_mgr.acquire_lock(wt, "agent_1"))
        self.assertFalse(lock_mgr.acquire_lock(wt, "agent_2"))
        self.assertTrue(lock_mgr.release_lock(wt, "agent_1"))
        self.assertFalse(lock_mgr.is_locked(wt))
        self.assertTrue(lock_mgr.acquire_lock(wt, "agent_2"))

    def test_task_queue_manager_dependency_scheduling(self):
        queue = uo.TaskQueueManager(max_concurrent=2)
        t1 = queue.enqueue_task("task_1", "Initial build", priority=10)
        t2 = queue.enqueue_task("task_2", "Run tests", dependencies=["task_1"], priority=5)

        runnable = queue.get_runnable_tasks()
        self.assertEqual(len(runnable), 1)
        self.assertEqual(runnable[0]["task_id"], "task_1")

        queue.mark_status("task_1", "completed")
        runnable2 = queue.get_runnable_tasks()
        self.assertEqual(len(runnable2), 1)
        self.assertEqual(runnable2[0]["task_id"], "task_2")

    def test_observe_reason_act_verify_loop(self):
        loop = uo.ObserveReasonActVerifyLoop(self.db)
        obs = loop.observe()
        self.assertIn("git_branch", obs)
        self.assertIn("git_commit", obs)

        reasoning = loop.reason("Run test suite", obs)
        self.assertTrue(reasoning.get("coherence"))

        act_result = loop.act("Run test suite", {'description': 'Execute pytest'}, "idemp_loop_1")
        self.assertEqual(act_result["status"], "success")
        self.assertTrue(loop.verify(act_result))

        act_result2 = loop.act("Run test suite", {'description': 'Execute pytest'}, "idemp_loop_1")
        self.assertEqual(act_result2["status"], "skipped")

    def test_heartbeat_liveness(self):
        hb = uo.emit_heartbeat("ok")
        self.assertEqual(hb["status"], "ok")

        is_live, age = uo.check_heartbeat_liveness(max_stale_s=30.0)
        self.assertTrue(is_live)
        self.assertLess(age, 5.0)


if __name__ == "__main__":
    unittest.main()
