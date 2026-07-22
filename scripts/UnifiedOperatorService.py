"""UnifiedOperatorService -- Always-On Windows Background Service.

Emits 10-second heartbeats and executes task queue operations continuously.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from modules import unified_operator as uo


def run_service_loop(max_cycles: int = -1, interval_s: float = 10.0) -> None:
    print("[UnifiedOperatorService] Starting service loop...")
    db = uo.UnifiedOperatorStateDB()
    q_mgr = uo.TaskQueueManager()
    loop = uo.ObserveReasonActVerifyLoop(db)

    cycles = 0
    while max_cycles < 0 or cycles < max_cycles:
        cycles += 1
        hb = uo.emit_heartbeat(status="ok")
        print(f"[UnifiedOperatorService] Heartbeat emitted at {hb['timestamp_utc']} (cycle {cycles})")

        # Observe & check active checkpoints
        active = db.list_active_checkpoints()
        if active:
            print(f"[UnifiedOperatorService] Found {len(active)} active checkpoint(s). Resuming...")
            for rec in active:
                idemp_key = rec["idempotency_key"]
                goal = rec["goal"]
                step = {"description": rec["workflow_step"]}
                act_res = loop.act(goal, step, idemp_key)
                loop.verify(act_res)

        time.sleep(interval_s)


if __name__ == "__main__":
    run_service_loop(max_cycles=3, interval_s=1.0)
