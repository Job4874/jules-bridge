"""Reasoning eval harness for Jules Bridge.

Runs representative reasoning_module problems and writes a structured report to
memory/eval_results.json. This is an eval script, not a pytest test.

Usage:
    python tests/eval_reasoning.py --model stub
    python tests/eval_reasoning.py --model fast
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.reasoning_module import ReasoningTrace, reason  # noqa: E402


_PROBLEMS = [
    {
        "id": "akc_readiness",
        "problem": "Verify AKC readiness before a Jules Bridge coding session.",
        "context": "Use context files, memory, and evidence gates before implementation.",
    },
    {
        "id": "oracle_blocker",
        "problem": "Diagnose why Oracle V5 is not ready for Quantower replay.",
        "context": "Prefer oracle_status, Verify-OracleReplayReady.ps1, and no live order mutation.",
    },
    {
        "id": "ticket_loop",
        "problem": "Pick the next ticket and implement it with TDD.",
        "context": "Use local markdown tickets, one vertical slice, tests first, then evidence.",
    },
]


def default_output_path() -> str:
    """Return the default eval report path."""
    return str(PROJECT_ROOT / "memory" / "eval_results.json")


def _score_trace(trace: ReasoningTrace) -> dict:
    """Score one trace with simple deterministic heuristics."""
    confidence = max(0.0, min(1.0, float(trace.plan.confidence)))
    steps_taken = trace.halt.steps_used
    efficient = steps_taken <= 5
    coherent = bool(trace.plan.goal_statement and trace.plan.steps)
    halted_early = trace.halt.halted_early

    score_parts = [
        confidence,
        1.0 if efficient else 0.5,
        1.0 if coherent else 0.0,
        1.0 if halted_early else 0.5,
    ]
    return {
        "steps_taken": steps_taken,
        "confidence": round(confidence, 3),
        "halted_early": halted_early,
        "plan_coherence": coherent,
        "score": round(sum(score_parts) / len(score_parts), 3),
    }


def _trace_row(problem: dict, model: str, trace: ReasoningTrace, stub_trace: ReasoningTrace) -> dict:
    """Render one trace and its stub baseline comparison as a JSON row."""
    row = {
        "problem_id": problem["id"],
        "problem": problem["problem"],
        "model": model,
        "goal_statement": trace.plan.goal_statement,
        "halt_reason": trace.halt.reason,
        "answer_present": trace.answer is not None,
        "feedback": trace.feedback,
        "trace": asdict(trace),
        "stub_baseline": _score_trace(stub_trace),
    }
    row.update(_score_trace(trace))
    return row


def run_eval(
    model: str = "fast",
    output_path: Optional[str] = None,
    problems: Optional[Iterable[dict]] = None,
) -> dict:
    """Run the reasoning eval and write memory/eval_results.json.

    Args:
        model: Reasoning model alias to evaluate. Use "stub" for offline tests.
        output_path: Optional JSON destination. Defaults to memory/eval_results.json.
        problems: Optional problem set override for tests.

    Returns:
        Structured eval report with one row per problem.
    """
    selected_problems = list(problems or _PROBLEMS)
    rows: List[dict] = []
    for problem in selected_problems:
        stub_trace = reason(
            problem["problem"],
            context=problem.get("context", ""),
            halt_budget=8,
            model="stub",
        )
        trace = stub_trace if model == "stub" else reason(
            problem["problem"],
            context=problem.get("context", ""),
            halt_budget=8,
            model=model,
        )
        rows.append(_trace_row(problem, model, trace, stub_trace))

    average_score = (
        sum(row["score"] for row in rows) / len(rows)
        if rows else 0.0
    )
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "problem_count": len(rows),
        "average_score": round(average_score, 3),
        "results": rows,
    }

    destination = Path(output_path or default_output_path())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run Jules Bridge reasoning evals.")
    parser.add_argument("--model", default=os.environ.get("REASONING_EVAL_MODEL", "stub"))
    parser.add_argument("--output", default=default_output_path())
    args = parser.parse_args(argv)

    report = run_eval(model=args.model, output_path=args.output)
    print(json.dumps({
        "model": report["model"],
        "problem_count": report["problem_count"],
        "average_score": report["average_score"],
        "output": args.output,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
