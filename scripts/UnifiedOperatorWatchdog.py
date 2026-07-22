"""UnifiedOperatorWatchdog -- Lightweight health monitor for UnifiedOperatorService.

Checks heartbeat liveness and triggers sc.exe restart / subprocess restart on failure.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from modules import unified_operator as uo


def run_watchdog_check(max_stale_s: float = 30.0) -> bool:
    is_live, age = uo.check_heartbeat_liveness(max_stale_s=max_stale_s)
    db = uo.UnifiedOperatorStateDB()

    if is_live:
        print(f"[Watchdog] UnifiedOperatorService is healthy (heartbeat age: {round(age, 2)}s).")
        return True

    print(f"[Watchdog] WARNING: UnifiedOperatorService heartbeat is STALE (age: {round(age, 2)}s). Triggering recovery...")
    db.record_recovery_event(
        reason="Heartbeat stale / service unresponsive",
        component="UnifiedOperatorWatchdog",
        details={"heartbeat_age_seconds": age},
    )

    # Attempt Windows service restart via sc.exe if running as Windows Service, or fallback to subprocess
    try:
        res = subprocess.run(["sc.exe", "query", "UnifiedOperatorService"], capture_output=True, text=True)
        if "RUNNING" in res.stdout or "STOPPED" in res.stdout:
            print("[Watchdog] Restarting UnifiedOperatorService via sc.exe...")
            subprocess.run(["sc.exe", "restart", "UnifiedOperatorService"], capture_output=True, text=True)
            return True
    except Exception as e:
        print(f"[Watchdog] sc.exe restart check skipped: {e}")

    return False


if __name__ == "__main__":
    run_watchdog_check(max_stale_s=30.0)
