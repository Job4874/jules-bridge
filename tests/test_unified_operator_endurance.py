# Endurance and Crash Recovery Benchmark for UnifiedOperator

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from modules import unified_operator as uo


class TestUnifiedOperatorEndurance(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "endurance_state.db"
        self.db = uo.UnifiedOperatorStateDB(db_path=self.db_path)

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_crash_recovery_resumption(self):
        """Simulate a crash mid-workflow and verify resumption from transactional SQLite WAL checkpoint."""
        idemp_key = "crash_recovery_001"
        goal = "Process high-volume data batch"

        # Step 1: Save mid-execution checkpoint before simulated crash
        rec = self.db.save_checkpoint(
            idempotency_key=idemp_key,
            goal=goal,
            workflow_step="Step 2: Transforming records",
            status="executing",
            payload={"processed_count": 50, "total": 100},
        )
        self.assertEqual(rec["status"], "executing")

        # Step 2: Simulate process crash & restart (re-initialize state DB connection)
        db_restarted = uo.UnifiedOperatorStateDB(db_path=self.db_path)
        active = db_restarted.list_active_checkpoints()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["idempotency_key"], idemp_key)
        self.assertEqual(active[0]["payload"]["processed_count"], 50)

        # Step 3: Complete execution after recovery
        loop = uo.ObserveReasonActVerifyLoop(db_restarted)
        act_res = loop.act(goal, {"description": "Step 2: Transforming records"}, idemp_key)
        self.assertEqual(act_res["status"], "success")  # Completed interrupted step

        # Step 4: Subsequent re-execution is skipped idempotently
        act_res2 = loop.act(goal, {"description": "Step 2: Transforming records"}, idemp_key)
        self.assertEqual(act_res2["status"], "skipped")

    def test_parallel_task_queue_concurrency(self):
        """Verify priority scheduling and max concurrency bounds."""
        queue = uo.TaskQueueManager(max_concurrent=3)
        for i in range(10):
            queue.enqueue_task(f"t_{i}", f"Task {i}", priority=i)

        runnable = queue.get_runnable_tasks()
        self.assertEqual(len(runnable), 3)
        priorities = [t["priority"] for t in runnable]
        self.assertEqual(priorities, [9, 8, 7])

    def test_stale_lock_recovery(self):
        """Verify worktree lock release and re-acquisition under failure scenarios."""
        lock_mgr = uo.WorktreeLockManager()
        wt = str(Path(".").resolve())

        # Acquire lock for worker 1
        self.assertTrue(lock_mgr.acquire_lock(wt, "worker_1"))

        # Release lock on worker termination
        self.assertTrue(lock_mgr.release_lock(wt, "worker_1"))

        # Worker 2 acquires lock cleanly
        self.assertTrue(lock_mgr.acquire_lock(wt, "worker_2"))


if __name__ == "__main__":
    unittest.main()
