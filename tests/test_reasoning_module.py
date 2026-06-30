"""Tests for the HRM-inspired reasoning_module deep module.

Tests at the module boundary — no mocking of internals.
All stubs are deterministic so tests are 100% reliable (no error budget needed here).

To run:
    python -m pytest tests/test_reasoning_module.py -v
"""
import pytest
from types import SimpleNamespace
import modules.reasoning_module as reasoning_module
from modules.reasoning_module import (
    HLevelPlan,
    LLevelAction,
    HaltDecision,
    ReasoningTrace,
    reason,
    plan_only,
    execute_step,
)


# ---------------------------------------------------------------------------
# HLevelPlan
# ---------------------------------------------------------------------------

class TestHLevelPlan:
    def test_step_count(self):
        plan = HLevelPlan(
            steps=["step a", "step b", "step c"],
            goal_statement="Do three things",
            confidence=0.9,
            reasoning="",
            model="stub",
        )
        assert plan.step_count == 3

    def test_empty_steps(self):
        plan = HLevelPlan(steps=[], goal_statement="empty", confidence=0.0, reasoning="", model="stub")
        assert plan.step_count == 0


def test_gcloud_access_token_tries_windows_sdk_install_path(monkeypatch):
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        executable = cmd[0]
        if "Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.cmd" in executable:
            return SimpleNamespace(returncode=0, stdout="ya29.fake-token\n")
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\abdul\AppData\Local")
    monkeypatch.setattr(reasoning_module.subprocess, "run", fake_run)

    assert reasoning_module._gcloud_access_token() == "ya29.fake-token"
    assert any("Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.cmd" in call[0] for call in calls)


# ---------------------------------------------------------------------------
# LLevelAction
# ---------------------------------------------------------------------------

class TestLLevelAction:
    def test_should_execute_high_confidence(self):
        action = LLevelAction(
            step_index=0, step_description="do it",
            action_type="tool_call", payload={}, confidence=0.8, reasoning=""
        )
        assert action.should_execute is True

    def test_should_not_execute_low_confidence(self):
        action = LLevelAction(
            step_index=0, step_description="do it",
            action_type="tool_call", payload={}, confidence=0.3, reasoning=""
        )
        assert action.should_execute is False

    def test_skip_action_never_executes(self):
        action = LLevelAction(
            step_index=0, step_description="skip me",
            action_type="skip", payload={}, confidence=1.0, reasoning=""
        )
        assert action.should_execute is False


# ---------------------------------------------------------------------------
# HaltDecision
# ---------------------------------------------------------------------------

class TestHaltDecision:
    def test_halted_early_when_under_budget(self):
        halt = HaltDecision(should_halt=True, reason="confident", steps_used=2, steps_budget=8)
        assert halt.halted_early is True

    def test_not_halted_early_when_budget_exhausted(self):
        halt = HaltDecision(should_halt=True, reason="budget_exhausted", steps_used=8, steps_budget=8)
        assert halt.halted_early is False

    def test_not_halted_early_when_not_halted(self):
        halt = HaltDecision(should_halt=False, reason="continuing", steps_used=2, steps_budget=8)
        assert halt.halted_early is False


# ---------------------------------------------------------------------------
# plan_only — H module only
# ---------------------------------------------------------------------------

class TestPlanOnly:
    def test_returns_h_level_plan(self):
        plan = plan_only("Fix the Oracle trading strategy")
        assert isinstance(plan, HLevelPlan)

    def test_plan_has_steps(self):
        plan = plan_only("Deploy Oracle V5")
        assert len(plan.steps) > 0

    def test_plan_has_goal_statement(self):
        plan = plan_only("What should I do?")
        assert len(plan.goal_statement) > 0

    def test_confidence_is_between_0_and_1(self):
        plan = plan_only("anything")
        assert 0.0 <= plan.confidence <= 1.0

    def test_empty_problem_does_not_crash(self):
        # Should not raise
        plan = plan_only("", context="some context")
        assert isinstance(plan, HLevelPlan)

    def test_context_is_accepted(self):
        plan = plan_only("problem", context="Quantower is running, Oracle DLL deployed")
        assert isinstance(plan, HLevelPlan)


# ---------------------------------------------------------------------------
# execute_step — L module only
# ---------------------------------------------------------------------------

class TestExecuteStep:
    def test_returns_l_level_action(self):
        action = execute_step("Check if Quantower is running")
        assert isinstance(action, LLevelAction)

    def test_action_type_is_valid(self):
        action = execute_step("Verify DLL hash")
        assert action.action_type in ("tool_call", "answer", "observe", "skip")

    def test_confidence_in_range(self):
        action = execute_step("Do something")
        assert 0.0 <= action.confidence <= 1.0

    def test_step_index_is_set(self):
        action = execute_step("Run build", step_index=3)
        assert action.step_index == 3

    def test_step_description_preserved(self):
        action = execute_step("Connect to broker API")
        assert action.step_description == "Connect to broker API"


# ---------------------------------------------------------------------------
# reason — Full H→L→ACT cycle
# ---------------------------------------------------------------------------

class TestReason:
    def test_returns_reasoning_trace(self):
        trace = reason("Is Quantower running?")
        assert isinstance(trace, ReasoningTrace)

    def test_trace_has_plan(self):
        trace = reason("Fix Oracle V5 deployment")
        assert isinstance(trace.plan, HLevelPlan)
        assert trace.plan.step_count > 0

    def test_trace_has_halt_decision(self):
        trace = reason("Check system status")
        assert isinstance(trace.halt, HaltDecision)
        assert trace.halt.should_halt is True

    def test_trace_has_actions(self):
        trace = reason("Build and deploy Oracle")
        assert isinstance(trace.actions, list)

    def test_halt_reason_is_valid(self):
        trace = reason("diagnose issue")
        assert trace.halt.reason in ("goal_reached", "budget_exhausted", "stuck", "confident", "continuing")

    def test_steps_used_within_budget(self):
        budget = 3
        trace = reason("small problem", halt_budget=budget)
        assert trace.halt.steps_used <= budget

    def test_elapsed_ms_positive(self):
        trace = reason("timing test")
        assert trace.elapsed_ms >= 0.0

    def test_feedback_dict_present(self):
        trace = reason("Oracle status check")
        assert "plan_confidence" in trace.feedback
        assert "halt_reason" in trace.feedback
        assert "steps_planned" in trace.feedback
        assert "steps_executed" in trace.feedback

    def test_no_exception_on_empty_problem(self):
        trace = reason("")
        assert isinstance(trace, ReasoningTrace)

    def test_no_exception_with_large_budget(self):
        trace = reason("complex multi-step problem", halt_budget=100)
        assert isinstance(trace, ReasoningTrace)

    def test_inbox_summary_is_non_empty(self):
        trace = reason("Generate inbox summary")
        summary = trace.to_inbox_summary()
        assert len(summary) > 0

    def test_succeeded_flag_type(self):
        trace = reason("Should I trade now?")
        assert isinstance(trace.succeeded, bool)

    def test_executed_actions_subset_of_actions(self):
        trace = reason("multi-step workflow")
        executed = trace.executed_actions
        assert all(a in trace.actions for a in executed)

    def test_budget_one_runs_minimal_steps(self):
        trace = reason("minimal", halt_budget=1)
        assert trace.halt.steps_used <= 1

    def test_context_does_not_crash(self):
        trace = reason(
            "What is the Oracle V5 status?",
            context="Quantower running, DLL hash abc123, telemetry active"
        )
        assert isinstance(trace, ReasoningTrace)
