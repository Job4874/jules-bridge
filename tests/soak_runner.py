"""Soak test runner for UnifiedOperator.

Runs the observe→reason→act→verify loop continuously for a specified duration,
emitting heartbeats and logging cycle metrics. Produces a structured JSON report.

Usage:
    .venv\\Scripts\\python.exe tests/soak_runner.py --duration 3600   # 1-hour soak
    .venv\\Scripts\\python.exe tests/soak_runner.py --duration 43200  # 12-hour soak
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from modules.unified_operator import (
    ObserveReasonActVerifyLoop,
    UnifiedOperatorStateDB,
    emit_heartbeat,
    generate_operation_id,
)

_RESULTS_DIR = _ROOT / "test-results"


def run_soak(duration_s: int, interval_s: float = 10.0, label: str = "soak") -> dict:
    """Run the ORAV loop for the specified duration.

    Returns a structured report dict.
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    db_path = _RESULTS_DIR / f"{label}_state.db"
    db = UnifiedOperatorStateDB(db_path=db_path)
    loop = ObserveReasonActVerifyLoop(db)

    start = time.time()
    cycles = 0
    errors = 0
    max_cycle_ms = 0.0
    min_cycle_ms = float("inf")
    total_cycle_ms = 0.0

    print(f"[{label}] Starting soak test: {duration_s}s, interval {interval_s}s")
    print(f"[{label}] DB: {db_path}")

    while time.time() - start < duration_s:
        cycle_start = time.time()
        try:
            obs = loop.observe()
            reason = loop.reason(f"{label}-cycle-{cycles}", obs)
            op_id = generate_operation_id(f"{label}_cycle")
            result = loop.act(
                f"{label}-cycle-{cycles}",
                {"description": f"cycle_{cycles}", "observation_summary": obs.get("git_branch", "")},
                op_id,
            )
            verified = loop.verify(result)
            emit_heartbeat(status="soak_running")

            cycle_ms = (time.time() - cycle_start) * 1000
            max_cycle_ms = max(max_cycle_ms, cycle_ms)
            min_cycle_ms = min(min_cycle_ms, cycle_ms)
            total_cycle_ms += cycle_ms

            if cycles % 10 == 0:
                elapsed = time.time() - start
                print(f"[{label}] Cycle {cycles} | elapsed={elapsed:.0f}s | cycle_ms={cycle_ms:.1f} | verified={verified}")

        except Exception as exc:
            errors += 1
            print(f"[{label}] ERROR in cycle {cycles}: {exc}")

        cycles += 1
        remaining = duration_s - (time.time() - start)
        if remaining > 0:
            time.sleep(min(interval_s, remaining))

    elapsed_total = time.time() - start
    avg_cycle_ms = total_cycle_ms / max(cycles, 1)

    report = {
        "label": label,
        "started_utc": datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "duration_requested_s": duration_s,
        "duration_actual_s": round(elapsed_total, 2),
        "cycles_completed": cycles,
        "errors": errors,
        "avg_cycle_ms": round(avg_cycle_ms, 2),
        "max_cycle_ms": round(max_cycle_ms, 2),
        "min_cycle_ms": round(min_cycle_ms, 2) if min_cycle_ms != float("inf") else 0,
        "interval_s": interval_s,
        "status": "PASS" if errors == 0 else "FAIL",
        "db_path": str(db_path),
    }

    report_path = _RESULTS_DIR / f"{label}_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[{label}] === SOAK COMPLETE ===")
    print(json.dumps(report, indent=2))
    print(f"Report saved: {report_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UnifiedOperator soak test runner")
    parser.add_argument("--duration", type=int, default=3600, help="Soak duration in seconds")
    parser.add_argument("--interval", type=float, default=10.0, help="Seconds between cycles")
    parser.add_argument("--label", type=str, default="soak_1h", help="Test label for output files")
    args = parser.parse_args()

    result = run_soak(args.duration, args.interval, args.label)
    sys.exit(0 if result["status"] == "PASS" else 1)
