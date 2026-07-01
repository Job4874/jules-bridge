"""Tests for the reasoning eval harness script.

The eval harness is the CDLC feedback loop for reasoning_module: it runs
representative problems, scores the traces, and writes a structured report.
"""
import importlib.util
import json
from pathlib import Path


def _load_eval_module():
    module_path = Path(__file__).with_name("eval_reasoning.py")
    spec = importlib.util.spec_from_file_location("eval_reasoning", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReasoningEvalHarness:
    def test_run_eval_writes_report_with_stub_baseline(self, tmp_path):
        eval_reasoning = _load_eval_module()
        output_path = tmp_path / "eval_results.json"

        report = eval_reasoning.run_eval(model="stub", output_path=str(output_path))

        assert output_path.exists()
        persisted = json.loads(output_path.read_text(encoding="utf-8"))
        assert persisted == report
        assert report["model"] == "stub"
        assert report["problem_count"] >= 3
        assert len(report["results"]) == report["problem_count"]
        assert all("stub_baseline" in row for row in report["results"])
        assert all(row["model"] == "stub" for row in report["results"])

    def test_eval_rows_include_scoring_fields(self, tmp_path):
        eval_reasoning = _load_eval_module()
        report = eval_reasoning.run_eval(
            model="stub",
            output_path=str(tmp_path / "eval_results.json"),
        )

        row = report["results"][0]

        assert set([
            "problem",
            "model",
            "steps_taken",
            "confidence",
            "halted_early",
            "plan_coherence",
            "score",
            "stub_baseline",
        ]).issubset(row)
        assert 0.0 <= row["score"] <= 1.0
        assert isinstance(row["halted_early"], bool)

    def test_default_output_path_is_memory_eval_results(self):
        eval_reasoning = _load_eval_module()

        output_path = eval_reasoning.default_output_path()

        assert output_path.endswith(str(Path("memory") / "eval_results.json"))
