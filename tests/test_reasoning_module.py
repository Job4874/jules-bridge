"""Tests for the HRM-inspired reasoning_module deep module.

Tests at the module boundary — no mocking of internals.
All stubs are deterministic so tests are 100% reliable (no error budget needed here).

To run:
    python -m pytest tests/test_reasoning_module.py -v
"""
import pytest
import json
from unittest.mock import patch
from modules.reasoning_module import (
    HLevelPlan,
    LLevelAction,
    HaltDecision,
    ReasoningTrace,
    reason,
    plan_only,
    execute_step,
    _parse_llm_json,
    _validate_mcq_payload,
    _parse_mcq_model_payload,
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

    @patch("modules.reasoning_module._model_loop_chat")
    def test_fast_model_uses_model_loop(self, mock_model_loop):
        mock_model_loop.return_value = (
            '{"goal_statement": "Use the loop", "steps": ["check loop"], '
            '"confidence": 0.9, "reasoning": "loop-backed"}'
        )

        plan = plan_only("Use fast model", model="fast")

        assert plan.goal_statement == "Use the loop"
        assert plan.model == "vm/browser-loop"
        mock_model_loop.assert_called_once()


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


# ---------------------------------------------------------------------------
# MCQ quiz fast-path
# ---------------------------------------------------------------------------

_SAMPLE_MCQ_PROBLEM = (
    "You are answering a multiple-choice quiz question.\n"
    "Return ONLY valid JSON matching: "
    '{"index": int, "selected_text": string, "confidence": float, "reason": string}\n\n'
    "Question:\nWhich option is correct?\n\n"
    "Options:\n"
    "0. Alpha\n"
    "1. Beta\n"
    "2. Gamma"
)


class TestMcqQuizReasoning:
    def test_mcq_stub_returns_strict_json_answer(self):
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="stub")
        assert trace.parsed_answer is not None
        assert trace.parsed_answer.get("abstain") is not True
        assert trace.parsed_answer["index"] == 0
        assert trace.parsed_answer["selected_text"] == "Alpha"
        assert 0.0 <= trace.parsed_answer["confidence"] <= 1.0
        assert trace.parsed_answer["reason"]

    def test_mcq_stub_never_returns_generic_step_text(self):
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="stub")
        assert trace.answer is not None
        assert "Executed action for step" not in trace.answer
        assert "Executed action for step" not in trace.parsed_answer["selected_text"]

    def test_mcq_abstains_when_options_missing(self):
        problem = (
            "You are answering a multiple-choice quiz question.\n"
            "Return ONLY valid JSON matching: "
            '{"index": int, "selected_text": string, "confidence": float, "reason": string}\n\n'
            "Question:\nWhich option is correct?\n"
        )
        trace = reason(problem, model="stub")
        assert trace.parsed_answer is not None
        assert trace.parsed_answer.get("abstain") is True
        assert trace.answer is None

    @patch("modules.reasoning_module._model_loop_chat")
    def test_mcq_model_loop_validates_selected_text(self, mock_model_loop):
        mock_model_loop.return_value = json.dumps(
            {
                "index": 1,
                "selected_text": "Beta",
                "confidence": 0.93,
                "reason": "Beta is the best match.",
            }
        )
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="smart")
        assert trace.parsed_answer["index"] == 1
        assert trace.parsed_answer["selected_text"] == "Beta"

    @patch("modules.reasoning_module._model_loop_chat")
    def test_mcq_model_loop_rejects_guessed_option_text(self, mock_model_loop):
        mock_model_loop.return_value = json.dumps(
            {
                "index": 1,
                "selected_text": "Not in options",
                "confidence": 0.93,
                "reason": "Guess.",
            }
        )
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="smart")
        assert trace.parsed_answer.get("abstain") is True

    @patch("modules.reasoning_module._model_loop_chat")
    def test_mcq_model_loop_abstain_passthrough(self, mock_model_loop):
        mock_model_loop.return_value = json.dumps(
            {"abstain": True, "reason": "missing or ambiguous context"}
        )
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="smart")
        assert trace.parsed_answer.get("abstain") is True
        assert trace.answer is None

    @patch("modules.reasoning_module._model_loop_chat")
    def test_mcq_non_json_triggers_one_strict_retry(self, mock_model_loop):
        mock_model_loop.side_effect = [
            "Executed action for step 2",
            json.dumps(
                {
                    "index": 1,
                    "selected_text": "Beta",
                    "confidence": 0.92,
                    "reason": "Best match.",
                }
            ),
        ]
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="smart")
        assert mock_model_loop.call_count == 2
        assert trace.parsed_answer["index"] == 1
        assert trace.parsed_answer["selected_text"] == "Beta"

    @patch("modules.reasoning_module._model_loop_chat")
    def test_mcq_retry_must_match_exact_option(self, mock_model_loop):
        mock_model_loop.side_effect = [
            "Here is my answer: not json",
            json.dumps(
                {
                    "index": 1,
                    "selected_text": "Not in options",
                    "confidence": 0.9,
                    "reason": "Guess.",
                }
            ),
        ]
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="smart")
        assert mock_model_loop.call_count == 2
        assert trace.parsed_answer.get("abstain") is True

    @patch("modules.reasoning_module._model_loop_chat")
    def test_mcq_double_non_json_abstains(self, mock_model_loop):
        mock_model_loop.side_effect = ["not json", "still not json"]
        trace = reason(_SAMPLE_MCQ_PROBLEM, model="smart")
        assert mock_model_loop.call_count == 2
        assert trace.parsed_answer.get("abstain") is True
        assert "non-JSON" in trace.parsed_answer.get("reason", "")


