"""Hierarchical reasoning deep module — HRM-inspired two-timescale reasoning.

Implements the Hierarchical Reasoning Model (HRM) pattern for Jules Bridge
using structured LLM calls instead of the neural network in the paper.
See: https://arxiv.org/abs/2506.21734

Architecture mirrors the original HRM:
  - H module (high-level): slow, abstract planning — "what needs to happen?"
  - L module (low-level): fast, detailed execution — "how do I do each step?"
  - ACT halting: the system decides when it's done, rather than running a fixed number of steps

Unlike the paper's recurrent neural architecture, this module uses LLM calls
as the computation primitive. The H/L split maps to prompt engineering:
  - H prompt: sees the full problem, produces an abstract multi-step plan
  - L prompt: sees one H-level step, produces a concrete runnable action

This is a deep module: single typed interface, complex hidden implementation.

Public interface:
    reason(problem, context, halt_budget) -> ReasoningTrace
    plan_only(problem, context) -> HLevelPlan
    execute_step(step, context) -> LLevelAction
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Typed contracts — the "carry" state analogous to HRM's recurrent carry
# ---------------------------------------------------------------------------

@dataclass
class HLevelPlan:
    """High-level abstract plan produced by the H module.

    Analogous to HRM's z_H (high-level hidden state).
    Contains the strategic structure before any details are resolved.
    """
    steps: List[str]          # Ordered abstract steps ("plan the plan")
    goal_statement: str       # One-sentence statement of the final goal
    confidence: float         # 0.0–1.0 confidence the plan is correct
    reasoning: str            # H module's chain of thought (hidden from caller)
    model: str                # Which LLM produced this plan

    @property
    def step_count(self) -> int:
        return len(self.steps)


@dataclass
class LLevelAction:
    """Low-level concrete action produced by the L module for one H step.

    Analogous to HRM's z_L (low-level hidden state).
    """
    step_index: int           # Which H-level step this executes
    step_description: str     # The H step being resolved
    action_type: str          # "tool_call" | "answer" | "observe" | "skip"
    payload: Dict[str, Any]   # The concrete action (tool args, answer text, etc.)
    confidence: float         # 0.0–1.0 confidence this action is correct
    reasoning: str            # L module's chain of thought (hidden from caller)

    @property
    def should_execute(self) -> bool:
        return self.action_type != "skip" and self.confidence >= 0.5


@dataclass
class HaltDecision:
    """ACT halting decision — should the reasoning loop continue or stop?

    Analogous to HRM's Q-learning halting with halt_max_steps.
    """
    should_halt: bool
    reason: str               # "goal_reached" | "budget_exhausted" | "stuck" | "confident"
    steps_used: int
    steps_budget: int

    @property
    def halted_early(self) -> bool:
        """True if halted before exhausting the budget (efficient!)"""
        return self.should_halt and self.steps_used < self.steps_budget


@dataclass
class ReasoningTrace:
    """Full trace of one reasoning run through H → L cycles.

    The complete record of what the hierarchical reasoner did, analogous to
    the full carry state at the end of HRM's forward pass.
    """
    problem: str
    plan: HLevelPlan
    actions: List[LLevelAction]
    halt: HaltDecision
    answer: Optional[str]
    elapsed_ms: float

    # CDLC Observe: structured feedback for improving future context
    feedback: Dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.answer is not None and self.halt.reason in ("goal_reached", "confident")

    @property
    def executed_actions(self) -> List[LLevelAction]:
        return [a for a in self.actions if a.should_execute]

    def to_inbox_summary(self) -> str:
        """Format as a compact summary for inbox_service."""
        lines = [
            f"Goal: {self.plan.goal_statement}",
            f"Steps planned: {self.plan.step_count}, executed: {len(self.executed_actions)}",
            f"Halted: {self.halt.reason} (step {self.halt.steps_used}/{self.halt.steps_budget})",
            f"Elapsed: {self.elapsed_ms:.0f}ms",
        ]
        if self.answer:
            lines.append(f"Answer: {self.answer}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call stubs — replace with real LLM calls in production
# ---------------------------------------------------------------------------
# These stubs make the module testable without a live LLM.
# In production, swap _h_module_call and _l_module_call with actual calls
# to your preferred LLM API (OpenAI, Anthropic, Gemini, etc.)

def _h_module_call(problem: str, context: str, model: str = "stub") -> Dict[str, Any]:
    """H module: high-level planning call.

    In production: replace with LLM API call using a planning-focused system prompt.

    System prompt template (H module):
        You are a strategic planner. Break the problem into 3-7 high-level steps.
        Do NOT include implementation details — those come later.
        For each step, write one clear action sentence.
        Return JSON: {goal_statement, steps: [], confidence, reasoning}

    Args:
        problem: The problem to solve
        context: Relevant background context
        model: LLM model identifier

    Returns:
        JSON-parseable dict with goal_statement, steps, confidence, reasoning
    """
    # Stub: returns a deterministic plan for testing
    return {
        "goal_statement": f"Resolve: {problem[:60]}",
        "steps": [
            "Understand the current state",
            "Identify what needs to change",
            "Make the change",
            "Verify the result",
        ],
        "confidence": 0.8,
        "reasoning": "[H module stub — replace with real LLM call]",
        "model": model,
    }


def _l_module_call(
    step: str,
    step_index: int,
    problem: str,
    context: str,
    model: str = "stub",
) -> Dict[str, Any]:
    """L module: low-level execution planning for one H step.

    In production: replace with LLM API call using an execution-focused system prompt.

    System prompt template (L module):
        You are a precise executor. You have one task to complete.
        Return the exact action to take as JSON.
        action_type must be one of: "tool_call" | "answer" | "observe" | "skip"
        Return JSON: {action_type, payload, confidence, reasoning}

    Args:
        step: One H-level step description
        step_index: Index of this step in the plan
        problem: The original problem (full context)
        context: Additional context
        model: LLM model identifier

    Returns:
        JSON-parseable dict with action_type, payload, confidence, reasoning
    """
    # Stub: returns a deterministic action for testing
    return {
        "action_type": "answer",
        "payload": {"text": f"[Stub execution of step {step_index}: {step[:40]}]"},
        "confidence": 0.7,
        "reasoning": "[L module stub — replace with real LLM call]",
    }


def _halt_check(
    actions: List[LLevelAction],
    plan: HLevelPlan,
    steps_used: int,
    steps_budget: int,
) -> HaltDecision:
    """ACT halting decision — should we stop or keep computing?

    Implements the Q-learning halting logic from HRM, adapted for LLM-based reasoning:
    - If all plan steps have been executed: halt (goal reached)
    - If budget exhausted: halt (forced)
    - If confidence is very high: halt early (efficient)
    - If stuck (repeated failures): halt (give up gracefully)

    Args:
        actions: Actions taken so far
        plan: The H-level plan
        steps_used: How many L-module calls have been made
        steps_budget: Maximum allowed L-module calls

    Returns:
        HaltDecision indicating whether to stop and why
    """
    if steps_used >= steps_budget:
        return HaltDecision(
            should_halt=True,
            reason="budget_exhausted",
            steps_used=steps_used,
            steps_budget=steps_budget,
        )

    executed = [a for a in actions if a.should_execute]
    all_steps_done = len(executed) >= plan.step_count

    if all_steps_done:
        return HaltDecision(
            should_halt=True,
            reason="goal_reached",
            steps_used=steps_used,
            steps_budget=steps_budget,
        )

    # Check if stuck: last 2 consecutive actions both low confidence
    if len(actions) >= 2:
        last_two = actions[-2:]
        if all(a.confidence < 0.4 for a in last_two):
            return HaltDecision(
                should_halt=True,
                reason="stuck",
                steps_used=steps_used,
                steps_budget=steps_budget,
            )

    # High confidence early halt (like ACT epsilon exploration)
    if actions and actions[-1].confidence >= 0.95 and len(executed) >= plan.step_count - 1:
        return HaltDecision(
            should_halt=True,
            reason="confident",
            steps_used=steps_used,
            steps_budget=steps_budget,
        )

    return HaltDecision(
        should_halt=False,
        reason="continuing",
        steps_used=steps_used,
        steps_budget=steps_budget,
    )


def _extract_answer(actions: List[LLevelAction], plan: HLevelPlan) -> Optional[str]:
    """Extract a final answer from the set of executed actions."""
    answer_actions = [a for a in actions if a.action_type == "answer" and a.should_execute]
    if not answer_actions:
        return None
    # Take the last answer action (most refined)
    last = answer_actions[-1]
    return last.payload.get("text")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def reason(
    problem: str,
    context: str = "",
    halt_budget: int = 8,
    model: str = "stub",
) -> ReasoningTrace:
    """Run hierarchical reasoning on a problem using H → L cycles with ACT halting.

    This is the main entry point. It mirrors the HRM forward pass:
      1. H module produces an abstract plan (z_H)
      2. For each plan step, L module produces a concrete action (z_L)
      3. ACT halting decides when to stop (even before the budget is exhausted)

    Args:
        problem: The problem to solve (free-form text or JSON)
        context: Additional context (e.g. current system state, constraints)
        halt_budget: Maximum number of L-module calls before forced halt
                     (analogous to halt_max_steps in HRM config)
        model: LLM model to use for H and L modules

    Returns:
        ReasoningTrace with plan, executed actions, halt decision, and answer

    Never raises — all sub-operations are defensive and return partial data.
    This matches oracle_session.py's contract: "Never raises".
    """
    t0 = time.perf_counter()
    actions: List[LLevelAction] = []

    # Step 1: H module — produce the abstract plan
    try:
        h_raw = _h_module_call(problem, context, model)
        plan = HLevelPlan(
            steps=h_raw.get("steps", []),
            goal_statement=h_raw.get("goal_statement", problem[:80]),
            confidence=float(h_raw.get("confidence", 0.5)),
            reasoning=h_raw.get("reasoning", ""),
            model=h_raw.get("model", model),
        )
    except Exception as exc:
        plan = HLevelPlan(
            steps=["Resolve the problem"],
            goal_statement=problem[:80],
            confidence=0.1,
            reasoning=f"H module failed: {exc}",
            model=model,
        )

    # Step 2: L module loop — execute each step with ACT halting
    steps_used = 0
    for step_index, step in enumerate(plan.steps):
        halt = _halt_check(actions, plan, steps_used, halt_budget)
        if halt.should_halt:
            break

        try:
            l_raw = _l_module_call(step, step_index, problem, context, model)
            action = LLevelAction(
                step_index=step_index,
                step_description=step,
                action_type=l_raw.get("action_type", "skip"),
                payload=l_raw.get("payload", {}),
                confidence=float(l_raw.get("confidence", 0.5)),
                reasoning=l_raw.get("reasoning", ""),
            )
        except Exception as exc:
            action = LLevelAction(
                step_index=step_index,
                step_description=step,
                action_type="skip",
                payload={"error": str(exc)},
                confidence=0.0,
                reasoning=f"L module failed: {exc}",
            )

        actions.append(action)
        steps_used += 1

    # Final halt decision
    final_halt = _halt_check(actions, plan, steps_used, halt_budget)
    if not final_halt.should_halt:
        final_halt = HaltDecision(
            should_halt=True,
            reason="goal_reached",
            steps_used=steps_used,
            steps_budget=halt_budget,
        )

    answer = _extract_answer(actions, plan)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return ReasoningTrace(
        problem=problem,
        plan=plan,
        actions=actions,
        halt=final_halt,
        answer=answer,
        elapsed_ms=elapsed_ms,
        # CDLC Observe: structured feedback for context improvement
        feedback={
            "plan_confidence": plan.confidence,
            "steps_planned": plan.step_count,
            "steps_executed": len([a for a in actions if a.should_execute]),
            "halt_reason": final_halt.reason,
            "halted_early": final_halt.halted_early,
            "mean_action_confidence": (
                sum(a.confidence for a in actions) / len(actions) if actions else 0.0
            ),
        },
    )


def plan_only(problem: str, context: str = "", model: str = "stub") -> HLevelPlan:
    """Run only the H module — return an abstract plan without executing any steps.

    Use when you want to preview the plan before committing to execution.

    Args:
        problem: The problem to plan for
        context: Additional context
        model: LLM model to use

    Returns:
        HLevelPlan with abstract steps and confidence
    """
    try:
        h_raw = _h_module_call(problem, context, model)
        return HLevelPlan(
            steps=h_raw.get("steps", []),
            goal_statement=h_raw.get("goal_statement", problem[:80]),
            confidence=float(h_raw.get("confidence", 0.5)),
            reasoning=h_raw.get("reasoning", ""),
            model=h_raw.get("model", model),
        )
    except Exception as exc:
        return HLevelPlan(
            steps=[],
            goal_statement=problem[:80],
            confidence=0.0,
            reasoning=f"H module failed: {exc}",
            model=model,
        )


def execute_step(
    step: str,
    context: str = "",
    step_index: int = 0,
    problem: str = "",
    model: str = "stub",
) -> LLevelAction:
    """Run only the L module for a single step — useful for manual control.

    Use when you have a specific step to execute without running the full H→L cycle.

    Args:
        step: The step description to execute
        context: Additional context
        step_index: Index of this step (for logging)
        problem: The original problem (for full context)
        model: LLM model to use

    Returns:
        LLevelAction with the concrete action to take
    """
    try:
        l_raw = _l_module_call(step, step_index, problem or step, context, model)
        return LLevelAction(
            step_index=step_index,
            step_description=step,
            action_type=l_raw.get("action_type", "skip"),
            payload=l_raw.get("payload", {}),
            confidence=float(l_raw.get("confidence", 0.5)),
            reasoning=l_raw.get("reasoning", ""),
        )
    except Exception as exc:
        return LLevelAction(
            step_index=step_index,
            step_description=step,
            action_type="skip",
            payload={"error": str(exc)},
            confidence=0.0,
            reasoning=f"L module failed: {exc}",
        )