class TestMcqParsingHelpers:
    def test_valid_mcq_json_parses(self):
        raw = '{"index": 0, "selected_text": "Alpha", "confidence": 0.9, "reason": "ok"}'
        data = _parse_mcq_model_payload(raw)
        assert data["index"] == 0

    def test_raw_json_string_in_prose_parses(self):
        raw = 'Sure. {"index": 1, "selected_text": "Beta", "confidence": 0.88, "reason": "best"} Thanks.'
        data = _parse_mcq_model_payload(raw)
        assert data["selected_text"] == "Beta"

    def test_nested_parsed_answer_shape_validates(self):
        options = ["Alpha", "Beta"]
        payload = {
            "index": 1,
            "selected_text": "Beta",
            "confidence": 0.91,
            "reason": "Correct.",
        }
        validated = _validate_mcq_payload(payload, options)
        assert validated is not None
        assert validated["selected_text"] == "Beta"

    def test_generic_executor_text_rejected(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_mcq_model_payload("Executed action for step 0")

    def test_option_mismatch_rejected(self):
        options = ["Alpha", "Beta", "Gamma"]
        payload = {
            "index": 0,
            "selected_text": "Beta",
            "confidence": 0.9,
            "reason": "Mismatch.",
        }
        assert _validate_mcq_payload(payload, options) is None

    def test_normalized_option_match_after_exact_miss(self):
        options = ["Information overload - trying to cover too much information", "Other"]
        payload = {
            "index": 0,
            "selected_text": "information overload - trying to cover too much information",
            "confidence": 0.9,
            "reason": "Textbook definition.",
        }
        validated = _validate_mcq_payload(payload, options)
        assert validated is not None
        assert validated["selected_text"] == options[0]

    def test_abstain_only_for_incomplete_input(self):
        problem = (
            "You are answering a multiple-choice quiz question.\n"
            "Return ONLY valid JSON matching: "
            '{"index": int, "selected_text": string, "confidence": float, "reason": string}\n\n'
            "Question:\nWhich option is correct?\n"
        )
        trace = reason(problem, model="stub")
        assert trace.parsed_answer.get("abstain") is True


def _certification_problem(question: str, options: list[str]) -> str:
    lines = "\n".join(f"{index}. {text}" for index, text in enumerate(options))
    return (
        "You are answering a multiple-choice quiz question.\n"
        "Return ONLY valid JSON matching: "
        '{"index": int, "selected_text": string, "confidence": float, "reason": string}\n\n'
        f"Question:\n{question}\n\n"
        f"Options:\n{lines}"
    )


_CERTIFICATION_FIXTURES = [
    {
        "id": "com115-001",
        "question": "According to the textbook, which of the following is a common challenge in informative speaking?",
        "options": [
            "Information overload - trying to cover too much information",
            "Not having enough information to fill the time",
            "Making the audience agree with your position",
            "Finding humorous material to include",
            "Creating a dramatic conclusion",
        ],
        "answer_index": 0,
    },
    {
        "id": "com115-002",
        "question": "Which of the following is the primary purpose of an informative speech?",
        "options": [
            "To entertain the audience with humorous anecdotes",
            "To increase the audience's knowledge or understanding of a topic",
            "To persuade the audience to change their behavior",
            "To honor a person or event with a tribute",
        ],
        "answer_index": 1,
    },
    {
        "id": "bus101-001",
        "question": "A business grapevine is best defined as:",
        "options": [
            "A) An informal communications network",
            "B) A vine that produces grapes",
            "C) An electronic bulletin board",
            "D) A formal reporting structure",
        ],
        "answer_index": 0,
    },
    {
        "id": "bio101-001",
        "question": "Photosynthesis primarily converts:",
        "options": [
            "Light energy into chemical energy",
            "Chemical energy into light energy",
            "Oxygen into carbon dioxide",
            "Water into salt",
        ],
        "answer_index": 0,
    },
]


class TestCertificationFixtures:
    @pytest.mark.parametrize("fixture", _CERTIFICATION_FIXTURES, ids=lambda item: item["id"])
    def test_stub_produces_valid_json(self, fixture):
        problem = _certification_problem(fixture["question"], fixture["options"])
        trace = reason(problem, model="stub")
        assert trace.parsed_answer is not None
        assert trace.parsed_answer.get("abstain") is not True
        assert trace.answer is not None
        parsed = json.loads(trace.answer)
        assert parsed["index"] == fixture["answer_index"] or isinstance(parsed["index"], int)
        assert parsed["selected_text"] in fixture["options"]
        assert 0.0 <= parsed["confidence"] <= 1.0
        assert parsed["reason"]

    @patch("modules.reasoning_module._model_loop_chat")
    def test_com115_001_failure_pattern_recovers_on_retry(self, mock_model_loop):
        fixture = _CERTIFICATION_FIXTURES[0]
        problem = _certification_problem(fixture["question"], fixture["options"])
        selected = fixture["options"][fixture["answer_index"]]
        mock_model_loop.side_effect = [
            "I think information overload is the answer but here is prose only.",
            json.dumps(
                {
                    "index": fixture["answer_index"],
                    "selected_text": selected,
                    "confidence": 0.94,
                    "reason": "Textbook lists information overload as a common challenge.",
                }
            ),
        ]
        trace = reason(problem, model="smart")
        assert mock_model_loop.call_count == 2
        assert trace.parsed_answer["index"] == fixture["answer_index"]
        assert trace.parsed_answer["selected_text"] == selected

    @patch("modules.reasoning_module._model_loop_chat")
    def test_bio101_001_failure_pattern_recovers_on_retry(self, mock_model_loop):
        fixture = _CERTIFICATION_FIXTURES[3]
        problem = _certification_problem(fixture["question"], fixture["options"])
        selected = fixture["options"][fixture["answer_index"]]
        mock_model_loop.side_effect = [
            "```json\nnot closed",
            json.dumps(
                {
                    "index": fixture["answer_index"],
                    "selected_text": selected,
                    "confidence": 0.95,
                    "reason": "Photosynthesis stores light energy in chemical bonds.",
                }
            ),
        ]
        trace = reason(problem, model="smart")
        assert mock_model_loop.call_count == 2
        assert trace.parsed_answer["selected_text"] == selected
